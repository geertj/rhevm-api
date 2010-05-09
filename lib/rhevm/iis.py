#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import sys
import os.path
import inspect
import py_compile
from optparse import OptionParser

from rhevm.application import RhevmApp
from rhevm.util import setup_logging

from isapi_wsgi import ISAPIThreadPoolHandler
from isapi.install import (ISAPIParameters, ScriptMapParams,
                           VirtualDirParameters, HandleCommandLine)


eggdir = r'C:\Documents and Settings\Default User\Application Data' \
         r'\Python-Eggs'


class Error(Exception):
    """ISAPI installation error."""


class RhevmExtension(ISAPIThreadPoolHandler):
    """ISAPI Extension that uses isapi_wsgi to run a WSGI application under
    IIS."""

    def __init__(self):
        ISAPIThreadPoolHandler.__init__(self, RhevmApp)

    def TerminateExtension(self, status):
        self.rootapp.shutdown()
        ISAPIThreadPoolHandler.TerminateExtension(self, status)


def __ExtensionFactory__():
    import _iis_config
    if _iis_config.debug:
        import win32traceutil
    setup_logging(_iis_config.debug)
    return RhevmExtension()


def create_iis_config(config, opts):
    """Store command line arguments for when we start running under IIS."""
    fout = file(config, 'w')
    fout.write('## This file is auto-generated and will be overwritten\n')
    fout.write('debug = %s\n' % opts.debug)
    fout.close()
    py_compile.compile(config)
    print 'Configuration file created.'


def main():
    parser = OptionParser()
    parser.add_option('-d', '--debug', action='store_true')
    parser.set_default('debug', False)
    opts, args = parser.parse_args()
    sys.argv[1:] = args
    params = ISAPIParameters()
    sm = ScriptMapParams(Extension='*', Flags=0)
    vd = VirtualDirParameters(Name='api', Description='RHEVManagerApi',
                              ScriptMaps=[sm], ScriptMapUpdate='replace')
    params.VirtualDirs = [vd]
    # A DLL with the name _server.dll is installed in the same directory as
    # this file. But because we're called by a setuptools entry_point, we need
    # to override the default.
    fname = inspect.getfile(sys.modules[__name__])
    HandleCommandLine(params, conf_module_name=fname)
    config = os.path.join(os.path.split(fname)[0], '_iis_config.py')
    create_iis_config(config, opts)
