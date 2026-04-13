# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    iys_sms_consent = fields.Selection(
        selection=[('ONAY', 'Approved'), ('RET', 'Rejected'), ('pending', 'Pending')],
        string='IYS SMS Consent (MESAJ)',
        default='pending',
        tracking=True,
    )

    def _iys_consent_items(self):
        items = super()._iys_consent_items()
        items.append((self.verimor_mobile, 'MESAJ', self.iys_sms_consent))
        return items
