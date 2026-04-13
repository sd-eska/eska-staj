# -*- coding: utf-8 -*-
from odoo import fields, models


class IapAccount(models.Model):
    _inherit = 'iap.account'

    provider = fields.Selection(
        selection_add=[('iys_pbx', 'IYS PBX (Bulutsantralim)')],
        ondelete={'iys_pbx': 'cascade'},
    )
    pbx_api_key = fields.Char(
        string='Bulutsantralim API Key',
        help='API key from the Bulutsantralim management panel',
    )
    pbx_extension = fields.Char(
        string='Default Extension',
        help='Extension/DID to dial from for click-to-call (e.g. 1001)',
    )

    def _get_service_from_provider(self):
        if self.provider == 'iys_pbx':
            return 'pbx'
        return super()._get_service_from_provider()
