"""
Utilities for processing JSON-RPC method signatures, and their types.
"""
import re

from .jsontype import JSONType


# Signature: ``name(foo=<type>, bar=<type>, baz=<type>) -> <type>``.
SIG_RE = r'^(?P<name>[\w\.]+)\((?P<args>.*)\)(?: -> <(?P<rtype>\w+)>)$'

# Arguments only: ``foo=<type>, bar=<type>, baz=<type>``.
ARG_RE = r'^(?P<name>\w+)=<(?P<type>\w+)>(?:(?P<optional>[\?])?)$'


def name_from_signature(sig):
    """
    Takes a method signature. Returns the method's name.

    Usage:

    >>> name_from_signature('spam_eggs(arg=<str>, arg2=<str>) -> <str>')
    'spam_eggs'
    >>>

    """
    try:
        return re.match(SIG_RE, sig).group('name')
    except AttributeError:
        raise ValueError(
            u'Method signature syntax "{sig}" is incorrect.'.format(sig=sig))


def params_from_signature(sig):
    """
    Takes a method signature, such as ``sig_example``. Returns a list of
    3-tuples, each with a parameter, it's type, and whether it's optional.

    Usage:

    >>> params_from_signature('spam_eggs(arg=<str>, arg2=<str>) -> <str>')
    [('arg', 'str', False), ('arg2', 'str', False)]
    >>>

    """
    try:
        args = re.match(SIG_RE, sig).group('args')
    except AttributeError:
        raise ValueError(
            u'Method signature syntax "{sig}" is incorrect.'.format(sig=sig))
    try:
        lot = []  # Return value ``[(name, type, optional), ...]``
        if len(args) > 0:
            args = args.split(', ')
            opt_flag = False
            for arg in args:
                match = re.match(ARG_RE, arg)
                if match.group('optional') is not None:
                    optional = True
                    opt_flag = True
                else:
                    if opt_flag:  # Optional params already encountered.
                        raise ValueError(
                            u'Required params must come before optional '
                            'params in "{sig}".'.format(sig=sig))
                    optional = False
                lot.append(
                    (match.group('name'), match.group('type'), optional))
        return lot
    except AttributeError:
        raise ValueError(
            u'Method signature params syntax "{sig}" is incorrect '.format(
                sig=sig))


def return_type_from_signature(sig):
    """
    Returns the string representation of the JSON type returned by a method
    (for use in ``jsonrpc.types.JSONRPCType``), based on a provided signature.

    Usage:

    >>> return_type_from_signature('spam_eggs(arg=<str>, arg2=<str>) -> <str>')
    'str'
    >>>

    """
    try:
        r_type = re.match(SIG_RE, sig).group('rtype')
    except AttributeError:
        raise ValueError(
            u'Method signature syntax "{sig}" is incorrect.'.format(sig=sig))
    if not r_type in JSONType.json_types:
        raise ValueError(
            u'Invalid return type "{r_type}". Allowed types are: '
            '{allowed}.'.format(
                r_type=r_type, allowed=', '.join(JSONType.json_types)))
    return r_type
