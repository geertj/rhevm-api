#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import binascii
import httplib as http
import yaml
from xml.etree import ElementTree as etree

from rest import InputFilter, OutputFilter, Error
from rest.api import request, response, collection

from rhevm.api import powershell
from rhevm.powershell import PowerShellError


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
                        reason='Illegal Authorization value')
        try:
            powershell.execute('Login-User %s %s' % (username, password))
        except PowerShellError:
            headers = [('WWW-Authenticate', 'Basic realm=rhev')]
            raise Error(http.UNAUTHORIZED, headers,
                        reason='Illegal username/password')
        return input


class StructuredInput(InputFilter):
    """Convert XML or YAML input to a dictionary representation."""

    def filter(self, input):
        ctype = request.header('Content-Type')
        if ctype == 'text/xml':
            xml = etree.fromstring(input)
            input = {}
            for child in xml:
                result[child.tag.lower()] = child.text
        elif ctype == 'text/yaml':
            result = yaml.load(input)
        else:
            return input
        return result


class StructuredOutput(OutputFilter):
    """Convert a (list of) dictionary representation to XML or YAML."""

    def filter(self, output):
        if not isinstance(output, dict) and not isinstance(output, list):
            return output
        ctype = request.header('Content-Type')
        if ctype == 'text/xml':
            if isinstance(output, list):
                root = etree.Element(collection.name)
                for entry in output:
                    elem = etree.SubElement(root, collection.objectname)
                    for key in entry:
                        subelem = etree.SubElement(elem, key.lower())
                        subelem.text = entry[key]
            elif isinstance(output, dict):
                root = etree.Element(collection.objectname)
                for key in output:
                    elem = etree.SubElement(root, key.lower())
                    elem.text = output[key]
            output = etree.tostring(root)
            response.set_header('Content-Type', 'text/xml')
        elif ctype == 'text/yaml':
            output = yaml.dump(output, default_flow_style=False)
            response.set_header('Content-Type', 'text/yaml')
        return output
