from decimal import Decimal


class JSONType(object):
    """
    A mapping of JSON type to Python types, which provides equality checking,
    much like ``type``.

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
    ValueError: Invalid key "spam" provided

    """
    json_types = {
        'bit': (bool,),
        'num': (float, int, Decimal),
        'str': (basestring, str, unicode),
        'arr': (list,),
        'obj': (dict,),
        'nil': (None,),
        'any': (bool, float, int, Decimal, str, unicode, list, dict, None),
    }

    def __init__(self, type_key):
        """Provide a key (str). This indicates which type/s this ``JSONType``
        should be mapped to (e.g. 'bit' maps to ``bool``, etc.)."""
        try:
            self._types = self.json_types[type_key]
        except KeyError:
            raise ValueError('Invalid key "{0}" provided'.format(type_key))
        else:
            self._json_type_code = type_key

    def __eq__(self, other):
        """
        Returns whether or not the provided type is in the tuple of supported
        types for self.
        """
        return other in self._types

    @classmethod
    def by_python_type(cls, p_type):
        """
        Takes any Python type, and returns an appropriate ``JSONType``. If the
        type provided isn't supported, a ``ValueError`` is raised.
        """
        for key, python_types in cls.json_types.iteritems():
            if not key == 'any' and p_type in python_types:
                return cls(key)

        raise ValueError(u'{t} is not a valid JSON type'.format(t=p_type))


    def __unicode__(self):
        return self._json_type_code


if __name__ == '__main__':
    import doctest
    doctest.testmod()
