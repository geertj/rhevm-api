#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import threading
from nose.tools import assert_raises

from rhevm.powershell import PowerShell, Error
from rhevm.test.base import RhevmTest


class TestPowerShell(RhevmTest):

    def setUp(self):
        username = self.config.get('test', 'username')
        password = self.config.get('test', 'password')
        self.ps = PowerShell()
        self.ps.execute('Login-User %s %s' % (username, password))

    def tearDown(self):
        self.ps.close()

    def test_basic(self):
        objects = self.ps.execute('Select-Event')

    def test_error(self):
        try:
            self.ps.execute('Add-DataCenter -name test -datacentertype test')
        except Error, e:
            assert len(e.message) > 0
            assert len(e.category) > 0
            assert len(e.id) > 0
        else:
            raise AssertionError, 'Test did not raise exception.'
