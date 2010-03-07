#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import binascii
import httplib as http
from xml.etree import ElementTree as etree

from rest import (Application, InputFilter, OutputFilter,
                  Error as RestError)
from rest.api import request, response, collection

import rhevm.api
from rhevm.datacenter import DataCenterCollection
from rhevm.powershell import PowerShell, PowerShellError


class XmlInput(InputFilter):
    """Convert XML input to a dictionary representation."""

    def filter(self, input):
        if request.header('Content-Type') != 'text/xml':
            raise Error, http.UNSUPPORTED_MEDIA_TYPE
        try:
            xml = etree.fromstring(input)
        except:
            raise RestError(http.BAD_REQUEST, reason='Illegal XML input')
        result = {}
        for child in xml:
            result[child.tag] = child.text
        return result


class XmlOutput(OutputFilter):
    """Convert a (list of) dictionary representation of XML to XML."""

    def filter(self, output):
        if isinstance(output, dict):
            root = etree.Element(collection.objectname)
            for key in output:
                elem = etree.SubElement(root, key)
                elem.text = output[key]
        elif isinstance(output, list):
            root = etree.Element(collection.name)
            for entry in output:
                elem = etree.SubElement(root, collection.objectname)
                for key in entry:
                    subelem = etree.SubElement(elem, key)
                    subelem.text = entry[key]
        else:
            return output
        output = etree.tostring(root)
        response.set_header('Content-Type', 'text/xml')
        return output


class RequireAuthentication(InputFilter):
    """Require Basic authentication."""

    def filter(self, input):
        auth = request.header('Authorization')
        if not auth:
            headers = [('WWW-Authenticate', 'Basic realm=rhev')]
            raise RestError(http.UNAUTHORIZED, headers,
                    reason='No Authorization header')
        try:
            method, auth = auth.split(' ')
        except ValueError:
            raise RestError(http.BAD_REQUEST,
                reason='Illegal Authorization header')
        if method != 'Basic':
            headers = [('WWW-Authenticate', 'Basic realm=rhev')]
            raise RestError(http.UNAUTHORIZED, headers,
                    reason='Illegal Authorization scheme')
        try:
            username, password = auth.decode('base64').split(':')
        except (ValueError, binascii.Error):
            raise RestError(http.BAD_REQUEST,
                    reason='Illegal Authorization value')
        try:
            rhevm.api.powershell.execute('Login-User %s %s' % (username, password))
        except PowerShellError:
            headers = [('WWW-Authenticate', 'Basic realm=rhev')]
            raise RestError(http.UNAUTHORIZED, headers,
                    reason='Illegal username/password')
        return input


class RhevmApp(Application):
    """The RHEVM API application."""

    def setup_collections(self):
        self.add_collection(DataCenterCollection())

    def setup_filters(self):
        super(RhevmApp, self).setup_filters()
        self.add_input_filter(None, None, RequireAuthentication())
        self.add_input_filter(None, 'create', XmlInput())
        self.add_input_filter(None, 'update', XmlInput())
        self.add_output_filter(None, 'show', XmlOutput(), -1)
        self.add_output_filter(None, 'list', XmlOutput(), -1)

    def respond(self):
        powershell = PowerShell()
        rhevm.api.powershell._register(powershell)
        try:
            return super(RhevApp, self).respond()
        finally:
            rhevm.api.powershell._release()
            powershell.close()
