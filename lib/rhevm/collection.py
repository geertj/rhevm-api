#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest.collection import Collection
from rest.api import request
from rhevm.api import powershell


class RhevmCollection(Collection):
    """Base class for all rhevm-api collections."""

    def _get_tags(self):
        tags = super(RhevmCollection, self)._get_tags()
        tags.append('rhevm%d%s' % powershell.version[:2])
        if 'command' in request.args:
            tags.append(request.args['command'])
        return tags
