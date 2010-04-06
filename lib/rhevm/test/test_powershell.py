#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from nose import SkipTest
from nose.tools import assert_raises

from rhevm import *
from rhevm.test.base import RhevmTest, local_only, require_rhev


class TestPowerShell(RhevmTest):

    @local_only
    def test_short_form(self):
        result = self.powershell.execute('Get-Version')
        assert len(result) == 1
        assert 'Major' in result[0]
        assert 'Minor' in result[0]
        assert 'Build' in result[0]
        assert 'Revision' in result[0]

    @local_only
    def test_long_form(self):
        result = self.powershell.execute('Select-Event | '
                                         'Select-Object -First 1')
        assert len(result) == 1
        assert 'Id' in result[0]
        assert 'LogTime' in result[0]
        assert 'LogType' in result[0]
        assert 'Message' in result[0]
        assert 'Severity' in result[0]

    @local_only
    def test_multiple_entries(self):
        result = self.powershell.execute('Select-Event | '
                                         'Select-Object -First 10')
        print 'RESULT', len(result)
        assert len(result) == 10
    
    @local_only
    def test_zero_entries(self):
        result = self.powershell.execute('Select-Event | '
                                         'Select-Object -First 0')
        assert len(result) == 0

    @local_only
    @require_rhev('2.2')
    def test_nested_object(self):
        result = self.powershell.execute('Select-DataCenter')
        assert isinstance(result[0]['CompatibilityVersion'], dict)
        assert 'Major' in result[0]['CompatibilityVersion']
        assert 'Minor' in result[0]['CompatibilityVersion']

    @local_only
    def test_continuation(self):
        self.powershell.execute('$dc = Select-DataCenter'
                                ' | Select-Object -First 1')
        desc = 'long line that overflows for sure.' * 5
        self.powershell.execute('$dc.description = "%s"' % desc)
        result = self.powershell.execute('Out-Host -InputObject $dc')
        assert len(result) == 1
        assert result[0]['Description'] == desc

    @local_only
    def test_error(self):
        try:
            # Generate an exception by passing an unknown argument
            self.powershell.execute('Add-DataCenter -foo bar')
        except PowerShellError, e:
            assert len(e.message) > 0
            assert len(e.category) > 0
            assert len(e.id) > 0
        else:
            raise AssertionError, 'Test did not raise exception.'
