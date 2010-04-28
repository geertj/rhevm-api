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


class TestTag(RhevmTest): 

    def test_crud(self):
        client = self.client
        headers = self.headers
        # Create a new tag with a random name
        headers['Content-Type'] = 'text/yaml'
        data = { 'name': 'test-%s' % random.randint(0, 1000000000) }
        body = yaml.dump(data)
        client.request('POST', '/api/tags', body=body, headers=headers)
        response = client.getresponse()
        assert response.status in (http.OK, http.CREATED)
        location = response.getheader('Location')
        assert location is not None
        url = urlparse(location)
        # List all tags and check that the new one is there.
        client.request('GET', '/api/tags', headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        result = yaml.load(response.read())
        for entry in result:
            if entry['name'] == data['name']:
                break
        else:
            raise AssertionError, 'Tag not found'
        # Update the tag
        data['description'] = 'new description'
        body = yaml.dump(data)
        client.request('PUT', url.path, headers=headers, body=body)
        response = client.getresponse()
        assert response.status == http.OK
        # Get the tag and make sure the description was updated
        client.request('GET', url.path, headers=headers)
        response = client.getresponse()
        assert response.status == http.OK
        result = yaml.load(response.read())
        assert result['name'] == data['name']
        assert result['description'] == data['description']
        # Remove it
        client.request('DELETE', url.path, headers=headers)
        response = client.getresponse()
        assert response.status in (http.OK, http.NO_CONTENT)
