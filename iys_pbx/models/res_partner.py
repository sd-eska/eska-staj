# -*- coding: utf-8 -*-
import logging
import requests
from odoo import fields, models
from odoo.exceptions import UserError
from odoo.addons.iys.models.res_partner import _normalize_phone

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    iys_call_consent = fields.Selection(
        selection=[('ONAY', 'Approved'), ('RET', 'Rejected'), ('pending', 'Pending')],
        string='IYS Call Consent (ARAMA)',
        default='pending',
        tracking=True,
    )

    def _iys_consent_items(self):
        items = super()._iys_consent_items()
        items.append((self.verimor_mobile, 'ARAMA', self.iys_call_consent))
        return items

    def action_iys_click_to_call(self):
        """
        Initiate a click-to-call via Odoo VoIP (voip.call).
        IYS ARAMA RET check happens before the call record is created.
        """
        self.ensure_one()
        destination = _normalize_phone(self.mobile or self.phone or '')
        if not destination:
            raise UserError(
                self.env._('No valid Turkish mobile number found on partner %s.', self.name)
            )

        # IYS ARAMA consent check
        Consent = self.env['iys.consent']
        if Consent._is_blocked(destination, 'ARAMA'):
            raise UserError(
                self.env._('Partner %s has rejected IYS call consent (ARAMA). Call blocked.', self.name)
            )

        # Delegate to Odoo VoIP — create a voip.call record (triggers the softphone)
        call = self.env['voip.call'].create({
            'phone_number': destination,
            'direction': 'outgoing',
            'partner_id': self.id,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._('Call Initiated'),
                'message': self.env._('Connecting call to %s via Odoo VoIP.', self.name),
                'type': 'success',
                'sticky': False,
            },
        }
