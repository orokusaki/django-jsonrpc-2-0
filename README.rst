===============
Django-JSON-RPC-2.0
===============

Currently being used by *a* production site, built-in unit tests coming soon...


Requirements
============

* Python 2.6+
* Django 1.2+

Example Usage
====================

A basic example looks like::

    # foo_app/api.py
    from jsonrpc.service import JSONRPCService
    from jsonrpc.decorators import jrpc


    class FooAPI(JSONRPCService):
        @jrpc('get_sum(foo=<num>, bar=<num>?) -> <num>')  # bar arg is optional
        def get_sum(self, foo, bar=2):
            return foo + bar

        def private_foo(self):
            return u'Hello, World'

    # urls.py
    # =======
    from django.views.decorators.csrf import csrf_exempt
    from foo_app.api import FooAPI


    foo_api = FooAPI(debug=settings.DEBUG)

    urlpatterns = patterns('',
        url(r'^foo.json$', csrf_exempt(foo_api), name='foo_api'),
    )

That's it. You don't need to do anything special, define a queryset method,
register anything, etc. Just write normal methods.

More docs coming soon...

Features
=============

When DEBUG is on, you'll receive a 'debug' key in the object that's returned
that contains (still to spec) information about the queries that were run, and
full tracebacks for any exceptions.

Supports JSON-P, with any callback name you'd like to use (docs coming soon :)


Freebies
=============

Every API you create comes with a method called 'system.describe' which returns
a JSON-RPC 2.0 spec description of the API's methods, the arguments they take,
whether each argument is optional, which type the argument should be, etc. This
method can be overridden just like any other.

:author: Michael Angeletti
:date: 2011/05/03
