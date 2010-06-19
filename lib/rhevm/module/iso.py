#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest import http
from rest.api import mapper, request, response
from rhevm.api import powershell
from rhevm.util import *
from rhevm.collection import RhevmCollection


class IsoCollection(RhevmCollection):
    """REST API for managing a DC's isos."""

    name = 'isos'
    contains = 'iso'
    entity_transform = """
        $!type => $!type
        $!type <= "iso"
        $name <=> $name
        """

    def list(self, dc, **args):
        filter = create_filter(DataCenterId=dc)
        result = powershell.execute('Get-ISOImages -DataCenterId %s' % dc)
        isos = []
        for iso in result:
            isos.append({'name': iso})
        return isos


def setup_module(app):
    app.add_route('/api/datacenters/:dc/isos', method='GET', collection='isos',
                  action='list')
    app.add_collection(IsoCollection())
