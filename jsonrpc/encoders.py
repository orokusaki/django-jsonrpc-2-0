import json
import decimal
from datetime import datetime, date, time

from django.db import models
from django.db.models.query import QuerySet
from django.core.serializers import serialize
from django.utils.functional import Promise
from django.utils.encoding import force_unicode


class RobustEncoder(json.JSONEncoder):
    """
    JSON encoder with support for ``QuerySet``, ``Model``, ``Promise``,
    ``datetime``, ``date``, ``time``, and ``Decimal`` objects.
    """
    def default(self, obj):
        """
        Provides custom functionality for certain types, defaulting to the
        built-in encoder.
        """
        # QuerySet
        if isinstance(obj, QuerySet):
            return json.loads(serialize('json', obj))

        # Model
        if isinstance(obj, models.Model):
            return json.loads(serialize('json', [obj]))[0]

        # Promise (e.g., ``ugettext_lazy``), and Decimal both get unicoded
        if isinstance(obj, (Promise, decimal.Decimal)):
            return force_unicode(obj)

        # datetime, time, and date get isoformatted and unicoded
        if isinstance(obj, (datetime, time, date)):
            return unicode(obj.isoformat())

        return super(RobustEncoder, self).default(obj)
