# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    iys_email_consent = fields.Selection(
        selection=[('ONAY', 'Approved'), ('RET', 'Rejected'), ('pending', 'Pending')],
        string='IYS Email Consent (EPOSTA)',
        default='pending',
        tracking=True,
    )

    def _iys_consent_items(self):
        items = super()._iys_consent_items()
        items.append((self.email, 'EPOSTA', self.iys_email_consent))
        return items
