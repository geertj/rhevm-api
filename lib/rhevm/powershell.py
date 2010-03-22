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

    _re_separator = re.compile('-+')

    def _parse_objects(self, output):
        """INTERNAL: Parse a list of PowerShell objects."""
        result = []
        state = 'DETECT_FORM'
        lines = output.splitlines()
        for line in lines:
            if state == 'DETECT_FORM':
                if not line:
                    continue
                p1 = line.find(':')
                if p1 == -1:
                    keys = line.split()
                    result.append({})
                    state = 'SKIP_HYPHENS_SHORT_FORM'
                else:
                    key = line[:p1].strip()
                    value = line[p1+1:].strip()
                    result.append({})
                    result[-1][key] = value or None
                    state = 'READ_OBJECT_LONG_FORM'
            elif state == 'SKIP_HYPHENS_SHORT_FORM':
                separators = line.strip().split()
                if len(separators) != len(keys):
                    raise ParseError
                for sep in separators:
                    if not self._re_separator.match(sep):
                        raise ParseError
                state = 'READ_OBJECT_SHORT_FORM'
            elif state == 'READ_OBJECT_SHORT_FORM':
                values = line.split()
                if len(values) != len(keys):
                    raise ParseError
                for i in range(len(keys)):
                    result[-1][keys[i]] = values[i]
                state = 'SKIP_TRAILING_NEWLINES'
            elif state == 'NEW_OBJECT_LONG_FORM':
                if not line:
                    continue
                p1 = line.find(':')
                if p1 == -1:
                    raise ParseError
                key = line[:p1].strip()
                value = line[p1+1:].strip()
                result.append({})
                result[-1][key] = value or None
                state = 'READ_OBJECT_LONG_FORM'
            elif state == 'READ_OBJECT_LONG_FORM':
                if not line:
                    state = 'NEW_OBJECT_LONG_FORM'
                    continue
                p1 = line.find(':')
                if p1 == -1:
                    raise ParseError
                key = line[:p1].strip()
                value = line[p1+1:].strip()
                result[-1][key] = value or None
            elif state == 'SKIP_TRAILING_NEWLINES':
                if line and not line.isspace():
                    raise ParseError
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
        script = 'Write-Host "START-OF-OUTPUT-MARKER";'
        script += '%s;' % command 
        script += 'Write-Host "END-OF-OUTPUT-MARKER $?";'
        self.logger.debug('Executing powershell: %s' % script)
        self.child.sendline(script)
        try:
            # Write-Host does not seem to be generating a \r ...
            self.child.expect('START-OF-OUTPUT-MARKER\r?\n')
            self.child.expect('END-OF-OUTPUT-MARKER (True|False)\r?\n')
        except TIMEOUT:
            self.logger.debug('PExpect state: %s' % str(self.child))
            raise ParseError, 'TIMEOUT in PowerShell command.'
        status = bool(self.child.match.group(1) == 'True')
        output = self.child.before
        if status:
            if output.startswith('\r\n'):
                result = self._parse_objects(output)
            else:
                result = output
        else:
            error = self._parse_error(output)
            raise error
        return result
