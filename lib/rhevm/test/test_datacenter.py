#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import random

import httplib as http
from xml.etree import ElementTree as etree
from xml.etree.ElementTree import Element, SubElement

from rhevm.test.base import RhevmTest


class TestDataCenter(RhevmTest): 

    def test_list(self):
        ref = self.ps.execute('Select-DataCenter')
        self.client.request('GET', '/api/datacenters', headers=self.headers)
        response = self.client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type', 'text/xml')
        xml = etree.fromstring(response.read())
        assert xml.tag == 'datacenters'
        assert len(xml) == len(ref)

    def test_show(self):
        ref = self.ps.execute('Select-DataCenter')
        id = ref[0]['DataCenterId']
        self.client.request('GET', '/api/datacenters/%s' % id,
                headers=self.headers)
        response = self.client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type', 'text/xml')
        xml = etree.fromstring(response.read())
        assert xml.tag == 'datacenter'

    def test_create(self):
        client = self.client
        headers = self.headers
        root = Element('datacenter')
        elem = SubElement(root, 'type')
        elem.text = 'NFS'
        elem = SubElement(root, 'name')
        elem.text = 'NewName-%s' % random.randint(0, 1000000000)
        body = etree.tostring(root)
        headers['Content-Type'] = 'text/xml'
        print 'client content length: %s' % len(body)
        print body
        client.request('POST', '/api/datacenters', body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        assert response.getheader('Location')
