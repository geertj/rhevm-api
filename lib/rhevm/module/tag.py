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


class TagCollection(RhevmCollection):
    """REST API for managing tags."""

    name = 'tags'
    objectname = 'tag'

    def show(self, id):
        cmdline = create_cmdline(Id=id)
        result = powershell.execute('Get-Tag %s' % cmdline)
        if not result:
            return
        return result[0]

    def list(self, **args):
        filter = create_filter(**args)
        result = powershell.execute('Get-Tags | %s' % filter)
        return result

    def create(self, input):
        cmdline = create_cmdline(**input)
        result = powershell.execute('Add-Tag %s' % cmdline)
        url = mapper.url_for(collection='tags', action='show',
                             id=result[0]['TagID'])
        return url, result[0]

    def update(self, id, input):
        cmdline = create_cmdline(Id=id)
        result = powershell.execute('Get-Tag %s'
                                    ' | Tee-Object -Variable tag' % cmdline)
        if not result:
            raise KeyError, 'Tag not found'
        setattr = create_setattr('tag', **input)
        result = powershell.execute('%s; Update-Tag -TagObject $tag' % setattr)
        return result[0]
        
    def delete(self, id):
        cmdline = create_cmdline(Id=id)
        result = powershell.execute('Get-Tag %s'
                                    ' | Tee-Object -Variable tag' % cmdline)
        if not result:
            raise KeyError, 'Tag not found'
        powershell.execute('Remove-Tag -TagObject $tag')

    def show_for_object(self, type, id):
        if type == 'vms':
            cmdline = create_cmdline(VmId=id)
        elif type == 'hosts':
            cmdline = create_cmdline(HostId=id)
        elif type == 'users':
            cmdline = create_cmdline(UserId=id)
        elif type == 'clusters':
            cmdline = create_cmdline(ClusterId=id)
        else:
            raise KeyError
        result = powershell.execute('Get-Tags %s' % cmdline)
        return result

    def attach_to_object(self, type, id, input):
        cmdline = create_cmdline(**input)
        result = powershell.execute('Get-Tag %s | Tee-Object -Variable tag'
                                     % cmdline)
        if not result:
            raise KeyError
        if type == 'vms':
            cmdline = create_cmdline(VmId=id)
        elif type == 'hosts':
            cmdline = create_cmdline(HostId=id)
        elif type == 'users':
            cmdline = create_cmdline(UserId=id)
        elif type == 'clusters':
            cmdline = create_cmdline(ClusterId=id)
        else:
            return
        result = powershell.execute('Attach-Tag -TagObject $tag %s' % cmdline)
        return result[0]

    def detach_from_object(self, type, id, tag):
        if type == 'vms':
            cmdline = create_cmdline(VmId=id)
        elif type == 'hosts':
            cmdline = create_cmdline(HostId=id)
        elif type == 'users':
            cmdline = create_cmdline(UserId=id)
        elif type == 'clusters':
            cmdline = create_cmdline(ClusterId=id)
        else:
            return
        filter = create_filter(TagId=tag)
        result = powershell.execute('Get-Tags %s | %s | Tee-Object'
                                   ' -Variable tag' % (cmdline, filter))
        if not result:
            raise KeyError, 'No such tag'
        powershell.execute('Detach-Tag -TagObject $tag %s' % cmdline)


def setup_module(app):
    app.add_route('/api/:type/:id/tags', method='GET',
                  collection='tags', action='show_for_object')
    app.add_route('/api/:type/:id/tags', method='POST',
                  collection='tags', action='attach_to_object')
    app.add_route('/api/:type/:id/tags/:tag', method='DELETE',
                  collection='tags', action='detach_from_object')
    proc = ArgumentProcessor()
    proc.rules("""
        int($id) <=> int($TagID) [!attach_to_object]
        int($id) => $Id [attach_to_object]
        $name <=> $Name
        $description <=> $Description
        boolean($readonly) <=> boolean($ReadOnly)
        int($parent) <=> subif(int($ParentId), -1, None)
    """)
    app.add_input_filter(StructuredInput(proc), collection='tags')
    app.add_output_filter(StructuredOutput(proc), collection='tags')
    app.add_collection(TagCollection())
