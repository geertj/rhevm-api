#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import random
import httplib as http
import yaml

from urlparse import urlparse
from xml.etree import ElementTree as etree
from xml.etree.ElementTree import Element, SubElement

from rhevm.test.base import RhevmTest


class TestVm(RhevmTest): 

    def test_simple(self):
        client = self.client
        headers = self.headers
        headers['Content-Type'] = 'text/yaml'
        vm = { 'name': 'test-%s' % random.randint(0, 1000000),
               'template': 'Blank',
               'cluster': 'Main' }
        body = yaml.dump(vm)
        client.request('POST', '/api/vms', body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        location = response.getheader('Location')
        assert location is not None
        url = urlparse(location)
        del vm['template']
        vm['memory'] = 512
        vm['description'] = 'My new virtual machine'
        body = yaml.dump(vm)
        client.request('PUT', url.path, body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        client.request('GET', url.path, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type') == 'text/yaml'
        data = yaml.load(response.read())
        assert data['memory'] == '512'
        assert data['description'] == 'My new virtual machine'
        client.request('DELETE', url.path, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        client.request('DELETE', url.path, headers=headers)
        response = client.getresponse()
        assert response.status == http.NOT_FOUND
