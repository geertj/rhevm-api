#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import time
import random
from urlparse import urlparse
import yaml

from rest import http
from rhevm.test.base import RhevmTest


class TestVmTicket(RhevmTest): 

    def test_set_ticket(self):
        client = self.client
        headers = self.headers
        # Create a VM
        vm = { 'name': 'test-%s' % random.randint(0, 1000000),
               'template': self.template,
               'cluster': self.cluster,
               'type': 'server' }
        body = yaml.dump(vm)
        headers['Content-Type'] = 'text/x-yaml'
        client.request('POST', '/api/vms', body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        location = response.getheader('Location')
        assert location
        vmpath = urlparse(location).path
        # Add a disk
        diskpath = vmpath + '/disks'
        disk = { 'size': 1,
                 'allocation': 'sparse' }
        body = yaml.dump(disk)
        client.request('POST', diskpath, body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        # Add a NIC
        nicpath = vmpath + '/nics'
        nic = { 'name': 'eth0',
                'network': 'rhevm',
                'type': 'e1000' }
        body = yaml.dump(nic)
        client.request('POST', nicpath, body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        # Start it up
        ctrlpath = vmpath + '/control'
        command = { 'command': 'start',
                    'boot': 'cdrom',
                    'display': 'vnc' }
        body = yaml.dump(command)
        client.request('POST', ctrlpath, body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        # Wait max 2 minutes until the VM is launched
        now = time.time()
        while time.time() < now + 120:
            client.request('GET', vmpath, headers=headers)
            response = client.getresponse()
            assert response.status == http.OK
            data = yaml.load(response.read())
            if data['status'] == 'up':
                break
            print 'state = %s, sleeping' % data['status']
            time.sleep(10)
        # Set a ticket
        ticketpath = vmpath + '/ticket'
        ticket = { 'ticket': 'S3cret!',
                   'valid':  300 }
        body = yaml.dump(ticket)
        client.request('POST', ticketpath, body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        # Stop the VM
        command = { 'command': 'stop' }
        body = yaml.dump(command)
        client.request('POST', ctrlpath, body=body, headers=headers)
        response = client.getresponse()
        assert response.status == http.CREATED
        # Wait until it is stopped
        now = time.time()
        while time.time() < now + 120:
            client.request('GET', vmpath, headers=headers)
            response = client.getresponse()
            assert response.status == http.OK
            data = yaml.load(response.read())
            if data['status'] == 'down':
                break
            print 'state = %s, sleeping' % data['status']
            time.sleep(10)
        # Now delete it
        client.request('DELETE', vmpath, headers=headers)
        response = client.getresponse()
        assert response.status == http.NO_CONTENT
