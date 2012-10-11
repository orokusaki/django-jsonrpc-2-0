import json
import decimal
from datetime import datetime, date, time

from django.utils.functional import Promise
from django.utils.encoding import force_unicode


class RobustEncoder(json.JSONEncoder):
    """
    JSON encoder with support for ``Promise``, ``datetime``, ``date``,
    ``time``, and ``Decimal`` objects.
    """
    def default(self, obj):
        """
        Provides custom functionality for certain types, defaulting to the
        built-in encoder.
        """
        # Promise (e.g., ``ugettext_lazy``), and Decimal both get unicoded
        if isinstance(obj, (Promise, decimal.Decimal)):
            return force_unicode(obj)

        # datetime, time, and date get isoformatted and unicoded
        if isinstance(obj, (datetime, time, date)):
            return unicode(obj.isoformat())

        return super(RobustEncoder, self).default(obj)
