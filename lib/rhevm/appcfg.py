#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import yaml
import binascii

from xml.etree import ElementTree as etree
from rest import InputFilter, OutputFilter, ExceptionHandler, Error
from rest import http, AssertInputFormat, AssertAcceptableOutputFormat
from rest.api import request, response, collection
from argproc.error import Error as ArgProcError
import rhevm
from rhevm.api import powershell
from rhevm.powershell import PowerShellError
from rhevm.util import create_cmdline


class RequireAuthentication(InputFilter):
    """Require Basic authentication."""

    def filter(self, input):
        auth = request.header('Authorization')
        if not auth:
            headers = [('WWW-Authenticate', 'Basic realm=rhev')]
            raise Error(http.UNAUTHORIZED, headers,
                        reason='No Authorization header')
        try:
            method, auth = auth.split(' ')
        except ValueError:
            raise Error(http.BAD_REQUEST,
                reason='Illegal Authorization header')
        if method != 'Basic':
            headers = [('WWW-Authenticate', 'Basic realm=rhev')]
            raise Error(http.UNAUTHORIZED, headers,
                        reason='Illegal Authorization scheme')
        try:
            username, password = auth.decode('base64').split(':')
        except (ValueError, binascii.Error):
            raise Error(http.BAD_REQUEST,
                        reason='Illegal Authorization header')
        if '@' in username:
            try:
                username, domain = username.split('@')
            except ValueError:
                raise Error(http.BAD_REQUEST, reason='Illegal user name')
        else:
            domain = None
        args = { 'UserName': username, 'Password': password, 'Domain': domain }
        cmdline = create_cmdline(**args)
        try:
            powershell.execute('Login-User %s' % cmdline)
        except PowerShellError:
            headers = [('WWW-Authenticate', 'Basic realm=rhev')]
            raise Error(http.UNAUTHORIZED, headers,
                        reason='Illegal username/password')
        result = powershell.execute('Get-Version')
        version = tuple(map(int, (result[0][i] for i in (
                            'Major', 'Minor', 'Build', 'Revision'))))
        powershell.version = version
        return input


class StructuredInput(InputFilter):
    """Convert XML or YAML input to a dictionary representation."""

    def __init__(self, argproc=None):
        self.argproc = argproc
        
    def filter(self, input):
        ctype = request.header('Content-Type')
        if not input or not ctype:
            return input
        if ctype == 'text/xml':
            xml = etree.fromstring(input)
            input = {}
            for child in xml:
                result[child.tag.lower()] = child.text
        elif ctype == 'text/yaml':
            result = yaml.load(input)
        else:
            return input
        if self.argproc:
            tags = [request.match['action']]
            result = self.argproc.process(result, tags=tags)
        return result


class StructuredOutput(OutputFilter):
    """Convert a (list of) dictionary representation to XML or YAML."""

    def __init__(self, argproc=None):
        self.argproc = argproc

    def filter(self, output):
        if not output or isinstance(output, basestring):
            return output
        if self.argproc:
            tags = [request.match['action']]
            if isinstance(output, list):
                output = [ self.argproc.reverse(entry, tags=tags)
                           for entry in output ]
            else:
                output = self.argproc.reverse(output, tags=tags)
        accept = http.parse_accept(request.header('Accept'))
        for ctype,params in accept:
            if ctype in ('text/yaml', 'text/xml'):
                break
        else:
            ctype = request.header('Content-Type')
            if ctype not in ('text/yaml', 'text/xml'):
                ctype = 'text/yaml'
        if ctype == 'text/yaml':
            output = yaml.dump(output, default_flow_style=False, version=(1,1))
            response.set_header('Content-Type', 'text/yaml')
        elif ctype == 'text/xml':
            if isinstance(output, list):
                root = etree.Element(collection.name)
                for entry in output:
                    elem = etree.SubElement(root, collection.objectname)
                    for key in entry:
                        subelem = etree.SubElement(elem, key)
                        subelem.text = entry[key]
            elif isinstance(output, dict):
                root = etree.Element(collection.objectname)
                for key in output:
                    elem = etree.SubElement(root, key)
                    elem.text = output[key]
            output = etree.tostring(root)
            response.set_header('Content-Type', 'text/xml')
        return output


class HandleArgProcError(ExceptionHandler):
    """Handle an ArgProc error (return 400 (BAD_REQUEST))."""

    def handle(self, exception):
        if isinstance(exception, ArgProcError):
            reason = 'Error processing arguments: %s' % str(exception)
            return Error(http.BAD_REQUEST, reason=reason)
        return exception


class AddServerIdentification(OutputFilter):
    """Add a Server: header to the response."""

    def filter(self, output):
        server = 'rhevm-api/%s' % '.'.join(map(str, rhevm.version))
        server += ' rhevm/%s' % '.'.join(map(str, powershell.version))
        response.set_header('Server', server)
        return output


def setup_module(app):
    app.add_input_filter(RequireAuthentication())
    app.add_input_filter(AssertInputFormat(['text/xml', 'text/yaml']),
                         action=['create', 'update'])
    app.add_input_filter(AssertAcceptableOutputFormat(['text/xml',
                         'text/yaml']), action=['create', 'show', 'list'])
    app.add_output_filter(AddServerIdentification())
    app.add_exception_handler(HandleArgProcError())
