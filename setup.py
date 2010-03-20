#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from setuptools import setup, Extension


setup(
    name = 'rhevm-api',
    version = '0.1',
    description = 'A REST mapping of the PowerShell API of RHEV-M.',
    author = 'Geert Jansen',
    author_email = 'geert@boskant.nl',
    url = 'http://bitbucket.org/geertj/rhevm-api',
    license = 'MIT',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License : = OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application' ],
    package_dir = { '': 'lib' },
    packages = ['rhevm', 'rhevm.test'],
    test_suite = 'nose.collector',
    entry_points = { 'console_scripts': [ 'rhevmapi = rhevm.server:main' ] },
    install_requires = ['argproc >= 1.0', 'winpexpect >= 1.0',
                        'python-rest >= 1.0', 'pyyaml >= 3.09']
)
