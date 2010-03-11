#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import re
import os.path
import logging

from winpexpect import winspawn, TIMEOUT
from rhevm.error import Error


class PowerShellError(Error):
    """A PowerShell command exited with an error."""

    def __init__(self, message=None, category=None, id=None):
        self.message = message
        self.category = category
        self.id = id

    def __str__(self):
        return self.message or ''


class ParseError(Error):
    """Error parsing PowerShell output."""


class PowerShell(object):
    """Execute Windows PowerShell commands."""

    def __init__(self):
        self.logger = logging.getLogger('rhevm.powershell')
        self.child = winspawn('powershell.exe -Command -')

    def _parse_objects(self, output):
        """INTERNAL: Parse a list of PowerShell objects."""
        result = []
        state = 'NEW_OBJECT'
        lines = output.splitlines()
        for line in lines:
            line = line.strip()
            if state == 'NEW_OBJECT':
                if not line:
                    continue
                p1 = line.find(':')
                if p1 == -1:
                    raise ParseError
                key = line[:p1].strip()
                value = line[p1+1:].strip()
                result.append({key: value})
                state = 'READ_OBJECT'
            elif state == 'READ_OBJECT':
                if not line:
                    state = 'NEW_OBJECT'
                    continue
                p1 = line.find(':')
                if p1 == -1:
                    raise ParseError
                key = line[:p1].strip()
                value = line[p1+1:].strip()
                result[-1][key] = value
        return result

    _re_error_end_header = re.compile('At line:\d+')
    _re_error_property = re.compile(
            '\s+\+ (CategoryInfo|FullyQualifiedErrorId)\s+:\s+(.*?)\s*$')
    _re_error_property_continuation = re.compile('\s+([^\s+].*?)\s*$')

    def _parse_error(self, output):
        """INTERNAL: Parse an error response."""
        lines = output.splitlines()
        state = 'READ_ERROR_MESSAGE'
        error = PowerShellError()
        for line in lines:
            if state == 'READ_ERROR_MESSAGE':
                error.message = line
                state = 'CONTINUE_ERROR_MESSAGE'
            elif state == 'CONTINUE_ERROR_MESSAGE':
                mobj = self._re_error_end_header.match(line)
                if not mobj:
                    error.message += line
                    continue
                state = 'READ_ERROR_PROPERTIES'
            elif state == 'READ_ERROR_PROPERTIES':
                mobj = self._re_error_property.match(line)
                if not mobj:
                    continue
                name, value = mobj.groups()
                if name == 'CategoryInfo':
                    error.category = value
                    state = 'CONTINUE_ERROR_CATEGORY'
                elif name == 'FullyQualifiedErrorId':
                    error.id = value
                    state = 'CONTINUE_ERROR_ID'
            elif state == 'CONTINUE_ERROR_CATEGORY':
                mobj = self._re_error_property_continuation.match(line)
                if mobj:
                    error.category += mobj.group(1)
                    continue
                mobj = self._re_error_property.match(line)
                if not mobj:
                    if not line or line.isspace():
                        state = 'DONE'
                        continue
                    raise ParseError
                name, value = mobj.groups()
                if name == 'FullyQualifiedErrorId':
                    error.id = value
                    state = 'CONTINUE_ERROR_ID'
                else:
                    state = 'READ_ERROR_PROPERTIES'
            elif state == 'CONTINUE_ERROR_ID':
                mobj = self._re_error_property_continuation.match(line)
                if mobj:
                    error.id += mobj.group(1)
                    continue
                mobj = self._re_error_property.match(line)
                if not mobj:
                    if not line or line.isspace():
                        state = 'DONE'
                        continue
                    raise ParseError
                name, value = mobj.groups()
                if name == 'CategoryInfo':
                    error.category = value
                    state = 'CONTINUE_ERROR_CATEGORY'
                else:
                    state = 'READ_ERROR_PROPERTIES'
        return error

    def close(self):
        """Close the powershell process."""
        self.child.sendline('Exit')
        try:
            self.child.wait(timeout=2)
        except TIMEOUT:
            self.child.terminate()

    def execute(self, command):
        """Execute a command. Return a string, a list of objects, or
        raises an exception."""
        command = '%s; Write-Host "END-OF-OUTPUT-MARKER $?"' % command
        self.logger.debug('Executing powershell: %s' % command)
        self.child.sendline(command)
        try:
            self.child.expect('END-OF-OUTPUT-MARKER (True|False)')
        except TIMEOUT:
            raise ParseError, 'Could not parse PowerShell output.'
        status = self.child.match.group(1) == 'True' and True or False
        if status:
            output = self.child.before
            p1 = output.find('\n')
            if p1 != -1 and output[:p1+1].isspace():
                result = self._parse_objects(self.child.before)
            else:
                result = output
        else:
            error = self._parse_error(self.child.before)
            raise error
        return result
