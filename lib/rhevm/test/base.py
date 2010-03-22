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

from httplib import HTTPConnection
from ConfigParser import ConfigParser

from rest.server import make_server
from rhevm.powershell import PowerShell
from rhevm.application import RhevmApp


class TestError(Exception):
    pass


class RhevmTest(object):

    @classmethod
    def setUpClass(cls):
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
        if not config.has_option('test', 'username') or \
                not config.has_option('test', 'password'):
            raise TestError, 'You need to specify both username and ' \
                        'password in the test config.'
        cls.config = config
        cls.datacenter = config.get('test', 'datacenter')
        cls.cluster = config.get('test', 'cluster')
        cls.template = config.get('test', 'template')

    def setUp(self):
        username = self.config.get('test', 'username')
        password = self.config.get('test', 'password')
        self.powershell = PowerShell()
        self.powershell.execute('Login-User %s %s' % (username, password))
        self.server = make_server('localhost', 0, RhevmApp)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        time.sleep(0.5)
        self.client = HTTPConnection(*self.server.address)
        auth = '%s:%s' % (username, password)
        auth = 'Basic %s' % auth.encode('base64').rstrip()
        self.headers = { 'Authorization': auth,
                         'Accept': 'text/yaml',
                         'Host': 'localhost:%s' % self.client.port }

    def tearDown(self):
        self.client.close()
        self.powershell.close()
        self.server.shutdown()
        self.thread.join()
