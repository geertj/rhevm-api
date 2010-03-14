#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rest import InputFilter, OutputFilter
from rest.filter import LOWER, HIGHER

from rhevm.api import powershell
from rhevm.collection import RhevmCollection


class DataCenterInput(InputFilter):
    """Fix some ideosyncrasies with respect to property names."""
    
    def filter(self, input):
        if not isinstance(input, dict):
            return input
        if 'type' in input:
            input['datacentertype'] = input.pop('type')
        return input


class DataCenterOutput(OutputFilter):

    def filter(self, output):
        if not isinstance(output, dict):
            return output
        if 'datacenterid' in output:
            output['id'] = output.pop('datacenterid')
        return output


class DataCenterCollection(RhevmCollection):

    name = 'datacenters'
    objectname = 'datacenter'

    def show(self, id):
        filter = self._filter_from_dict({'Name': id})
        result = powershell.execute('Select-DataCenter | %s' % filter)
        if len(result) != 1:
            return
        return result[0]

    def list(self, **filter):
        filter = self._filter_from_dict(filter)
        result = powershell.execute('Select-DataCenter | %s' % filter)
        return result

    def create(self, input):
        cmdline = self._cmdline_from_dict(input)
        result = powershell.execute('Add-DataCenter %s' % cmdline)
        return result[0]['Name']

    def update(self, id, input):
        filter = self._filter_from_dict({'DataCenterId': id})
        result = powershell.execute('Select-DataCenter | %s' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('$dc = Select-DataCenter | %s' % filter)
        for key in input:
            powershell.execute('$dc.%s = "%s"' % (key, input[key]))
        powershell.execute('Update-DataCenter -DataCenterObject $dc')

    def delete(self, id):
        filter = self._filter_from_dict({'DataCenterId': id})
        result = powershell.execute('Select-DataCenter | %s' % filter)
        if len(result) != 1:
            raise KeyError
        powershell.execute('Remove-DataCenter -DataCenterId %s' % id)


def setup(application):
    application.add_input_filter(DataCenterInput(), collection='datacenters',
                                 priority=LOWER)
    application.add_output_filter(DataCenterOutput(), collection='datacenters',
                                  priority=HIGHER)
