#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import binascii

from rest import InputFilter, OutputFilter, ExceptionHandler, Error
from rest import http
from rest.api import request, response
from rest.entity import FormatEntity
from rest.resource import Resource

import rhevm
from rhevm.api import powershell
from rhevm.powershell import PowerShellError, WindowsError


class RequireAuthentication(InputFilter):
    """Require Basic authentication."""

    def filter(self, input):
        auth = request.header('Authorization')
        if not auth:
            headers = [('WWW-Authenticate', 'Basic realm=rhevm')]
            raise Error(http.UNAUTHORIZED, headers,
                        reason='No Authorization header')
        try:
            method, auth = auth.split(' ')
        except ValueError:
            raise Error(http.BAD_REQUEST,
                reason='Illegal Authorization header')
        if method != 'Basic':
            headers = [('WWW-Authenticate', 'Basic realm=rhevm')]
            raise Error(http.UNAUTHORIZED, headers,
                        reason='Illegal Authorization scheme')
        try:
            username, password = auth.decode('base64').split(':')
        except (ValueError, binascii.Error):
            raise Error(http.BAD_REQUEST,
                        reason='Illegal Authorization header')
        try:
            username, domain = username.split('@')
        except ValueError:
            raise Error(http.BAD_REQUEST, reason='Illegal user name')
        auth = { 'username': username, 'password': password,
                 'domain': domain }
        try:
            powershell = rhevm.api.pool.get(auth)
        except (PowerShellError, WindowsError):
            headers = [('WWW-Authenticate', 'Basic realm=rhevm')]
            raise Error(http.UNAUTHORIZED, headers, reason='Could not logon.')
        rhevm.api.powershell._register(powershell)
        return input


class HandlePowerShellError(ExceptionHandler):
    """Handle a PowerShell error -> 400 BAD REQUEST."""

    def handle(self, exception):
        if not isinstance(exception, PowerShellError):
            return exception
        format = FormatEntity()
        error = Resource('error')
        error['id'] = exception.id
        error['message'] = exception.message
        body = format.filter(error)
        headers = response.headers
        raise Error(http.BAD_REQUEST, headers=headers, body=body)


class AddServerIdentification(OutputFilter):
    """Add a Server: header to the response."""

    def filter(self, output):
        server = response.header('Server')
        server += 'rhevm-api/%s' % '.'.join(map(str, rhevm.version))
        server += ' rhevm/%s' % '.'.join(map(str, powershell.version))
        response.set_header('Server', server)
        return output


def setup_module(app):
    app.add_input_filter(RequireAuthentication(), priority=20)
    app.add_output_filter(AddServerIdentification())
