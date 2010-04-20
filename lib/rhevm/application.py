#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest import Application
import rhevm.api
from rhevm.pool import Pool
from rhevm.powershell import PowerShell
from rhevm.util import create_powershell


class RhevmApp(Application):
    """The RHEVM API application."""

    def load_modules(self):
        super(RhevmApp, self).load_modules()
        self.load_module('rhevm.appcfg')
        self.load_module('rhevm.module.datacenter')
        self.load_module('rhevm.module.vm')
        self.load_module('rhevm.module.vmcontrol')
        self.load_module('rhevm.module.nic')
        self.load_module('rhevm.module.disk')
        self.load_module('rhevm.module.ticket')

    def respond(self):
        if not rhevm.api.pool:
            rhevm.api.pool = Pool(PowerShell, create_powershell)
        response = super(RhevmApp, self).respond()
        rhevm.api.pool.put(rhevm.api.powershell._release())
        rhevm.api.pool.maintenance()  # this is async
        return response
