# -*- coding: utf-8 -*-
from __future__ import absolute_import

import hashlib
import json

from mgr_module import Option

from . import PLUGIN_MANAGER as PM
from . import interfaces as I  # noqa: E741,N812


@PM.add_plugin  # pylint: disable=too-many-ancestors
class SES7PMotd(I.CanMgr, I.Setupable, I.HasOptions):
    @PM.add_hook
    def get_options(self):
        return [Option(
            name='ses7p_motd_enabled',
            default=False,
            type='bool',
            desc='Enable the SES 7.1 message of the day')]

    @PM.add_hook
    def setup(self):
        # Check whether the MOTD has already been enabled. This is
        # done to ensure the SES7P announcement is not enabled on
        # every start of the Ceph Dashboard module and to allow the
        # administrator to disable it if necessary.
        enabled = self.mgr.get_module_option('ses7p_motd_enabled')
        if enabled:
            return
        # Note, we can not call the 'ceph dashboard motd set ...' command
        # here because it is not available at this time. To workaround
        # this issue we build and write the MOTD configuration ourself.
        message = 'There is an upgrade to SES 7.1 available, please check the ' \
                  '<a href="https://documentation.suse.com/ses/7/html/ses-all/upgrade-to-pacific.html">' \
                  'documentation</a> for more information.'  # noqa # pylint: disable=line-too-long
        value: str = json.dumps({
            'message': message,
            'md5': hashlib.md5(message.encode()).hexdigest(),
            'severity': 'danger',
            'expires': 0
        })
        self.mgr.set_module_option('motd', value)
        self.mgr.set_module_option('ses7p_motd_enabled', True)
