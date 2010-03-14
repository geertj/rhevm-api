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


class VmCollection(Collection):

    name = 'vms'
    objectname = 'vm'

    def show(self, id):
        filter = create_filter(name=id)
        result = powershell.execute('Select-Vm | %s' % filter)
        if len(result) != 1:
            return
        return result[0]

    def list(self, **filter):
        filter = create_filter(**filter)
        result = powershell.execute('Select-Vm | %s' % filter)
        return result

    def create(self, input):
        skel = { 'Name': input.pop('Name'),
                 'TemplateObject': input.pop('TemplateId'),
                 'HostClusterId': input.pop('HostClusterId') }
        cmdline = create_cmdline(**skel)
        result = powershell.execute('$vm = Add-VM %s' % cmdline)
        updates = []
        for key in input:
            updates.append('$vm.%s = "%s"' % (key, input[key]))
        updates = '; '.join(updates)
        powershell.execute('%s; Update-Vm -VmObject $vm' % updates)
        result = powershell.execute('$name = $vm.Name; Write-Host "Name: $name"')
        return result[0]['Name']

    def update(self, id, input):
        filter = create_filter(name=id)
        result = powershell.execute('Select-Vm | %s' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('$vm = Select-Vm | %s' % filter)
        updates = []
        for key in input:
            updates.append('$vm.%s = "%s"' % (key, input[key]))
        updates = '; '.join(updates)
        powershell.execute('%s; Update-Vm -VmObject $vm' % updates)

    def delete(self, id):
        filter = create_filter(name=id)
        result = powershell.execute('Select-Vm | %s' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('$vm = Select-Vm | %s' % filter)
        powershell.execute('Remove-Vm -VmId $vm.VmId')


def setup(app):
    val = Validator(globals())
    val.rule('id <= VmId')
    val.rule('name <=> Name *')
    val.rule('description <=> Description')
    val.rule('cluster_id(cluster) <=> cluster_name(HostClusterId) *')
    val.rule('template_object(template) <=> template_name(TemplateId)')
    #val.rule('template_object(template) <=> template_name(TemplateId) * [create]')
    #val.rule('template <= template_name(TemplateId) * [update]')
    val.rule('session <= Session')
    val.rule('memory <=> MemorySize')
    val.rule('domain <=> Domain')
    val.rule('os <=> OperatingSystem')
    val.rule('creationdate <= CreationDate')
    val.rule('monitors <=> NumOfMonitors')
    val.rule('cpus <=> NumOfCpus')
    val.rule('host_id(defaulthost) <=> host_name(DefaultHost)')
    val.rule('nice <=> NiceLevel')
    val.rule('failback <=> FailBack')
    val.rule('bootdevice <=> DefaultBootDevice')
    val.rule('type <=> VmType')
    val.rule('hypervisor <=> HypervisorType')
    val.rule('mode <=> OperationMode')
    val.rule('status <= Status')
    val.rule('ip <= Ip')
    val.rule('hostname <= HostName')
    val.rule('uptime <= UpTime')
    val.rule('logintime <= LoginTime')
    val.rule('username <= CurrentUserName')
    val.rule('lastlogout <= LastLogoutTime')
    val.rule('elapsedtime <= ElapsedTime')
    val.rule('host <= RunningOnHost')
    val.rule('migratehost <= MigratingToHost')
    val.rule('applications <= ApplicationList')
    val.rule('displayport <= DisplayPort')
    val.rule('ha <=> HighlyAvailable')
    # XXX: syntax error in Select-VmPool. Bug?
    #val.rule('pool_id(pool) <=> pool_name(poolid)')
    val.rule('pool <=> PoolId')
    app.add_input_filter(InputValidator(val), collection='vms',
                         action=['create', 'update'])
    app.add_output_filter(OutputValidator(val), collection='vms',
                          action=['show', 'list'], priority=40)
    app.add_collection(VmCollection())
