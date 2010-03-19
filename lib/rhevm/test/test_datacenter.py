#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import random
import httplib as http

from urlparse import urlparse
import yaml

from rhevm.test.base import RhevmTest


class TestDataCenter(RhevmTest): 

    def test_show(self):
        powershell = self.powershell
        ref = powershell.execute('Select-DataCenter')
        id = ref[0]['Name']
        self.client.request('GET', '/api/datacenters/%s' % id,
                            headers=self.headers)
        response = self.client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type', 'text/yaml')

    def test_list(self):
        powershell = self.powershell
        powershell.execute('Select-DataCenter')
        self.client.request('GET', '/api/datacenters', headers=self.headers)
        response = self.client.getresponse()
        assert response.status == http.OK
        assert response.getheader('Content-Type', 'text/yaml')
        parsed = yaml.load(response.read())
        assert len(parsed) == len(ref)

    def test_create_update_delete(self):
        client = self.client
        headers = self.headers
        headers['Content-Type'] = 'text/yaml'
        data = {}
        data['type'] = 'NFS'
        data['name'] = 'NewName-%s' % random.randint(0, 1000000000)
        body = yaml.dump(data)
        client.request('POST', '/api/datacenters', body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        location = response.getheader('Location')
        assert location is not None
        url = urlparse(location)
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
