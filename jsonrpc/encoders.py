import json
from decimal import Decimal


class JSONRPCEncoder(json.JSONEncoder):
    """
    JSON encoder with decimal support.
    """
    def default(self, obj):
        """
        If a `Decimal` is provided, it is converted into `unicode`.
        """
        if isinstance(obj, Decimal):
            return unicode(obj.quantize(Decimal('0.00')))
        return super(JSONRPCEncoder, self).default(obj)
