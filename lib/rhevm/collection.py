#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest import http
from rest.api import request
from rest.collection import Collection
from rest.api import request
from rhevm.api import powershell
from rest.error import error as HTTPReturn


class RhevmCollection(Collection):
    """Base class for all rhevm-api collections."""

    def _get_tags(self):
        tags = super(RhevmCollection, self)._get_tags()
        tags.append('rhevm%d%s' % powershell.version[:2])
        if 'command' in request.args:
            tags.append(request.args['command'])
        return tags

    def _get_detail(self):
        ctypes = ['text/xml', 'text/yaml']
        for i in range(4):
            ctypes.append('text/xml; detail=%s' % i)
            ctypes.append('text/yaml; detail=%s' % i)
        ctype = request.preferred_content_type(ctypes)
        if ctype is None:
            return
        sub, subtype, params = http.parse_content_type(ctype)
        try:
            detail = int(params.get('detail', '1'))
        except ValueError:
            raise HTTPReturn(http.NOT_ACCEPTABLE,
                             reason='Non-integer "detail" in Accept header.')
        return detail
