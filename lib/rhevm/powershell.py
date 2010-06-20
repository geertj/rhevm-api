#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import os
import os.path
import re
import stat
import logging
from xml.etree import ElementTree as etree

from rest.resource import Resource
from winpexpect import winspawn, TIMEOUT, WindowsError
from rhevm.error import Error


def escape(s):
    return '"%s"' % s.replace('`', '``').replace('"', '`"')


class PowerShellError(Error):
    """A PowerShell command exited with an error."""

    def __init__(self, message=None, id=None):
        self.message = message
        self.id = id

    def __str__(self):
        return self.message or ''


class ParseError(Error):
    """Error parsing PowerShell output."""


class PowerShell(object):
    """Execute Windows PowerShell commands.""" 

    def __init__(self):
        self.logger = logging.getLogger('rhevm.powershell')
        self.child = None

    def start(self, **args):
        # On Windows 2008 R2, which is always 64-bit,  the PowerShell bindings
        # are only installed in the  32-bit "Windows on Windows" environment.
        syswow = r'C:\Windows\SysWOW64'
        try:
            st = os.stat(syswow)
        except OSError:
            st = None
        if st and stat.S_ISDIR(st.st_mode):
            newpath = os.path.join(syswow, 'WindowsPowerShell', 'v1.0')
            newpath += os.pathsep
            if newpath not in os.environ['Path']:
                newpath += os.environ['Path']
                os.environ['Path'] = newpath
        self.child = winspawn('powershell.exe -Command -', **args)

    def terminate(self):
        """Close the powershell process."""
        if not self.child:
            return
        self.child.sendline('Exit')
        try:
            self.child.wait(timeout=2)
        except TIMEOUT:
            self.child.terminate()
        self.child = None

    def _convert_xml_node(self, node):
        """INTERNAL: convert a single XML node to a Resource."""
        type = node.attrib['Type']
        if type in ('System.Int32', 'System.Int64'):
            return int(node.text)
        elif type == 'System.Boolean':
            return node.text == 'True'
        elif type == 'System.String':
            return node.text
        elif type == 'System.Version':
            # Why isn't this done automatically??
            parts = map(int, node.text.split('.'))
            items = zip(('Major', 'Minor', 'Build', 'Revision'), parts)
            resource = Resource('version', items)
            return resource
        elif type.startswith('System.'):
            return node.text
        elif type.startswith('RhevmCmd.'):
            type = type[9:]
            if type.startswith('CLI'):
                type = type[3:]
            resource = Resource(type.lower())
            for child in node:
                resource[child.attrib['Name']] = self._convert_xml_node(child)
            return resource
        elif type.startswith('VdcDAL.'):
            return self._convert_xml_node(node[0])
        elif type.endswith('[]'):
            result = []
            for child in node:
                result.append(self._convert_xml_node(child))
            return result
        elif type:
            raise ParseError, 'Unknown type: %s' % type

    def _parse_objects(self, output):
        """INTERNAL: Parse output of "ConvertTo-XML"."""
        xml = etree.fromstring(output)
        assert xml.tag == 'Objects'
        type = xml[0].attrib.get('Type')
        if type == 'System.Object[]' or type is None:
            xml = xml[0]
        result = []
        for child in xml:
            result.append(self._convert_xml_node(child))
        return result

    def _parse_error(self, output):
        """INTERNAL: Parse an XML formatted exception."""
        xml = etree.fromstring(output)
        error = PowerShellError()
        for node in xml[0]:
            name = node.attrib['Name']
            if name == 'Exception':
                message = node.text
                p1 = message.find(': ')
                if p1 == -1:
                    p1 = 0
                else:
                    p1 += 2
                p2 = message.find(' at System.')
                if p2 == -1:
                    p2 = len(message)
                error.message = message[p1:p2].strip()
            elif name == 'FullyQualifiedErrorId':
                id = node.text
                p1 = id.find(',')
                if p1 == -1:
                    p1 = len(id)
                error.id = 'rhevm.powershell.backend.%s' % id[:p1].lower()
        return error

    re_comment = re.compile('#.*$', re.M)
    re_whitespace = re.compile('\s+')

    def _compact(self, command):
        """INTERNAL: compat a powershell command (for logging)."""
        command = self.re_comment.sub('', command)
        command = self.re_whitespace.sub(' ', command)
        return command
        
    def execute(self, command):
        """Execute a command. Return a string, a list of objects, or
        raises an exception."""
        if self.child is None:
            self.start()
        script = """
            Write-Host "START-OF-OUTPUT-MARKER";
            try {
                $result = Invoke-Expression '%s';
                ConvertTo-XML $result -As String -Depth 5;
                $success = 1;
            } catch {
                # There's a circular reference in $_...
                ConvertTo-XML $_ -As String -Depth 1;
                $success = 0;
            }
            Write-Host "END-OF-OUTPUT-MARKER $success";
        """ % command
        script = self._compact(script)
        self.logger.debug('Executing powershell: %s' % script)
        self.child.sendline(script)
        try:
            # Write-Host does not seem to be generating a \r ...
            self.child.expect('START-OF-OUTPUT-MARKER\r?\n')
            self.child.expect('END-OF-OUTPUT-MARKER (1|0)\r?\n')
        except TIMEOUT:
            self.logger.debug('PExpect state: %s' % str(self.child))
            raise ParseError, 'TIMEOUT in PowerShell command.'
        status = self.child.match.group(1) == '1'
        output = self.child.before
        p1 = output.find('<?xml')
        if p1 == -1:
            p1 = len(output)
        textout = output[:p1]
        xmlout = output[p1:]
        xmlout = xmlout.replace('\r\n', '')  # line wrapping (sigh...)
        if status:
            if xmlout:
                objects = self._parse_objects(xmlout)
                return objects
            else:
                return textout
        else:
            error = self._parse_error(xmlout)
            raise error
