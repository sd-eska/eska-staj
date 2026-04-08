# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── SMS credentials ────────────────────────────────────────────────────────
    verimor_sms_username = fields.Char(
        string='Verimor SMS Username',
        help='Verimor API username (e.g. 908501234567)',
        config_parameter='verimor.sms.username',
    )
    verimor_sms_password = fields.Char(
        string='Verimor SMS Password',
        help='Verimor API password',
        config_parameter='verimor.sms.password',
    )
    verimor_sms_source_addr = fields.Char(
        string='Verimor SMS Sender ID',
        help='Approved sender name / title (e.g. FIRMAADI)',
        config_parameter='verimor.sms.source_addr',
    )

    # ── PBX / Bulutsantralim credentials ──────────────────────────────────────
    verimor_pbx_api_key = fields.Char(
        string='Bulutsantralim API Key',
        help='API key obtained from Verimor Bulutsantralim panel',
        config_parameter='verimor.pbx.api_key',
    )
    verimor_pbx_extension = fields.Char(
        string='Bulutsantralim Extension',
        help='Default extension / DID to dial from (e.g. 1001)',
        config_parameter='verimor.pbx.extension',
    )
