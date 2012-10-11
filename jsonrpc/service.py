"""
This module is home to the ``JSONRPCService`` API base-class.
"""
import sys
import logging
import json
import urllib2
import traceback

from django.db import connection
from django.http import HttpResponse

from .decorators import jrpc
from .errors import (InternalError, InvalidParamsError, InvalidRequestError,
                     JSONRPCError, MethodNotFoundError, ParseError)
from .json_types import JSONType
from .encoders import RobustEncoder


logger = logging.getLogger(__name__)


class JSONRPCServiceMeta(type):
    """
    The purpose of this metaclass is to allow sub-classes to register
    methods using a decorator: ``jrpc(method_name)``, then use
    ``gateway.supports_method(method_name)`` to check at runtime if the gateway
    they're using supports a given method.

    This metaclass adds a ``rpc_methods`` attribute to sub-classes, which is a
    dicitonary of method lookups. The methods added to this dictionary are ones
    decorated with ``jrpc('method_name')``. The method name passed into the
    decorator is used for the dictionary key.

    """
    def __new__(mcs, name, bases, dct):
        """
        Attaches a dictionary of methods wrapped by ``decorators.jrpc``.
        """
        dct['rpc_methods'] = {}
        for base in bases:
            # Update the methods dict from all bases, overwriting each parent
            # class's RPC methods with any sub-class methods of the same name,
            # so that designers of service classes may use natural inheritance.
            try:
                dct['rpc_methods'].update(base.rpc_methods)
            except AttributeError:  # Some mixin or ``object`` was encountered.
                pass

        for member in dct.itervalues():
            if hasattr(member, 'rpc_method_name'):
                # Add, or update this key on the rpc methods dict.
                dct['rpc_methods'][member.rpc_method_name] = member

        return type.__new__(mcs, name, bases, dct)


class JSONRPCService(object):
    """
    Create a subclass of this, add methods (wrapped in ``decorators.jrpc``),
    and map an instance of the class to a URL, and you have a JSON-RPC service.
    All API methods need to return normal, hashable responses, suitable for
    ``json.dumps``.

    # Usage::

    class MyService(JSONRPCService):
        @jrpc('sum(a=<num>, b=<num>) -> <num>')
        def add_numbers(self, request, a, b):
            logger.debug(u'API request by %s' % (request.user.username,))
            return a + b

    urlpatterns = patterns('',
        url(r'^rpc.json$', MyService(debug=settings.DEBUG), name='myservice'),
    )

    """
    __metaclass__ = JSONRPCServiceMeta  # Adds ``rpc_methods`` to class.

    # This probably won't ever need to chanage
    jsonrpc_version = u'2.0'

    # Override this to provide "application/json", etc, if desired.
    content_type = u'text/plain; encoding=utf-8'

    # When set to ``True`` this provides the Django request object as the
    # first argument of each RPC method (after ``self``), so that the RPC
    # methods can use request (e.g., ``request.META.get('REMOTE_ADDR', None)``)
    provide_request = False

    # Service Description: http://json-rpc.org/wd/JSON-RPC-1-1-WD-20060807.html
    service_sdversion = u'1.0'  # Service description version (always "1.0").
    service_name = None  # Name for service (e.g. "Search API").
    service_id = None  # Unique URI (http://tools.ietf.org/html/rfc3986).
    service_version = None  # Version of this service.
    service_summary = None  # Summarizes the purpose of this service.
    service_help = None  # URL to documentation for this service.
    service_address = None  # Endpoint for this service (ie, URL).

    # Allowed JSON-P padding names. Override in sub-classes to allow less/more.
    padding_names = ('callback', 'jsoncallback')

    def __init__(self, debug=False, can_get=False, http_errors=True, **kwargs):
        """
        When debug is ``True`` JSON output is formatted using indentation,
        and extra debug information, such as database queries, tracebacks, etc.
        are provided. When ``can_get`` is ``True`` all methods are available
        via GET (allowing JSON-P as well).
        """
        self.debug = debug
        self.can_get = can_get
        self.http_errors = http_errors
        # Turn on verbose formatting when ``verbose`` kwarg is provided and is
        # ``True``, else default to what debug is set to.
        self.verbose = kwargs.pop('verbose', self.debug)

    def __call__(self, request):
        """
        Calling a service requires an HTTP request object, and returns an HTTP
        response object, unless an unanticipated exception is encountered, and
        ``settings.DEBUG`` is set to ``True``, at which point the exception is
        raised to allow Django's built-in exception handling to take over.
        """
        # Get the IP address of the client for logging, etc.
        remote_addr = request.META['REMOTE_ADDR']

        # Get JSON-P padding from the request (if applicable).
        padding = self._json_padding_or_none(request)

        try:
            # Get the deserialized request JSON.
            json_req = self._get_json_req(request)
            # Get the ID.
            rid = self._valid_jsonrpc_id(json_req)
        except JSONRPCError, ex:
            return self._response(ex=ex, padding=padding)

        try:
            # Check the "jsonrpc" argument.
            self._validate_jsonrpc_verion(json_req)
        except JSONRPCError, ex:
            return self._response(ex=ex, rid=rid, padding=padding)

        try:
            # Get the method (we'll validate it later).
            method = self._valid_jsonrpc_method(json_req)
            # Get the parameters from the JSON object.
            params = self._valid_jsonrpc_params(json_req)
            # Call extra validation hook
            self._validate_extra(request, json_req)
            logger.debug(u'{i} calling method `{m}` on `{c}`'.format(
                i=remote_addr, m=method, c=type(self).__name__))
            # Attempt to dispatch the requested method.
            result = self._dispatch(request, method, params)
        except Exception, ex:
            if isinstance(ex, JSONRPCError):
                logger.debug(u'Error from {i}: {m}'.format(
                    i=remote_addr, m=ex.details))
            else:
                logger.exception(u'Error from {i}'.format(i=remote_addr))

            # If in debug mode and the request isn't an AJAX request and the
            # error is not a ``JSONRPCError``, we'll re-raise to allow Django's
            # default error handling take over
            if self.debug and not request.is_ajax():
                if not isinstance(ex, JSONRPCError):
                    raise

            # Return an error response
            return self._response(ex=ex, rid=rid, padding=padding)
        else:
            # Return successful response back to client.
            return self._response(result=result, rid=rid, padding=padding)

    @property
    def proc_descriptions(self):
        """
        Returns a list with procedure descriptions for each procedure.
        """
        return [m.description for m in self.methods.itervalues() if m.describe]

    @property
    def methods(self):
        """
        Returns the dictionary of methods attached to a ``JSONRPCService``
        during class creation (ones decorated by ``decorators.jrpc``).
        """
        return self.rpc_methods

    def _get_json_req(self, request):
        """
        Returns a JSON request object (as defined in JSON-RPC 2.0 spec), or
        raises a ``JSONRPCError``, if there is a problem with the request.
        """
        if request.method == 'GET':
            try:
                urlencoded_json = request.GET['json']
            except KeyError:
                raise InvalidRequestError(
                    details=u'In a GET request, JSON must be provided in a '
                    'URL argument named "json"')
            else:
                if not urlencoded_json:
                    raise InvalidRequestError(
                        u'The "json" URL argument cannot be empty')
            try:
                json_req = json.loads(urllib2.unquote(urlencoded_json))
                if not type(json_req) == dict:
                    raise InvalidRequestError(
                        details=u'The JSON provided must be an object')
                return json_req
            except ValueError:
                raise ParseError
        elif request.method == 'POST':
            try:
                json_req = json.loads(request.body)
            except ValueError:
                raise ParseError
            else:
                if not type(json_req) == dict:
                    raise InvalidRequestError(
                        details=u'The JSON provided must be an object')
                return json_req
        else:
            # This was a PUT or HEAD request.
            raise InvalidRequestError(
                details=u'Invalid request method. Method must be GET or POST, '
                'not {m}'.format(m=request.method))

    def _valid_jsonrpc_id(self, json_req):
        """
        Returns a valid ``int`` or ``str`` id from a JSON request object, or
        raises a ``JSONRPCError``, if the id is missing or of invalid type.
        """
        try:
            rid = json_req['id']
        except KeyError:
            raise InvalidRequestError(details=u'A request `id` is required')
        if not isinstance(rid, (int, basestring)):
            json_type = JSONType.by_python_type(type(rid))
            raise InvalidRequestError(
                details=u'Request `id` must be a `str` or `int` (string or '
                'integer), not `{t}`'.format(t=json_type))
        if isinstance(rid, basestring) and not len(rid) > 0:
            raise InvalidRequestError(
                details=u'The request `id` cannot be an empty string')
        return rid

    def _valid_jsonrpc_params(self, json_req):
        """
        Accepts a JSON request object and returns the params, or raises a
        ``JSONRCPRError``, if the params are missing or are of invalid type.
        """
        try:
            params = json_req['params']
        except KeyError:
            raise InvalidRequestError(
                details=u'`params` argument required, even when a method '
                'doesn\'t require any params')
        if type(params) not in (dict, list):
            raise InvalidParamsError(
                details=u'`params` argument must be an array or an object')
        return params

    def _valid_jsonrpc_method(self, json_req):
        """
        Accepts a JSON request object and returns the method, or raises a
        ``JSONRCPRError``, if the method is missing or is of invalid type.
        """
        try:
            method = json_req['method']
        except KeyError:
            raise InvalidRequestError(details=u'`method` argument required')
        if not type(method) in (unicode, str):
            raise InvalidRequestError(
                details=u'The `method` argument must be a string')
        return method

    def _validate_jsonrpc_verion(self, json_req):
        """
        Accepts a JSON request object and does nothing, or raises a
        ``JSONRPCError``, if the jsonrpc argument != self.jsonrpc_version.
        """
        try:
            version = json_req['jsonrpc']
        except KeyError:
            raise InvalidRequestError(details=u'`jsonrpc` argument required')
        if not version == self.jsonrpc_version:
            raise InvalidRequestError(
                details=u'`jsonrpc` argument must be exactly "{0}"'.format(
                    self.jsonrpc_version))

    def _json_padding_or_none(self, request):
        """
        Returns the padding string for JSON-P requests, if provided. If
        multiple allowed JSON-P padding strings are provided, the first will be
        returned. If none are provided, ``None`` is returned.
        """
        if request.method == 'GET':
            for name in self.padding_names:
                padding = request.GET.get(name, None)
                if padding is not None:
                    return padding
        return None

    def _validate_extra(self, request, json_req):
        """
        Everyone likes a hook... except for fish. This is a pre-method-call
        hook for providing custom validation. This should raise ``ServerError``
        when the desired conditions are not met.
        """
        pass

    def _response(self, ex=None, result=None, rid=None, padding=None):
        """
        Takes an ``Exception`` instance or a hashable result from a service
        method, an ID (if available), and JSON-P padding (if applicable).
        Returns an ``HTTPResponse`` instance. If no result or exception is
        provided, a general server error will be returned.
        """
        response = {
            'id': rid,
            'jsonrpc': self.jsonrpc_version,
        }
        if ex is not None:
            response['error'] = self._error_dict(ex)
            if self.http_errors:
                status = getattr(ex, 'http_status', 500)
            else:
                # This breaks the specification in an attempt to make errors
                # easily recoverable for AJAX clients by always returning 200.
                status = 200
        else:
            response['result'] = result
            status = 200

        if self.debug:
            # Add a ``debug`` object with DB queries to the response.
            response['debug'] = {
                'queries': {
                    'count': len(connection.queries),
                    'data': connection.queries
                }
            }

        if self.verbose:
            # Turn on verbose JSON formatting with indentation.
            json_output = json.dumps(response, indent=4, cls=RobustEncoder)
        else:
            # Turn off verbose JSON formatting and remove indentation.
            json_output = json.dumps(
                response, separators=(',', ':'), cls=RobustEncoder)

        if padding is not None:  # Add the JSON-P padding to response.
            response = u'{p}({j})'.format(p=padding, j=json_output)
        else:
            response = json_output
        return HttpResponse(response, status=status,
                            content_type=self.content_type)

    @staticmethod
    def _valid_params(method, params):
        """
        Validates type, and number of params. Raises ``ParamsError`` when a
        missmatch is found.
        """
        # ``list`` (JavaScript Array) based "params"
        if type(params) is list:
            params_list = []
            for idx, defined in enumerate(method.rpc_params):
                try:
                    provided = params[idx]
                except IndexError:
                    # JSON-RPC 1.1 spec states that parameters should be
                    # replaced with a "nil" object, but instead let's raise an
                    # exception, unless the param is marked optional with "?".
                    if defined['optional']:
                        provided = None  # Set value to "nil" (None)
                    else:
                        raise InvalidParamsError(
                            details=u'Parameter `{0}` is required, but was '
                            'not provided'.format(defined['name']))
                if not JSONType(defined['type']) == type(provided):
                    if defined['optional'] and provided is None:
                        pass  # Optional params are allowed to be "nil"
                    else:
                        raise InvalidParamsError(
                            details=u'`{0}` param should be of type '
                            '{1}'.format(defined['name'], defined['type']))
                params_list.append(provided)
            return params_list
        # ``dict`` (JavaScript object) based "params"
        elif type(params) is dict:
            params_dict = {}
            for defined in method.rpc_params:
                name = defined['name']
                try:
                    provided = params[name]
                except KeyError:
                    if defined['optional']:
                        provided = None  # Set value to "nil" (None)
                    else:
                        raise InvalidParamsError(
                            details=u'Parameter `{0}` is required, but was '
                            'not provided'.format(defined['name']))
                if not JSONType(defined['type']) == type(provided):
                    if defined['optional'] and provided is None:
                        pass  # Optional params are allowed to be "nil"
                    else:
                        raise InvalidParamsError(
                            details=u'`{0}` param should be of type '
                            '{1}'.format(defined['name'], defined['type']))
                params_dict[name] = provided
            return params_dict
        else:
            raise InvalidParamsError(
                details=u'The `params` argument must be an array or object')

    def _error_dict(self, ex):
        """
        Returns a ``dict`` in the format of an JSON-RPC error object, with
        extra "data", including a full traceback when in development.
        """
        error = {}
        if isinstance(ex, JSONRPCError):
            error['code'] = ex.code
            error['message'] = ex.message
        else:
            ex = InternalError(details=u'An internal error has occurred')
            error['code'] = ex.code
            error['message'] = ex.message
        error['data'] = {
            'details': getattr(ex, 'details', None)
        }
        if self.debug:
            # Add traceback and exception type to the error dict for debugging
            # even ``JSONRPCError`` exceptions.
            error['data']['traceback'] = traceback.format_list(
                traceback.extract_tb(sys.exc_info()[2]))
        return error

    def _dispatch(self, request, method_name, params):
        """
        Returns the result of calling the method via it's name from
        ``self.methods`` with the provided arguments.
        """
        try:
            method = self.methods[method_name]
        except KeyError:
            raise MethodNotFoundError(
                details=u'Method `{0}` not found'.format(method_name))
        if request.method == 'GET' and not self.can_get:
            raise MethodNotFoundError(
                details=u'Method `{0}` was either not found, or is not '
                'available via GET requests'.format(method_name))

        # Validate the parameters before calling the method, and remove extra
        # parameters (per JSON-RPC 1.1 specification).
        params = self._valid_params(method, params)

        # Call method with params provided as a **kwargs
        if type(params) is dict:
            if self.provide_request:
                # Include the request as the first argument
                return method(self, request, **params)
            # Don't include the request
            return method(self, **params)

        # Call the method with params provided as *args
        if self.provide_request:
            # Include the request as the first argument
            return method(self, request, *params)
        # Don't include the request
        return method(self, *params)

    @jrpc('system.describe() -> <obj>')
    def describe(self, request):
        """
        Describes the system per the specification (from JSON-RPC 1.1) at
        http://json-rpc.org/wd/JSON-RPC-1-1-WD-20060807.html, with a few minor
        differences (additions).
        """
        return {
            'sdversion': self.service_sdversion,
            'name': self.service_name,
            'id': self.service_id,
            'version': self.service_version,
            'summary': self.service_summary,
            'help': self.service_help,
            'address': self.service_address,
            'procs': self.proc_descriptions
        }
