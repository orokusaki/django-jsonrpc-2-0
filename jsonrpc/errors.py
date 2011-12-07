"""
JSON-RPC 2.0 exceptions (including custom exceptions), based on the
specificaction at http://groups.google.com/group/json-rpc/web/json-rpc-2-0.
"""
class JSONRPCError(Exception):
    """A general JSON-RPC error which defaults to the ``ServerError`` specs."""
    code = -32603
    message = u'Server error'
    http_status = 500

    def __init__(self, message=None, details=None, *args, **kwargs):
        super(JSONRPCError, self).__init__(message)
        if message is not None:
            self.message = message
        if details is not None:
            self.details = details


class ParseError(JSONRPCError):
    code = -32700
    message = u'Parse error'
    details = (u'Invalid JSON was received by the server. An error occurred '
               'on the server while parsing the JSON text.')


class InvalidRequestError(JSONRPCError):
    code = -32600
    message = u'Invalid request'
    http_status = 400
    details = u'The JSON sent is not a valid Request object.'


class MethodNotFoundError(JSONRPCError):
    """The requested JSON-RPC method is not registered with the service."""
    code = -32601
    message = u'Method not found'
    http_status = 404
    details = u'The method does not exist / is not available.'


class InvalidParamsError(JSONRPCError):
    """An error raised when incorrect arguments are given, not enough arguments
    are given, or when positional and keyword arguments are given."""
    code = -32602
    message = u'Invalid params'


class InternalError(JSONRPCError):
    """Internal error with JSON-RPC server."""
    code = -32603
    message = u'Internal error'
    details = u'Internal JSON-RPC error.'


# Custom errors (codes -32099 to -32000 are reserved for this):

class ServerError(JSONRPCError):
    """A General error (in case something goes wrong with the app)."""
    code = -32099
    message = u'Server error'
