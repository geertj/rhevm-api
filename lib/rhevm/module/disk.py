#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest import http
from rest.api import mapper, request, response
from rhevm.api import powershell
from rhevm.util import *
from rhevm.collection import RhevmCollection


class DiskCollection(RhevmCollection):
    """REST API for managing a VM's disks."""

    name = 'disks'
    entity_transform = """
        $!type => $!type
        $!type <= "disk"
        # This parameters is different on the command line than for object
        # properties.
        $size:int => $DiskSize @create
        $size <= int($SizeInGB)

        # Settable properties
        $usage:('system', 'data', 'shared', 'swap', 'temp')
                <=> lower($DiskType)
        adjust($interface:('ide', 'virtio')) <=> lower($DiskInterface)
        adjust($allocation:('preallocated', 'sparse')) <=> lower($VolumeType)
        adjust($format:('cow', 'raw')) => lower($VolumeFormat)
        int($propagate_errors) <=> equals($PropagateErrors, "Off")
        int($wipe_after_delete) <=> boolean($WipeAfterDelete)

        # Read-only properties
        $created <= $CreationDate
        $modified <= $LastModified
        $description <= $Description
        $drive <= int($InternalDriveMapping)
        $id <= $SnapshotId
        $status <= upper($Status)
        $boot <= boolean($Boot)
        """

    def show(self, vm, id):
        filter = create_filter(vmid=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            return
        filter = create_filter(snapshotid=id)
        result = powershell.execute('$vm.GetDiskImages() | %s' % filter)
        if not result:
            return
        return result[0]

    def list(self, vm, **args):
        filter = create_filter(vmid=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            return
        filter = create_filter(**args)
        result = powershell.execute('$vm.GetDiskImages() | %s' % filter)
        return result

    def create(self, vm, input):
        filter = create_filter(vmid=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            raise KeyError
        # With RHEVM-2.1, when adding a disk with Add-Disk, the new SnapshotId
        # is not returned. Therefore we need to compare disk images before and
        # after to conclude what our new SnapshotId is. On RHEVM-2.2 the
        # SnapshotId seems to be returned.
        result = powershell.execute('$vm.GetDiskImages()')
        old = set((disk['SnapshotId'] for disk in result))
        create = { 'DiskSize': input.pop('DiskSize') }
        cmdline = create_cmdline(**create)
        updates = create_setattr('disk', **input)
        powershell.execute('$disk = New-Disk %s; %s' % (cmdline, updates))
        if powershell.version >= (2, 2):
            vmref = '-VmObject $vm'
        else:
            vmref = '-VmId $vm.VmId'
        if input.get('VolumeType') == 'Preallocated':
            result = powershell.execute('Add-Disk -DiskObject $disk %s -Async'
                                        % vmref)
            tasks = powershell.execute('Get-LastCommandTasks')
            async = True
        else:
            result = powershell.execute('Add-Disk -DiskObject $disk %s'
                                        % vmref)
            async = False
        result = powershell.execute('$vm.GetDiskImages()')
        new = set((disk['SnapshotId'] for disk in result))
        diskid = (new - old).pop()
        filter = create_filter(snapshotid=diskid)
        result = powershell.execute('$vm.GetDiskImages() | %s' % filter)
        if async:
            response.status = http.ACCEPTED
            url = mapper.url_for(collection='tasks', action='show',
                                 id=tasks[0]['TaskId'])
            response.set_header('Link', '<%s>; rel=status' % url)
        url = mapper.url_for(collection=self.name, action='show', 
                             id=result[0]['SnapshotId'], vm=vm)
        return url, result[0]

    def delete(self, vm, id):
        filter = create_filter(vmid=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            raise KeyError
        filter = create_filter(snapshotid=id)
        result = powershell.execute('$vm.GetDiskImages() | %s'
                                    ' | Tee-Object -Variable disk' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('Remove-Disk -DiskId $disk.SnapshotId -VmId $vm.VmId')


def setup_module(app):
    app.add_route('/api/vms/:vm/disks', method='GET', collection='disks',
                  action='list')
    app.add_route('/api/vms/:vm/disks', method='POST', collection='disks',
                  action='create')
    app.add_route('/api/vms/:vm/disks/:id', method='GET', collection='disks',
                  action='show')
    app.add_route('/api/vms/:vm/disks/:id', method='DELETE',
                  collection='disks', action='delete')
    app.add_collection(DiskCollection())
