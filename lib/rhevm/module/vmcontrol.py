#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest.api import response, mapper
from rhevm.api import powershell
from rhevm.util import *
from rhevm.collection import RhevmCollection


class VmControlCollection(RhevmCollection):
    """REST API for controlling a VM's state."""

    name = 'vmcontrol'

    entity_transform = """
        $command:('start', 'stop', 'shutdown', 'suspend', 'migrate')
                => $command *

        # Start-Vm parameters
        invert(boolean($hwaccel)) => $DisableHardwareAcceleration @start
        invert(boolean($pause)) => $RunAndPause @start
        adjust($display:('vnc', 'spice')) => $DisplayType @start
        invert(boolean($acpi)) => $AcpiDisable @start
        bootorder($boot) => $BootDevice @start
        $cdrom => $IsoFileName @start
        $floppy => $FloppyPath @start
        host_id($host) => $DestinationHostId @start
        boolean($stateless) => $RunAsStateless @start
        boolean($reinit) => $Reinitialize @start

        # Move-Vm parameters
        host_id($host) => $DestHostId @migrate
        """
    def create(self, vm, input):
        filter = create_filter(vmid=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            return
        command = input.pop('command')
        if command == 'start':
            # XXX workaround for bug: Start-Vm does not honour -IsoFileName
            if not 'RunAndPause' in input and 'IsoFileName' in input:
                input['RunAndPause'] = True
                iso = input.pop('IsoFileName')
                cmdline = create_cmdline(**input)
                powershell.execute('Start-Vm -VmObject $vm %s' % cmdline)
                cmdline = create_cmdline(IsoFileName=iso)
                powershell.execute('Mount-Disk -VmObject $vm %s' % cmdline)
                powershell.execute('Start-Vm -VmObject $vm')
            else:
                cmdline = create_cmdline(**input)
                powershell.execute('Start-Vm -VmObject $vm %s' % cmdline)
        elif command == 'stop':
            powershell.execute('Stop-Vm -VmObject $vm')
        elif command == 'shutdown':
            powershell.execute('Shutdown-Vm -VmObject $vm')
        elif command == 'suspend':
            powershell.execute('Suspend-Vm -VmObject $vm')
        elif command == 'migrate':
            cmdline = create_cmdline(**input)
            powershell.execute('Migrate-Vm -VmObject $vm %s' % cmdline)


def setup_module(app):
    app.add_route('/api/vms/:vm/control', method='POST',
                  collection='vmcontrol', action='create')
    app.add_collection(VmControlCollection())
