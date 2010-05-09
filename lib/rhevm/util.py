#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import sys
import logging

from rhevm.api import powershell
from rhevm.query import QueryParser
from rhevm.powershell import PowerShell, escape


def setup_logging(debug):
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


def create_powershell(username, password, domain):
    """Create a powershell object."""
    powershell = PowerShell()
    auth = { 'username': username, 'domain': domain, 'password': password }
    if hasattr(sys, 'isapidllhandle'):
        powershell.start(**auth)
        powershell.execute('Login-User')
    else:
        powershell.start()
        powershell.execute('Login-User %s' % create_cmdline(**auth))
    result = powershell.execute('Get-Version')
    version = tuple(map(int, (result[0][i] for i in (
                        'Major', 'Minor', 'Build', 'Revision'))))
    powershell.version = version
    return powershell


def cached(func):
    """Decorator that caches the result of a function."""
    cache = {}
    def cached_result(*args):
        try:
            return cache[args]
        except KeyError:
            ret = func(*args)
            cache[args] = ret
            return ret
    return cached_result

def create_filter(**kwargs):
    conditions = ['1']
    for key in kwargs:
        conditions.append('$_.%s -eq %s' % (key, escape(str(kwargs[key]))))
    filter = '? { %s }' % ' -and '.join(conditions)
    return filter

def create_cmdline(**kwargs):
    arguments = []
    for key in kwargs:
        value = kwargs[key]
        if value in (None, False):
            pass
        elif value is True:
            arguments.append('-%s' % key)
        elif key.endswith('Object'):
            # XXX: ugly hack:
            arguments.append('-%s %s' % (key, value))
        else:
            arguments.append('-%s %s' % (key, escape(str(value))))
    cmdline = ' '.join(arguments)
    return cmdline

def create_setattr(obj, **kwargs):
    statements = []
    for key in kwargs:
        value = kwargs[key]
        statements.append('$%s.%s = %s' % (obj, key, escape(str(value))))
    statement = ';'.join(statements) + ';'
    return statement

@cached
def cluster_id(name):
    """Return the cluster ID for a cluster name."""
    filter = create_filter(name=name)
    result =powershell.execute('Select-Cluster | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Cluster not found.'
    return result[0]['ClusterID']

@cached
def cluster_name(id):
    """Retur the cluster name for a given ID."""
    filter = create_filter(clusterid=id)
    result =powershell.execute('Select-Cluster | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Cluster not found.'
    return result[0]['Name']

def template_object(name):
    """Return the template ID for a template name."""
    filter = create_filter(name=name)
    result = powershell.execute('Select-Template | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Template not found'
    powershell.execute('$template = Select-Template | %s' % filter)
    return '$template'

@cached
def template_name(id):
    """Retur the template name for a given ID."""
    filter = create_filter(templateid=id)
    result =powershell.execute('Select-Template | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Template not found.'
    return result[0]['Name']

@cached
def host_id(name):
    """Return the host ID for a host name."""
    filter = create_filter(name=name)
    result = powershell.execute('Select-Host | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Host not found.'
    return result[0]['HostID']

@cached
def host_name(id, cluster):
    """Retur the host name for a given ID."""
    if id in ('-1', None):
        return
    filter = create_filter(hostid=id, hostclusterid=cluster)
    result = powershell.execute('Select-Host | %s' % filter)
    if len(result) != 1:
        return
    return result[0]['Name']

@cached
def pool_id(name):
    """Return the pool ID for a pool name."""
    filter = create_filter(name=name)
    result = powershell.execute('Select-VmPool | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Pool not found.'
    return result[0]['PoolID']

@cached
def pool_name(id):
    """Retur the pool name for a given ID."""
    if id == '-1':
        return None
    filter = create_filter(poolid=id)
    result =powershell.execute('Select-VmPool | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Pool not found.'
    return result[0]['Name']

def lower(s):
    return s.lower()

def upper(s):
    return s.upper()

def boolean(s):
    return s in ('True', 'true', True)

def subif(s, ref, sub):
    return sub if s == ref else s

def equals(s, ref):
    return s == ref

def invert(b):
    return not b

def adjust(s):
    if s == 'cdrom':
        return 'CD'
    elif s == 'harddisk':
        return 'HardDisk'
    elif s == 'network':
        return 'Network'
    elif s == 'vnc':
        return 'VNC'
    elif s == 'spice':
        return 'Spice'

def parse_query(s):
    parser = QueryParser()
    parsed = parser.parse(s)
    return parsed.tostring()

def bootorder(s):
    """Validate a boot order."""
    order = ''
    parts = s.split(',')
    for part in parts:
        if part == 'harddisk':
            order += 'C'
        elif part == 'cdrom':
            order += 'D'
        elif part == 'network':
            order += 'N'
        else:
            raise ValueError, 'Invalid boot order.'
    return order
