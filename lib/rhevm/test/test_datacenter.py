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


class TestDataCenter(RhevmTest): 

    def test_crud(self):
        client = self.client
        headers = self.headers
        headers['Content-Type'] = 'text/yaml'
        data = { 'name': 'test-%s' % random.randint(0, 1000000000),
                 'type': 'NFS' }
        body = yaml.dump(data)
        client.request('POST', '/api/datacenters', body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        location = response.getheader('Location')
        assert location is not None
        url = urlparse(location)
        client.request('GET', '/api/datacenters', headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type') == 'text/yaml'
        result = yaml.load(response.read())
        for entry in result:
            if entry['name'] == data['name']:
                break
        else:
            raise AssertionError
        data['type'] = 'FCP'
        data['description'] = 'New Description'
        body = yaml.dump(data)
        client.request('PUT', url.path, body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        client.request('GET', url.path, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type') == 'text/yaml'
        parsed = yaml.load(response.read())
        assert parsed['type'] == 'FCP'
        assert parsed['description'] == 'New Description'
        client.request('DELETE', url.path, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        client.request('DELETE', url.path, headers=headers)
        response = client.getresponse()
        assert response.status == http.NOT_FOUND
