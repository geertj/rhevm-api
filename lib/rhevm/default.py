#
# This file is part of Python-REST. Python-REST is free software that is
# made available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# Python-REST is copyright (c) 2010 by the Python-REST authors. See the file
# "AUTHORS" for a complete overview.

from rest.filter import RequireContentType
from rhevm.filter import RequireAuthentication, StructuredInput, StructuredOutput


def setup(app):
    app.add_input_filter(RequireAuthentication())
    app.add_input_filter(RequireContentType(['text/xml', 'text/yaml']),
                         action=['create', 'update'])
    app.add_input_filter(StructuredInput(), action=['create', 'update'])
    app.add_output_filter(StructuredOutput(), action=['show', 'list'])
