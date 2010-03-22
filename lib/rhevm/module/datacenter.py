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


class DataCenterCollection(RhevmCollection):
    """REST API for managing datacenters."""

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
        cargs = { 'Name': input.pop('Name'),
                  'DataCenterType': input.pop('Type') }
        cmdline = create_cmdline(**cargs)
        result = powershell.execute('$dc = Add-DataCenter %s' % cmdline)
        updates = []
        for key in input:
            updates.append('$dc.%s = "%s"' % (key, input[key]))
        updates = '; '.join(updates)
        result = powershell.execute('%s; Update-DataCenter'
                                    ' -DataCenterObject $dc' % updates)
        url = mapper.url_for(collection=self.name, action='show',
                             id=result[0]['Name'])
        return url, result[0]

    def update(self, id, input):
        filter = create_filter(name=id)
        result = powershell.execute('Select-DataCenter | %s'
                                    ' | Tee-Object -Variable dc' % filter)
        if len(result) != 1:
            raise KeyError
        updates = []
        for key in input:
            updates.append('$dc.%s = "%s"' % (key, input[key]))
        updates = '; '.join(updates)
        result = powershell.execute('%s; Update-DataCenter'
                                    ' -DataCenterObject $dc' % updates)
        return result[0]

    def delete(self, id):
        filter = create_filter(name=id)
        result = powershell.execute('Select-DataCenter | %s'
                                    ' | Tee-Object -Variable dc' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('Remove-DataCenter -DataCenterId $dc.DataCenterId')


def setup_module(app):
    proc = ArgumentProcessor()
    proc.rules("""
        $id <= $DataCenterId
        $name * <=> $Name
        $description <=> $Description
        $type * <=> $Type
        $status <= $Status
    """)
    app.add_input_filter(StructuredInput(proc), collection='datacenters')
    app.add_output_filter(StructuredOutput(proc), collection='datacenters')
    app.add_collection(DataCenterCollection())
