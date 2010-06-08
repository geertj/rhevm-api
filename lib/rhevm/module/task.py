#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from rhevm.api import powershell
from rhevm.util import *
from rhevm.collection import RhevmCollection


class TaskCollection(RhevmCollection):
    """REST API for managing a VM's network cards."""

    name = 'tasks'
    entity_transform = """
        $!type <=> $!type
        $status <= $Status
        $result <= $Result
        $exception <= $Exception
        $message <= $Message
        $running <= $TaskIsRunning
        $state <= subif($TaskInUnsualState, True, 'unusual', 'normal')
        $success <= $TaskEndedSuccessfully
        """

    def show(self, id):
        cmdline = create_cmdline(CommandTaskIdList=id)
        # XXX: this does not work yet. Finding out more info on
        # Get-TasksStatus.
        result = powershell.execute('Get-TasksStatus %s' % cmdline)
        if len(result) != 1:
            raise KeyError
        return result[0]


def setup_module(app):
    app.add_collection(TaskCollection())
