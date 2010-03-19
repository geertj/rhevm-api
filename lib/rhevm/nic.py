#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest import Collection, InputValidator, OutputValidator
from rhevm.api import powershell


class NicCollection(Collection):

    name = 'nics'
    objectname = 'nic'

    def show(self, vmid, id):
        filter = create_filter(name=vmid)
        result = powershell.execute('$vm = Select-Vm | %s; '
                                    'Write-Host $vm' % filter)
        if len(result) != 1:
            return
        filter = create_filter(name=id)
        result = powershell.execute('$vm.GetNetworkAdapters() | %s' % filter)
        if len(result) != 1:
            return
        return result[0]

    def list(self, vmid, **filter):
        filter = create_filter(name=vmid)
        result = powershell.execute('$vm = Select-Vm | %s; '
                                    'Write-Host $vm' % filter)
        if len(result) != 1:
            return
        filter = create_filter(**filter)
        result = powershell.execute('$vm.GetNetworkAdapters() | %s' % filter)
        return result

    def create(self, vmid, input):
        filter = create_filter(name=vmid)
        result = powershell.execute('$vm = Select-Vm | %s; '
                                    'Write-Host $vm' % filter)
        if len(result) != 1:
            raise KeyError
        cmdline = create_cmdline(**input)
        result = powershell.execute('Add-NetworkAdapter -VmObject $vm %s'
                                    % cmdline)
        return result[0]['name']

    def delete(self, vmid, id):
        filter = create_filter(name=vmid)
        result = powershell.execute('$vm = Select-Vm | %s; '
                                    'Write-Host $vm' % filter)
        if len(result) != 1:
            raise KeyError
        filter = create_filter(name=id)
        result = powershell.execute('$nic = $vm.GetNetworkAdapters() | %s; '
                                    'Write-Host $nic' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('Remove-NetworkAdapter -VmObject $vm '
                           ' -NetworkAdapter $nic')



def setup(app):
    app.add_route('/api/vms/:vmid/nics', method='GET',
                  collection='nics', action='list')
    app.add_route('/api/vms/:vmid/nics', method='POST',
                  collection='nics', action='create')
    app.add_route('/api/vms/:vmid/nics/:id', method='GET',
                  collection='nics', action='show')
    app.add_route('/api/vms/:vmid/nics/:id', method='DELETE',
                  collection='nics', action='delete')
    val = Validator(globals())
    val.rule('type <=> type')
    val.rule('gateway <=> gateway')
    val.rule('subnet <=> subnet')
    val.rule('speed <=> speed')
    val.rule('vlan <=> vlanid')
    val.rule('bondname <=> bondname')
    val.rule('bondtype <=> bondtype')
    val.rule('macaddress <=> macaddress')
    val.rule('id <= id')
    val.rule('name <=> name')
    val.rule('network <=> nework')
    val.rule('linespeed <= linespeed')
    val.rule('rxrate <= rxrate')
    val.rule('rxdropped <= rxdropped')
    val.rule('txrate <= txrate')
    val.rule('txdropped <= txdropped')
    val.rule('bond <= isbond')
    val.rule('bondinterfaces <= bondinterfaces')
    app.add_input_filter(InputValidator(val), collection='nics',
                         action=['create', 'update'])
    app.add_output_filter(OutputValidator(val), collection='nics',
                          action=['show', 'list'])
    app.add_collection(NicCollection())
