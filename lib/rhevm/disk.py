#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest import Collection, Validator, InputValidator, OutputValidator

from rhevm.api import powershell
from rhevm.util import *


class DiskCollection(Collection):

    name = 'disks'
    objectname = 'disk'

    def show(self, vmid, id):
        filter = create_filter(name=vmid)
        result = powershell.execute('$vm = Select-Vm | %s; '
                                    'Write-Host $vm' % filter)
        if len(result) != 1:
            return
        filter = create_filter(internaldrivemapping=id)
        result = powershell.execute('$vm.GetDiskImages() | %s' % filter)
        if not result:
            return
        return result[0]

    def list(self, vmid, **filter):
        filter = create_filter(name=vmid)
        result = powershell.execute('$vm = Select-Vm | %s; '
                                    'Write-Host $vm' % filter)
        if len(result) != 1:
            return
        filter = create_filter(**filter)
        result = powershell.execute('$vm.GetDiskImages() | %s' % filter)
        return result

    def create(self, vmid, input):
        filter = create_filter(name=vmid)
        result = powershell.execute('$vm = Select-Vm | %s; '
                                    'Write-Host $vm' % filter)
        if len(result) != 1:
            raise KeyError
        old = [ disk['internaldrivemapping']
                for disk in powershell.execute('$vm.GetDiskImages()') ]
        cmdline = create_cmdline(**input)
        powershell.execute('$disk = New-Disk %s' % cmdline)
        result = powershell.execute('Add-Disk -DiskObject $disk -VmId $vm.VmId')
        new = [ disk['internaldrivemapping']
                for disk in powershell.execute('$vm.GetDiskImages()') ]
        for disk in new:
            if disk not in old:
                return disk

    def delete(self, vmid, id):
        filter = create_filter(name=vmid)
        result = powershell.execute('$vm = Select-Vm | %s; '
                                    'Write-Host $vm' % filter)
        if len(result) != 1:
            raise KeyError
        filter = create_filter(internaldrivemapping=id)
        result = powershell.execute('$disk = $vm.GetDiskImages() | %s; '
                                    'Write-Host $disk' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('Remove-Disk -DiskId $disk.SnapshotId -VmId $vm.VmId')


def setup(app):
    app.add_route('/api/vms/:vmid/disks', method='GET',
                  collection='disks', action='list')
    app.add_route('/api/vms/:vmid/disks', method='POST',
                  collection='disks', action='create')
    app.add_route('/api/vms/:vmid/disks/:id', method='GET',
                  collection='disks', action='show')
    app.add_route('/api/vms/:vmid/disks/:id', method='DELETE',
                  collection='disks', action='delete')
    val = Validator(globals())
    val.rule('creationdate <=> creationdate')
    val.rule('lastmodified <=> lastmodified')
    val.rule('actualsizeinsectors <=> actualsizeinsectors')
    val.rule('actualsizeinmb <=> actualsizeinmb')
    val.rule('actualsizeingb <=> actualsizeingb')
    val.rule('description <=> description')
    val.rule('id <=> snapshotid')
    val.rule('vmsnapshot <=> vmsnapshotid')
    val.rule('sizeingb <=> sizeingb')
    val.rule('parent <=> parentid')
    val.rule('status <=> status')
    val.rule('applications <=> applist')
    val.rule('volumetype <=> volumetype')
    val.rule('volumeformat <=> volumeformat')
    val.rule('type <=> disktype')
    val.rule('name <=> internaldrivemapping')
    val.rule('boot <=> boot')
    val.rule('interface <=> diskinterface')
    val.rule('wipeafterdelete <=> wipeafterdelete')
    val.rule('propagateerrors <=> propagateerrors')
    app.add_input_filter(InputValidator(val), collection='disks',
                         action=['create', 'update'])
    app.add_output_filter(OutputValidator(val), collection='disks',
                          action=['show', 'list'])
    app.add_collection(DiskCollection())
