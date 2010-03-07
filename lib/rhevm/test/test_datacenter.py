#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import httplib as http
from xml.etree import ElementTree as etree

from rhevm.test.base import RhevmTest


class TestDataCenter(RhevmTest): 

    def test_list(self):
        ref = self.ps.execute('Select-DataCenter')
        self.client.request('GET', '/api/datacenters', headers=self.headers)
        response = self.client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type', 'text/xml')
        xml = etree.fromstring(response.read())
        assert len(xml) == len(ref)
