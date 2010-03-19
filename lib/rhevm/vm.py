#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from argproc import ArgumentProcessor
from rest import Collection
from rhevm.api import powershell
from rhevm.util import *
from rhevm.filter import StructuredInput, StructuredOutput


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
        args = { 'Name': input.pop('Name'),
                 'TemplateObject': input.pop('TemplateId'),
                 'HostClusterId': input.pop('HostClusterId') }
        cmdline = create_cmdline(**args)
        result = powershell.execute('$vm = Add-VM %s' % cmdline)
        updates = []
        for key in input:
            updates.append('$vm.%s = "%s"' % (key, input[key]))
        updates = '; '.join(updates)
        powershell.execute('%s; Update-Vm -VmObject $vm' % updates)
        return args['Name']

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
    proc = ArgumentProcessor()
    proc.rules("""
        # Properties required for creation
        $name * <=> $Name
        cluster_id($cluster) * <=> cluster_name($HostClusterId)
        template_object($template) * => template_name($TemplateId) [create]
        template_id($template) <=> template_name($TemplateId) [update]

        # Read-write properties
        $description <=> $Description
        $memory:int <=> int($MemorySize)
        $domain <=> $Domain
        $os <=> $OperatingSystem
        $monitors:int <=> int($NumOfMonitors)
        $cpus:int <=> int($NumOfCpus)
        host_id($defaulthost) <=> host_name($DefaultHost)
        $nicelevel:int <=> $NiceLevel
        int(bool($failback)) <=> bool($FailBack)
        $bootdevice:('harddisk', 'network') <=> lower($DefaultBootDevice)
        $type:('server', 'desktop') <=> lower($VmType)
        bool(int($ha)) <=> bool($HighlyAvailable)  # Requires to be set as int

        # Mask these out as i think they are going away
        #$hypervisor:'kvm' <=> lower($HypervisorType)
        #$mode:'fullvirtualized' <=> lower($OperationMode)

        # Readonly properties
        $id <= $VmId
        $creationdate <= $CreationDate
        $status <= $Status
        $session <= $Session
        $ip <= $Ip
        $hostname <= $HostName
        $uptime <= $UpTime
        $logintime <= $LoginTime
        $username <= $CurrentUserName
        $lastlogout <= $LastLogoutTime
        $elapsedtime <= $ElapsedTime
        $host <= $RunningOnHost
        $migratehost <= $MigratingToHost
        #$applications <= $ApplicationList  # xxx: need to check format
        $displayport <= $DisplayPort
        # XXX: syntax error in Select-VmPool. Bug?
        #pool_id($pool) <=> pool_name($PoolId)
        """)
    app.add_input_filter(StructuredInput(proc), collection='vms',
                         action=['create', 'update'])
    app.add_output_filter(StructuredOutput(proc), collection='vms',
                          action=['show', 'list'])
    app.add_collection(VmCollection())
