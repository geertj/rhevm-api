#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import random
from urlparse import urlparse
import yaml

from rest import http
from rhevm.test.base import RhevmTest


class TestNic(RhevmTest): 

    def test_crud(self):
        client = self.client
        headers = self.headers
        vm = { 'name': 'test-%s' % random.randint(0, 1000000),
               'template': self.template,
               'cluster': self.cluster }
        body = yaml.dump(vm)
        headers['Content-Type'] = 'text/yaml'
        client.request('POST', '/api/vms', body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        assert response.getheader('Location')
        vmpath = urlparse(response.getheader('Location')).path
        nic = { 'name': 'eth0',
                'type': 'e1000',
                'network': 'rhevm' }
        body = yaml.dump(nic)
        client.request('POST', '%s/nics' % vmpath, body=body,
                       headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        assert response.getheader('Content-Type') == 'text/yaml'
        assert response.getheader('Location')
        location = response.getheader('Location')
        nicpath = urlparse(response.getheader('Location')).path
        del headers['Content-Type']
        client.request('GET', '%s/nics' % vmpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type') == 'text/yaml'
        result = yaml.load(response.read())
        assert len(result) == 1
        assert result[0]['name'] == nic['name']
        client.request('GET', nicpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type') == 'text/yaml'
        data = yaml.load(response.read())
        assert data['name'] == 'eth0'
        assert data['type'] == 'e1000'
        assert data['network'] == 'rhevm'
        client.request('DELETE', nicpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        client.request('DELETE', nicpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.NOT_FOUND
        client.request('DELETE', vmpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
