from decimal import Decimal


class JSONType(object):
    """Similar to ``type`` for comparison purposes of a JSON object.

    Usage:

    >>> x = 1
    >>> # Next line checks that ``x`` is a JSON "num" object.
    >>> JSONType('num') == type(x)
    True
    >>> x = 'Hello, World'
    >>> JSONType('str') == type(x)
    True
    >>> JSONType('spam')
    Traceback (most recent call last):
    ...
    ValueError: Invalid key "spam" provided.

    """
    json_types = {
        'bit': (bool,),
        'num': (float, int, Decimal),
        'str': (basestring, str, unicode),
        'arr': (list,),
        'obj': (dict,),
        'any': (bool, float, int, Decimal, str, unicode, list, dict, None),
        'nil': (None,)
    }

    def __init__(self, type_key):
        """Provide a key (str). This indicates which type/s this ``JSONType``
        should be mapped to (e.g. 'bit' maps to ``bool``, etc.)."""
        try:
            self._types = self.json_types[type_key]
        except KeyError:
            raise ValueError('``type_key`` "{0}" is invalid.'.format(type_key))

    def __eq__(self, other):
        return other in self._types


if __name__ == '__main__':
    import doctest
    doctest.testmod()
