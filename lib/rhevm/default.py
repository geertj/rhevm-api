#
# This file is part of Python-REST. Python-REST is free software that is
# made available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# Python-REST is copyright (c) 2010 by the Python-REST authors. See the file
# "AUTHORS" for a complete overview.

from rest.filter import RequireContentType, ExceptionHandler
from argproc.error import Error as ArgProcError
from rhevm.filter import RequireAuthentication


class HandleArgumentError(ExceptionHandler):

    def handle(self, exception):
        if isinstance(exception, ArgProcError):
            reason = 'Error processing arguments: %s' % str(exception)
            return Error(http.BAD_REQUEST, reason=reason)
        return exception


def setup(app):
    app.add_input_filter(RequireAuthentication())
    app.add_input_filter(RequireContentType(['text/xml', 'text/yaml']),
                         action=['create', 'update'])
    app.add_exception_handler(HandleArgumentError())
