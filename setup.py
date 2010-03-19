#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import sys
import os
import os.path
import urllib
import hashlib
import tarfile
import gzip
import inspect
import shutil
import stat

from setuptools import setup, Extension, Command


class download_deps(Command):
    """Download dependencies, with the objective to make a fat binary
    package."""

    user_options = []
    description = 'download dependencies (to be included in a binary package)'

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def _download_tgz(self, url, checksum):
        """Download a gzipped tarfile, check its checksum, and extract it."""
        p1 = url.rfind('/')
        fname = url[p1+1:]
        sys.stdout.write('downloading file %s ... ' % fname)
        sys.stdout.flush()
        urllib.urlretrieve(url, fname)
        sys.stdout.write('done\n')
        sha1 = hashlib.sha1()
        sys.stdout.write('comparing checksum ... ')
        sys.stdout.flush()
        fin = file(fname)
        while True:
            buffer = fin.read(4096)
            if not buffer:
                break
            sha1.update(buffer)
        if sha1.hexdigest() != checksum:
            sys.stderr.write('Illegal checksum for downloaded file.\n')
            sys.exit(1)
        sys.stdout.write('done\n')
        sys.stdout.write('extracting ... ')
        sys.stdout.flush()
        ftar = tarfile.open(fname, 'r:gz')
        ftar.extractall()
        sys.stdout.write('done\n')

    def run(self):
        depdir = os.path.join(topdir(), 'dep')
        shutil.rmtree(depdir)
        os.makedirs(depdir); os.chdir(depdir)
        #self._download_tgz('http://bitbucket.org/geertj/winpexpect/get/tip.tar.gz',
        #                   'd0925d9b4a481e7f58b8e95eb6f2c5a7aee3a328')
        #self._download_tgz('http://www.bitbucket.org/geertj/python-rest/get/tip.tar.gz',
        #                   'd344e6c06aad970cedd5375d3f12eff21a0158be')
        #self.download_tgz('http://bitbucket.org/geertj/argproc/get/tip.tar.gz',
        #                  '')
        self._download_tgz('http://www.dabeaz.com/ply/ply-3.3.tar.gz',
                           '23291d8127f9f7189957fe1ff8925494e389fca3')
 

def topdir():
    """Return the directory containing "setup.py"."""
    fname = inspect.getfile(sys.modules['__main__'])
    topdir = os.path.split(fname)[0]
    return topdir


def installed(name):
    depdir = os.path.join(topdir(), 'dep')
    try:
        st = os.stat(depdir)
    except OSErrpr:
        st = None
    return st and stat.S_ISDIR(st.st_mode)


def get_packages():
    dirs = {}; packages = []
    dirs['rhevm'] = 'lib/rhevm'
    packages += ['rhevm', 'rhevm.test']
    if installed('ply-3.3'):
        dirs['ply'] = 'dep/ply-3.3/ply'
        packages += ['ply']
    if installed('argrpoc'):
        dirs['argproc'] = 'dep/argproc/lib/argproc'
        packages += ['argproc', 'argproc.test']
    if installed('python-rest'):
        dirs['rest'] = 'dep/python-rest/lib/rest'
        packages += ['rest', 'rest.test']
    if installed('winpexpect'):
        dirs['pexpect'] = 'dep/winpexpect/lib'
        packages += ['pexpect']
    return dirs, packages


package_dir, packages = get_packages()

setup(
    name = 'rhevm-api',
    version = '0.1',
    description = 'A REST mapping of the PowerShell API of RHEV-M.',
    author = 'Geert Jansen',
    author_email = 'geert@boskant.nl',
    url = 'http://bitbucket.org/geertj/rhevm-api',
    license = 'MIT',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License : = OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application' ],
    package_dir = package_dir,
    packages = packages,
    test_suite = 'nose.collector',
    entry_points = { 'console_scripts': [ 'rhevmapi = rhevm.server:main' ] },
    cmdclass = { 'download_deps': download_deps }
)
