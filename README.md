Django JSON-RPC 2.0
===================

Requirements
------------

* Python 2.6 +
* Django 1.4 +

Example Usage
-------------

A basic example looks like::

    # foo_app/api.py
    from jsonrpc.service import JSONRPCService
    from jsonrpc.decorators import jrpc


    class FooAPI(JSONRPCService):
        # Call all API methods with `request` as the first argument
        provide_request = True

        @jrpc('get_sum(foo=<num>, bar=<num>?) -> <num>')
        def get_sum(self, request, foo, bar=2):
            """
            No magic here, just a normal method.
            """
            return foo + bar

        def some_non_public_method(self):
            """
            Only explicitly exposed methods are exposed, so you can do what you
            want elsewhere.
            """
            ... perform top secret tasks here :)

    # urls.py
    # =======
    from django.conf import settings
    from django.views.decorators.csrf import csrf_exempt
    from foo_app.api import FooAPI


    foo_api = FooAPI(debug=settings.DEBUG)

    urlpatterns = patterns('',
        url(r'^foo.json$', csrf_exempt(foo_api), name='foo_api'),
    )

    # Example POST to /foo_app/foo.json

    REQ -> {"jsonrpc": "2.0", "method": "get_sum", "params": {"foo": 3}, "id": 1}

    RES <- {"jsonrpc": "2.0", "result": 5, "id": 1}

    # In GET requests, the JSON-RPC over HTTP spec calls for arguments to be
    # provided in a format like ?params=<params>&method=<method>. Since there
    # is no spec for JSON-RPC 2.0 over HTTP, I've taken some liberties and made
    # things a bit simpler, allowing you to simply URL encode the exact same
    # JSON request object that you'd otherwise POST to the server, and provide
    # it in a "json" query param (e.g. ?json={...).

    # Example GET

    REQ -> /rpc.json?json=%7b%22jsonrpc%22%3a+%222.0%22%2c+%22method%22%3a+%22a
                     dd_ints%22%2c+%22params%22%3a+%5b50%2c+25%5d%2c+%22id%22%3
                     a+1%7d
    RES <- {"jsonrpc": "2.0", "result": 75, "id": 1}

    # Example GET, with padding (ie, JSONP)

    REQ -> /rpc.json?json=%7b%22jsonrpc%22%3a+%222.0%22%2c+%22method%22%3a+%22a
                     dd_ints%22%2c+%22params%22%3a+%5b50%2c+25%5d%2c+%22id%22%3
                     a+1%7d&jsoncallback=mycallback
    RES < - mycallback({"jsonrpc": "2.0", "result": 75, "id": 1})

That's it. You don't need to do anything special, define a queryset method,
register anything, etc. Just write normal methods, and wrap the ones you wish
to expose with the `@jrpc` decorator (as shown above). If you define a method
and wrap it in `@jrpc` and the syntax of the method signature you provide to
`@jrpc` is incorrect, it'll raise an error (during "compile" time).

Features
--------

When your API is in debug mode you'll receive a `debug` key in the response
JSON object, which contains information about the queries that were run during
the request cycle, and tracebacks for exceptions.

Access the `request` by setting `provide_request` to `True` on your service
class. Then, write your API methods to accept `request` as the first argument.

Supports JSON-P, with any callback name you'd like to use, with an attribute
`padding_names` on your API class (default is `('callback', 'jsoncallback')`)

Freebies
--------

Every API you create comes with a method called `system.describe` which returns
a JSON-RPC 2.0 spec description of the API's methods, the arguments they take,
whether each argument is optional, which type the argument should be, etc. This
method can be overridden just like any other.

:author: Michael Angeletti
:date: 2013/01/24
