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


class TestDisk(RhevmTest): 

    def test_crud(self):
        client = self.client
        headers = self.headers
        vm = { 'name': 'test-%s' % random.randint(0, 1000000),
               'template': self.template,
               'cluster': self.cluster,
               'type': 'server' }
        body = yaml.dump(vm)
        headers['Content-Type'] = 'text/yaml'
        client.request('POST', '/api/vms', body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        assert response.getheader('Location')
        vmpath = urlparse(response.getheader('Location')).path
        disk = { 'size': 8 }
        body = yaml.dump(disk)
        client.request('POST', '%s/disks' % vmpath, body=body,
                       headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        assert response.getheader('Content-Type') == 'text/yaml'
        assert response.getheader('Location')
        location = response.getheader('Location')
        diskpath = urlparse(response.getheader('Location')).path
        del headers['Content-Type']
        client.request('GET', '%s/disks' % vmpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type') == 'text/yaml'
        result = yaml.load(response.read())
        assert len(result) == 1
        assert result[0]['size'] == 8
        client.request('GET', diskpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type') == 'text/yaml'
        data = yaml.load(response.read())
        assert data['size'] == 8
        client.request('DELETE', diskpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        client.request('DELETE', diskpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.NOT_FOUND
        client.request('DELETE', vmpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
