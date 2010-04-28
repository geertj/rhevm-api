#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import re
import sys
import os.path
import logging
import inspect
import py_compile
from optparse import OptionParser

from rest import make_server
from rhevm.application import RhevmApp

from isapi_wsgi import ISAPIThreadPoolHandler
from isapi.install import (ISAPIParameters, ScriptMapParams,
                           VirtualDirParameters, HandleCommandLine)

if hasattr(sys, 'isapidllhandle'):  # Do we run under IIS?
    import isapi_config
    if isapi_config.debug:
        import win32traceutil


re_listen = re.compile('([-A-Za-z0-9.]+):([0-9]+)')


def _setup_logging(debug):
    """Set up logging."""
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    format = '%(levelname)s [%(name)s] %(message)s'
    formatter = logging.Formatter(format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)


def cmdline():
    """Command-line integration. Start up the API based on the built-in
    wsgiref web server."""
    parser = OptionParser()
    parser.add_option('-l', '--listen', dest='listen',
                      help='listen on interface:port')
    parser.add_option('-d', '--debug', action='store_true')
    parser.set_default('listen', 'localhost:8080')
    parser.set_default('debug', False)
    opts, args = parser.parse_args()
    mobj = re_listen.match(opts.listen)
    if not mobj:
        parser.error('specify --listen as host:port')
    address = mobj.group(1)
    port = int(mobj.group(2))
    _setup_logging(opts.debug)
    server = make_server(address, port, RhevmApp)
    print 'Listening on %s:%s' % (address, port)
    print 'Press CTRL-C to quit'
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


class RhevmExtension(ISAPIThreadPoolHandler):
    """ISAPI Extension that uses isapi_wsgi to run a WSGI application under
    IIS."""

    def __init__(self):
        _setup_logging(isapi_config.debug)
        ISAPIThreadPoolHandler.__init__(self, RhevmApp)

    def TerminateExtension(self, status):
        self.rootapp.shutdown()
        ISAPIThreadPoolHandler.TerminateExtension(self, status)


def __ExtensionFactory__():
    return RhevmExtension()


def isapi():
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
    config = os.path.join(os.path.split(fname)[0], 'isapi_config.py')
    fout = file(config, 'w')
    fout.write('## This file is auto-generated and will be overwritten\n')
    fout.write('debug = %s\n' % opts.debug)
    fout.close()
    py_compile.compile(config)
