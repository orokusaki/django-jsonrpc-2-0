import json
from decimal import Decimal
from datetime import datetime, date, time


class JSONRPCEncoder(json.JSONEncoder):
    """
    JSON encoder with datetime, date, time, and decimal support.
    """
    def default(self, obj):
        """
        Provides custom functionality for certain types, defaulting to the
        built-in encoder.
        """
        if type(obj) in (Decimal, datetime, time, date):
            return unicode(obj)
        return super(JSONRPCEncoder, self).default(obj)
