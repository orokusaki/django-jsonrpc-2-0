from setuptools import setup, find_packages


# Dynamically calculate the version based on jsonrpc.VERSION
version = '.'.join([str(v) for v in __import__('jsonrpc').VERSION])

setup(
    name='jsonrpc',
    description='A JSON-RPC 2.0 server that is loosely coupled to Django',
    version=version,
    author='Michael Angeletti',
    author_email='michael [at] angelettigroup [dot] com',
    url='http://github.com/orokusaki/django-jsonrpc-2-0/',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities'
    ],
    packages=find_packages(),
)
