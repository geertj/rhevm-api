#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import sys
from rhevm.error import Error
from rhevm._version import *

# Allow this package to be imported on non-Windows platforms as well
# (to run the test suite remotely).
if sys.platform in ('win32', 'win64'):
    from rhevm.application import RhevmApp
    from rhevm.powershell import PowerShell, PowerShellError
