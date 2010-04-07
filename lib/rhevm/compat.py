#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

"""
Compatiblity functions with Python 2.5 (the oldest version of Python that we
support = Python that was installed with RHEV 2.1).
"""

try:
    from collections import namedtuple
except ImportError:
    def namedtuple(name, fields):
        d = dict(zip(fields, [None]*len(fields)))
        return type(name, (object,), fields)
