#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import sys
import os
import os.path
import time
import logging
import threading
import urlparse

from httplib import HTTPConnection
from ConfigParser import ConfigParser

from nose import SkipTest
from rest import http
from rest.server import make_server
from rhevm import *
from rhevm.server import _setup_logging


def local_only(func):
    """Decorator that skips a test if we're testing remotely."""
    def run_test(self):
        if 'url' in self.config:
            raise SkipTest, 'Test skipped in remote test mode.'
        func(self)
    run_test.__name__ = func.__name__
    return run_test

def require_rhev(version):
    """Skip a test if we don't have a minimum RHEV version."""
    version = map(int, version.split('.'))
    def decorator(func):
        def run_test(self):
            result = self.powershell.execute('Get-Version')
            current = (result[0]['Major'], result[0]['Minor'],
                       result[0]['Build'], result[0]['Revision'])
            if not current > version:
                raise SkipTest, 'Test skipped for this RHEV-M version.'
            func(self)
        run_test.__name__ = func.__name__
        return run_test
    return decorator

class TestError(Exception):
    pass


class RhevmTest(object):

    @classmethod
    def setUpClass(cls):
	_setup_logging(True)
        myfile = os.path.abspath(__file__)
        dir, tail = os.path.split(myfile)
        while tail:
            setup = os.path.join(dir, 'setup.py')
            if os.access(setup, os.R_OK):
                break
            dir, tail = os.path.split(dir)
        else:
            raise TestError, 'Could not find package directory.'
        cfgfile = os.path.join(dir, 'test.conf')
        config = ConfigParser()
        success = config.read(cfgfile)
        if cfgfile not in success:
            raise TestError, 'Could not read test config at %s.' % cfgfile
        cls.config = dict(config.items('test'))
        cls.datacenter = config.get('test', 'datacenter')
        cls.cluster = config.get('test', 'cluster')
        cls.template = config.get('test', 'template')

    def setUp(self):
        username = self.config['username']
        domain = self.config['domain']
        password = self.config['password']
        url = self.config.get('url')
        if url:
            parsed = urlparse.urlparse(url)
            if ':' in parsed.netloc:
                host, port = parsed.netloc.split(':')
            elif parsed.scheme == 'http':
                host, port = parsed.netloc, http.PORT
            elif parsed.scheme == 'https':
                host, port = parsed.netloc, http.SSL_PORT
            else:
                raise ValueError, 'Illegal URL: %s' % url
            self.client = HTTPConnection(host, port)
            self.server = None
            self.thread = None
            self.powershell = None
        else:
            self.server = make_server('localhost', 0, RhevmApp)
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.start()
            time.sleep(0.5)
            self.client = HTTPConnection(*self.server.address)
            self.powershell = PowerShell()
            self.powershell.execute('Login-User -UserName %s -Domain %s'
                                    ' -Password %s'
                                    % (username, domain, password))
        auth = '%s@%s:%s' % (username, domain, password)
        auth = 'Basic %s' % auth.encode('base64').rstrip()
        self.headers = { 'Authorization': auth,
                         'Accept': 'text/yaml',
                         'Host': 'localhost:%s' % self.client.port }

    def tearDown(self):
        self.client.close()
        if self.powershell:
            self.powershell.terminate()
        if self.server:
            self.server.shutdown()
        if self.thread:
            self.thread.join()
