#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rhevm.api import powershell

def create_filter(**kwargs):
    conditions = ['1']
    for key in kwargs:
        conditions.append('$_.%s -eq "%s"' % (key, kwargs[key]))
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
            arguments.append('-%s "%s"' % (key, value))
    cmdline = ' '.join(arguments)
    return cmdline

def cluster_id(name):
    """Return the cluster ID for a cluster name."""
    filter = create_filter(name=name)
    result =powershell.execute('Select-Cluster | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Cluster not found.'
    return result[0]['ClusterID']

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

def template_name(id):
    """Retur the template name for a given ID."""
    filter = create_filter(templateid=id)
    result =powershell.execute('Select-Template | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Template not found.'
    return result[0]['Name']

def host_id(name):
    """Return the host ID for a host name."""
    filter = create_filter(name=name)
    result = powershell.execute('Select-Host | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Host not found.'
    return result[0]['HostID']

def host_name(id, cluster):
    """Retur the host name for a given ID."""
    if id in ('-1', None):
        return
    filter = create_filter(hostid=id, hostclusterid=cluster)
    result = powershell.execute('Select-Host | %s' % filter)
    if len(result) != 1:
        return
    return result[0]['Name']

def pool_id(name):
    """Return the pool ID for a pool name."""
    filter = create_filter(name=name)
    result = powershell.execute('Select-VmPool | %s' % filter)
    if len(result) != 1:
        raise KeyError, 'Pool not found.'
    return result[0]['PoolID']

def pool_name(id):
    """Retur the pool name for a given ID."""
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
    return s == 'True'

def equals(s, ref):
    return s == ref
