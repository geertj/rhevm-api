#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from argproc import ArgumentProcessor
from rest.api import mapper
from rhevm.api import powershell
from rhevm.util import *
from rhevm.appcfg import StructuredInput, StructuredOutput
from rhevm.collection import RhevmCollection


class NicCollection(RhevmCollection):
    """REST API for managing a VM's network cards."""

    name = 'nics'
    objectname = 'nic'

    def show(self, vm, id):
        filter = create_filter(name=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            return
        filter = create_filter(name=id)
        result = powershell.execute('$vm.GetNetworkAdapters() | %s' % filter)
        if len(result) != 1:
            return
        return result[0]

    def list(self, vm, **args):
        filter = create_filter(name=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            return
        filter = create_filter(**args)
        result = powershell.execute('$vm.GetNetworkAdapters() | %s' % filter)
        return result

    def create(self, vm, input):
        filter = create_filter(name=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            raise KeyError
        cmdline = create_cmdline(**input)
        result = powershell.execute('Add-NetworkAdapter -VmObject $vm %s'
                                    % cmdline)
        # Weird output from Add-NetworkAdapter.. This is not equal to the
        # output of $vm.GetNetworkAdapters(). Re-fetch the object again.
        filter = create_filter(name=input['InterfaceName'])
        result = powershell.execute('$vm.GetNetworkAdapters() | %s' % filter)
        url = mapper.url_for(collection=self.name, action='show',
                             id=result[0]['Name'],vm=vm)
        return url, result[0]

    def delete(self, vm, id):
        filter = create_filter(name=vm)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            raise KeyError
        filter = create_filter(name=id)
        result = powershell.execute('$vm.GetNetworkAdapters() | %s'
                                    ' | Tee-Object -Variable nic' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('Remove-NetworkAdapter -VmObject $vm '
                           ' -NetworkAdapter $nic')


def setup_module(app):
    app.add_route('/api/vms/:vm/nics', method='GET', collection='nics',
                  action='list')
    app.add_route('/api/vms/:vm/nics', method='POST', collection='nics',
                  action='create')
    app.add_route('/api/vms/:vm/nics/:id', method='GET', collection='nics',
                  action='show')
    app.add_route('/api/vms/:vm/nics/:id', method='DELETE', collection='nics',
                  action='delete')
    proc = ArgumentProcessor()
    proc.rules("""
        # There's an inconsitency between command line argument names
        # and object properties...
        $type:('e1000', 'pv', 'rtl8139') * => $InterfaceType [create]
        $name * => $InterfaceName [create]
        $network * => $NetworkName [create]
        $type:('e1000', 'pv', 'rtl8139')  <= $Type [create]
        $name <= $Name [create]
        $network <= $Network [create]

        $type:('e1000', 'pv', 'rtl8139') * <=> $Type [!create]
        $name * <=> $Name [!create]
        $network * <=> $Network [!create]
        $mac <=> $MacAddress

        # Read-only properties
        $gateway <= $Gateway
        $subnet <= $Subnet
        $address <= $Address
        $id <= $Id
    """)
    app.add_input_filter(StructuredInput(proc), collection='nics')
    app.add_output_filter(StructuredOutput(proc), collection='nics')
    app.add_collection(NicCollection())
