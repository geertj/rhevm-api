#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import re
import os
import os.path
import stat
import logging
import itertools

from winpexpect import winspawn, TIMEOUT, WindowsError
from rhevm.error import Error
from compat import namedtuple


def escape(s):
    return '"%s"' % s.replace('`', '``').replace('"', '`"')


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
            newpath += os.environ['Path']
            os.environ['Path'] = newpath
        self.child = winspawn('powershell.exe -Command -', **args)

    def _detect_short_form(self, output):
        """INTERNAL detect if output is in short form."""
        short = False
        s_read_first_line, s_read_second_line = range(2)
        state = s_read_first_line
        for line in output:
            if state == s_read_first_line:
                if line and not line.isspace():
                    state = s_read_second_line
            elif state == s_read_second_line:
                if line.startswith('-'):
                    short = True
                break
        return short

    def _parse_objects_short_form(self, output):
        """INTERNAL: Parse a list of PowerShell objects (short form)."""
        s_read_keys, s_skip_hyphens, s_read_values = range(3)
        state = s_read_keys
        for line in output:
            if state == s_read_keys:
                if line and not line.isspace():
                    keys = line.strip().split()
                    state = s_skip_hyphens
            elif state == s_skip_hyphens:
                assert line.startswith('-')
                state = s_read_values
            elif state == s_read_values:
                values = line.strip().split()
        if state != s_read_values:
            raise ParseError
        if len(keys) != len(values):
            raise ParseError
        object = dict(zip(keys, values))
        return [object]

    _re_key_value = re.compile('\s*(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)'
                               '(\s+:)?\s+(?P<value>.*)$')
    _re_nested_object = re.compile('Class Name: (.*)')
    _re_continuation = re.compile('\s+(?P<value>[^\s].*)$')

    def _parse_objects_long_form(self, output):
        """INTERNAL: Parse a list of PowerShell objects."""
        # PowerShell output was not made for parsing... What we have below
        # should work reasonably well, but it's not pretty.
        result = [];
        state = namedtuple('state', ('obstack', 'indent', 'lastkey',
                                     'lastvaluepos'))
        state.obstack = []
        state.indent = []
        for line in itertools.chain(output, [None]):  # Mark End of Input
            if not line or line.isspace():
                if state.obstack:
                    result.append(state.obstack[0])
                    del state.obstack[:]
                    del state.indent[:]
                continue
            match = self._re_continuation.match(line)
            if match and state.lastkey and \
                    match.start('value') == state.lastvaluepos:
                state.obstack[-1][state.lastkey] += match.group('value')
                continue
            match = self._re_key_value.match(line)
            if not match:
                # XXX: there appears to be no way to match continuations
                # in nested sub objects... For now ignore the continuation.
                #raise ParseError, 'Key/value regex did not match.'
                continue
            level = match.start('key')
            if not state.obstack:
                state.obstack.append({})
                state.indent.append(level)
            if level != state.indent[-1]:
                for ix,lvl in enumerate(state.indent):
                    if lvl == level:
                        break
                else:
                    raise ParseError, 'Unknow indent level.'
                npop = len(state.indent) - ix - 1
                for i in range(npop):
                    state.obstack.pop()
                    state.indent.pop()
            key = match.group('key')
            value = match.group('value')
            if self._re_nested_object.match(value):
                nested = {}
                state.obstack[-1][key] = nested
                state.obstack.append(nested)
                state.indent.append(match.start('value'))
                state.lastvaluepos = None
            elif not value:
                state.obstack[-1][key] = None
                state.lastvaluepos = None
            else:
                state.obstack[-1][key] = value
                state.lastkey = key
                state.lastvaluepos = match.start('value')
        return result

    _re_error_end_message = re.compile('At line:\d+')
    _re_error_property = re.compile('\s+\+ (?P<name>[a-zA-Z_][a-zA-Z0-9_]*)'
                                    '\s+:\s+(?P<value>.*)$')

    def _parse_error(self, output):
        """INTERNAL: Parse an error response."""
        error = PowerShellError(message='', category='', id='')
        s_read_message, s_read_properties = range(2)
        state = namedtuple('state', ('state', 'property'))
        state.state = s_read_message
        state.property = None
        for line in output:
            if state.state == s_read_message:
                if not line or line.isspace():
                    continue
                if self._re_error_end_message.match(line):
                    state.state = s_read_properties
                    continue
                error.message += line
            elif state.state == s_read_properties:
                if not line or line.isspace():
                    break
                match = self._re_error_property.match(line)
                if match:
                    name = match.group('name')
                    value = match.group('value')
                elif state.property:
                    name = state.property
                    value = line.lstrip()
                else:
                    continue
                if name == 'CategoryInfo':
                    error.category += value
                elif name == 'FullyQualifiedErrorId':
                    error.id += value
                state.property = name
        return error

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

    def execute(self, command):
        """Execute a command. Return a string, a list of objects, or
        raises an exception."""
        if self.child is None:
            self.start()
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
        output = output.splitlines()
        if status:
            if output and not output[0]:
                if self._detect_short_form(output):
                    result = self._parse_objects_short_form(output)
                else:
                    result = self._parse_objects_long_form(output)
            else:
                result = output
        else:
            error = self._parse_error(output)
            raise error
        return result
