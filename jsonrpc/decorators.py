"""Provides ``jrpc`` for registering methods with a ``JSONRPCService``."""
from functools import wraps
from signatures import name_from_signature, params_from_signature
from signatures import return_type_from_signature


def jrpc(signature, safe=False, describe=True, summary=None, idempotent=False,
         docs_url=None):
    """Use to wrap methods that belong to a ``service.JSONRPCService``. Methods
    which are wrapped in this decorator will be added to the service for access
    via JSON-RPC.

    Usage:

    >>> #      [name] [required]  [optional] [rtn type]
    >>> @jrpc('get_sum(aye=<num>, bee=<num>?) -> <num>')
    ... def add(a, b=1):
    ...     return a + b
    ...
    >>>

    """
    if callable(signature):
        raise TypeError(u'The ``jrpc`` decorator must be provided with a '
                        'method signature.')

    def decorator(method):
        """Adds a ``rpc_method_name`` attribute to methods decorated, giving
        the method json-rpc method name (this is used by ``JSONRPCServiceMeta``
        to register this method as a supported method. This requires a
        ``JSONRPCService`` to register available methods on class creation,
        instead of instantiation. Use ``describe=False`` to hide a method from
        the service description."""
        method.rpc_method_name = name_from_signature(signature)
        method.rpc_params = [{'name': p[0], 'type': p[1], 'optional': p[2]} for
            p in params_from_signature(signature)]
        method.rpc_safe = safe
        method.describe = describe
        method.return_type = return_type_from_signature(signature)

        # Procedure description (for ``system.describe``).
        method.description = {
            'name': method.rpc_method_name,
            'summary': summary,
            'help': docs_url,
            'idempotent': idempotent,
            'params': method.rpc_params,
            'return': method.return_type,
            'signature': signature
        }

        @wraps(method)
        def wrapper(*args, **kwargs):
            """Returns the value returned by calling the actual method."""
            return method(*args, **kwargs)
        return wrapper
    return decorator
