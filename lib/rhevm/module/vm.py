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
from rhevm.powershell import escape


class VmCollection(RhevmCollection):
    """REST API for managing virtual machines."""

    name = 'vms'
    objectname = 'vm'

    def show(self, id):
        filter = create_filter(vmid=id)
        result = powershell.execute('Select-Vm | %s' % filter)
        if len(result) != 1:
            return
        return result[0]

    def list(self, **filter):
        query = filter.pop('query', 'vms:')
        filter = create_filter(**filter)
        result = powershell.execute('Select-Vm -SearchText %s | %s'
                                    % (escape(query), filter))
        return result

    def create(self, input):
        cargs = { 'Name': input.pop('Name'),
                  'TemplateObject': input.pop('TemplateId'),
                  'HostClusterId': input.pop('HostClusterId') }
        cmdline = create_cmdline(**cargs)
        result = powershell.execute('$vm = Add-VM %s' % cmdline)
        updates = []
        for key in input:
            updates.append('$vm.%s = "%s"' % (key, input[key]))
        updates = '; '.join(updates)
        result = powershell.execute('%s; Update-Vm -VmObject $vm' % updates)
        url = mapper.url_for(collection=self.name, action='show',
                             id=result[0]['VmId'])
        return url, result[0]

    def update(self, id, input):
        filter = create_filter(vmid=id)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            raise KeyError
        updates = []
        for key in input:
            updates.append('$vm.%s = "%s"' % (key, input[key]))
        updates = '; '.join(updates)
        result = powershell.execute('%s; Update-Vm -VmObject $vm' % updates)
        return result[0]

    def delete(self, id):
        filter = create_filter(vmid=id)
        result = powershell.execute('Select-Vm | %s'
                                    ' | Tee-Object -Variable vm' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('Remove-Vm -VmId $vm.VmId')


def setup_module(app):
    proc = ArgumentProcessor()
    proc.rules("""
        # Properties required for creation
        $name * <=> $Name
        cluster_id($cluster) * <=> cluster_name($HostClusterId)
        template_object($template) * => template_name($TemplateId) [create]
        template_id($template) <= template_name($TemplateId)

        # Read-write properties
        $description <=> $Description
        $memory:int <=> int($MemorySize)
        $domain <=> $Domain
        $os <=> $OperatingSystem
        $monitors:int <=> int($NumOfMonitors)
        $cpus:int <=> int($NumOfCpus)
        host_id($defaulthost) <=> host_name($DefaultHost, $HostClusterId)
        $nice:int <=> int($NiceLevel)
        int($failback) <=> boolean($FailBack)
        $boot:('harddisk', 'network', 'cdrom') <=> lower($DefaultBootDevice)
        $type:('server', 'desktop') <=> lower($VmType)
        int($ha) <=> boolean($HighlyAvailable)  # Requires to be set as int

        # Mask these out as i think they are going away
        #$hypervisor:'kvm' <=> lower($HypervisorType)
        #$mode:'fullvirtualized' <=> lower($OperationMode)

        # Readonly properties
        $id <= $VmId
        $created <= $CreationDate
        $status <= lower($Status)
        $session <= $Session
        $ip <= $Ip
        $hostname <= $HostName
        $uptime <= $UpTime
        $login <= $LoginTime
        $username <= $CurrentUserName
        $logout <= $LastLogoutTime
        $time <= int($ElapsedTime)
        $host <= host_name($RunningOnHost, $HostClusterId)
        $migrating <= host_name($MigratingToHost, $HostClusterId)
        #$applications <= $ApplicationList  # xxx: need to check format
        $port <= int($DisplayPort)
        # XXX: syntax error in Select-VmPool. Bug?
        #pool_id($pool) <= pool_name($PoolId)
        $pool <= int($PoolId)

        # Searching
        parse_query($query) => $query [list]
        """)
    app.add_input_filter(StructuredInput(proc), collection='vms')
    app.add_output_filter(StructuredOutput(proc), collection='vms')
    app.add_collection(VmCollection())
