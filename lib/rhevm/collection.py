#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest.collection import Collection


class RhevmCollection(Collection):

    def _filter_from_dict(self, dict):
        conditions = ['1']
        for key in dict:
            conditions.append('$_.%s -eq "%s"' % (key, dict[key]))
        filter = '? { %s }' % ' -and '.join(conditions)
        return filter

    def _cmdline_from_dict(self, dict):
        arguments = []
        for key in dict:
            arguments.append('-%s "%s"' % (key, dict[key]))
        cmdline = ' '.join(arguments)
        return cmdline
