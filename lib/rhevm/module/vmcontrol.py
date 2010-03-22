#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from argproc import ArgumentProcessor
from rest.api import response, mapper
from rhevm.api import powershell
from rhevm.util import *
from rhevm.appcfg import StructuredInput, StructuredOutput
from rhevm.collection import RhevmCollection


class VmControlCollection(RhevmCollection):
    """REST API for controlling a VM's state."""

    name = 'vmcontrol'

    def create(self, vm, input):
        filter = create_filter(name=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            return
        control = input.pop('control')
        cmdline = create_cmdline(**input)
        if control == 'start':
            powershell.execute('Start-Vm -VmObject $vm %s' % cmdline)
        elif control == 'stop':
            powershell.execute('Stop-Vm -VmObject $vm %s' % cmdline)
        elif control == 'shutdown':
            powershell.execute('Shutdown-Vm -VmObject $vm %s' % cmdline)
        elif control == 'suspend':
            powershell.execute('Suspend-Vm -VmObject $vm %s' % cmdline)
        elif control == 'migrate':
            powershell.execute('Migrate-Vm -VmObject $vm %s' % cmdline)


def setup_module(app):
    app.add_route('/api/vms/:vm/control', method='POST',
                  collection='vmcontrol', action='create')
    proc = ArgumentProcessor()
    proc.rules("""
        $command:('start', 'stop', 'shutdown', 'suspend', 'migrate) *
                => $command
        # Start-Vm parameters
        if(boolean($hwaccel), None) [command=start] => $DisableHardwareAcceleration
        if(boolean($pause), None) [command=start] => $RunAndPause
        $display:('vnc', 'spice') [command=start] => $DisplayType
        if(boolean($acpi), None) [command=start] => $AcpiDisable
        $boot [command=start] => $BootDevice
        $cdrom [command=start] => $IsoFileName
        $floppy [command=start] => $FloppyPath
        $host [command=start] => $DestinationHostId
        boolean($stateless) [command=start] => $RunAsStateless
        $reinit [command=start] => $Reinitialize

        # Move-Vm parameters
        host_id($host) [command=migrate] => $DestHostId
    """)
    app.add_input_filter(StructuredInput(proc), collection='vmcontrol')
    app.add_output_filter(StructuredOutput(proc), collection='vmcontrol')
    app.add_collection(VmControlCollection())
