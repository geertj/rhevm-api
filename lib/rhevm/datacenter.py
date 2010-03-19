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
from rhevm.filter import StructuredInput, StructuredOutput
from rhevm.util import *


class DataCenterCollection(Collection):

    name = 'datacenters'
    objectname = 'datacenter'

    def show(self, id):
        filter = create_filter(name=id)
        result = powershell.execute('Select-DataCenter | %s' % filter)
        if len(result) != 1:
            return
        return result[0]

    def list(self, **filter):
        filter = create_filter(**filter)
        result = powershell.execute('Select-DataCenter | %s' % filter)
        return result

    def create(self, input):
        args = { 'Name': input.pop('Name'),
                 'DataCenterType': input.pop('DataCenterType') }
        cmdline = create_cmdline(**args)
        result = powershell.execute('$dc = Add-DataCenter %s' % cmdline)
        updates = []
        for key in input:
            updates.append('$dc.%s = "%s"' % (key, input[key]))
        updates = '; '.join(updates)
        powershell.execute('%s; Update-DataCenter -DataCenterObject $dc' % updates)
        return args['Name']

    def update(self, id, input):
        filter = create_filter(name=id)
        result = powershell.execute('Select-DataCenter | %s' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('$dc = Select-DataCenter | %s' % filter)
        updates = []
        for key in input:
            updates.append('$dc.%s = "%s"' % (key, input[key]))
        updates = '; '.join(updates)
        powershell.execute('%s; Update-DataCenter -DataCenterObject $dc' % updates)

    def delete(self, id):
        filter = create_filter(name=id)
        result = powershell.execute('Select-DataCenter | %s' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('$dc = Select-DataCenter | %s' % filter)
        powershell.execute('Remove-DataCenter -DataCenterId $dc.DataCenterId')


def setup(app):
    proc = ArgumentProcessor()
    proc.rules("""
        $id <= $DataCenterId
        $name * <=> $Name
        $description <=> $Description
        $type * => $DataCenterType [create]
        $type * <=> $Type [update]
        $status <= $Status
    """)
    app.add_input_filter(StructuredInput(proc), collection='datacenters',
                         action=['create', 'update'])
    app.add_output_filter(StructuredOutput(proc), collection='datacenters',
                          action=['show', 'list'])
    app.add_collection(DataCenterCollection())
