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

from win32security import (GetNamedSecurityInfo, SetNamedSecurityInfo,
                           LookupAccountName, ACL_REVISION_DS, SE_FILE_OBJECT,
                           DACL_SECURITY_INFORMATION, OBJECT_INHERIT_ACE,
                           CONTAINER_INHERIT_ACE, INHERIT_ONLY_ACE)
from win32file import CreateDirectory, FindFilesW
from win32con import FILE_ATTRIBUTE_DIRECTORY
from ntsecuritycon import (FILE_GENERIC_READ, FILE_GENERIC_WRITE,
                           FILE_ADD_SUBDIRECTORY, FILE_TRAVERSE, DELETE)
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


def create_egg_cache(eggdir):
    """Create egg cache."""
    # Make sure there is an egg cache that is writeable to the IUSR_xxx
    # account.
    result = FindFilesW(eggdir)
    if result:
        finfo = result[0]
        if not finfo[0] & FILE_ATTRIBUTE_DIRECTORY:
            raise Error, 'Egg cache is not a directory.'
        print 'Egg cache exists.'
    else:
        CreateDirectory(eggdir, None)
        print 'Egg cache created.'

    # Change/check the ACL
    hostname = LookupAccountName(None, 'Administrator')[1]  # get host name
    target = LookupAccountName(None, 'IUSR_%s' % hostname)[0]
    desc = GetNamedSecurityInfo(eggdir, SE_FILE_OBJECT,
                                DACL_SECURITY_INFORMATION)
    acl = desc.GetSecurityDescriptorDacl()
    for i in range(acl.GetAceCount()):
        ace = acl.GetAce(i)
        if ace[2] == target:
            break  # assume the ACE is correct
    else:
        flags = OBJECT_INHERIT_ACE|CONTAINER_INHERIT_ACE
        access = FILE_GENERIC_READ|FILE_GENERIC_WRITE|FILE_ADD_SUBDIRECTORY| \
                 FILE_TRAVERSE|DELETE
        acl.AddAccessAllowedAceEx(ACL_REVISION_DS, flags, access, target)
        SetNamedSecurityInfo(eggdir, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
                             None, None, acl, None)

def fix_egg_permissions(dir):
    """Fixup egg file permissions."""
    # On Windows 2003, it appears that *.egg files do not get an ACE that
    # gives READ access to "Users". *.egg directories seem to be OK, as well
    # as egg files under Windows 2008.
    glob = os.path.join(dir, '*.egg')
    result = FindFilesW(glob)
    nfixup = 0
    target = LookupAccountName(None, 'Users')[0]
    for res in result:
        if res[0] & FILE_ATTRIBUTE_DIRECTORY:
            continue
        fname = os.path.join(dir, res[8])
        desc = GetNamedSecurityInfo(fname, SE_FILE_OBJECT,
                                    DACL_SECURITY_INFORMATION)
        acl = desc.GetSecurityDescriptorDacl()
        for i in range(acl.GetAceCount()):
            ace = acl.GetAce(i)
            if ace[2] == target:
                break  # assume the ACE is correct
        else:
            access = FILE_GENERIC_READ
            acl.AddAccessAllowedAce(ACL_REVISION_DS, access, target)
            SetNamedSecurityInfo(fname, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
                                 None, None, acl, None)
            nfixup += 1
    if nfixup:
        print 'Fixed %d eggs with wrong permissions.' % nfixup
    else:
        print 'All eggs have correct permissions.'


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
    create_egg_cache(eggdir)
    dir = os.path.join(sys.exec_prefix, 'Lib', 'site-packages')
    fix_egg_permissions(dir)
