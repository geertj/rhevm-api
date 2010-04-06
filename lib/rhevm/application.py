#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest import Application
import rhevm.api
from rhevm.powershell import PowerShell


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
        powershell = PowerShell()
        rhevm.api.powershell._register(powershell)
        try:
            return super(RhevmApp, self).respond()
        finally:
            rhevm.api.powershell._release()
            powershell.close()
