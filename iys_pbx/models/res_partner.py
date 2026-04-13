# -*- coding: utf-8 -*-
import logging
import requests
from odoo import models
from odoo.exceptions import UserError
from odoo.addons.iys.models.res_partner import _normalize_phone

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_iys_click_to_call(self):
        """Initiate a click-to-call via Bulutsantralim PBX API."""
        self.ensure_one()
        account = self.env['iap.account'].search(
            [('provider', '=', 'iys_pbx')], limit=1
        )
        if not account or not account.pbx_api_key:
            raise UserError(self.env._('Bulutsantralim API key is not configured.'))

        destination = _normalize_phone(self.mobile or self.phone or '')
        if not destination:
            raise UserError(
                self.env._('No valid Turkish mobile number found on partner %s.', self.name)
            )

        # Check IYS call consent from the central consent store
        Consent = self.env['iys.consent']
        if Consent._is_blocked(destination, 'ARAMA'):
            raise UserError(
                self.env._('Partner %s has rejected IYS call consent (ARAMA). Call blocked.', self.name)
            )

        url = 'https://pbx.verimor.com.tr/v2/call.json'
        payload = {
            'api_key': account.pbx_api_key,
            'source_addr': account.pbx_extension or '',
            'dest_addr': destination,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': self.env._('Call Initiated'),
                        'message': self.env._('Call to %s is being connected.', self.name),
                        'type': 'success',
                        'sticky': False,
                    },
                }
            else:
                raise UserError(
                    self.env._('Call failed (HTTP %(code)s): %(text)s',
                               code=resp.status_code, text=resp.text)
                )
        except requests.RequestException as exc:
            raise UserError(self.env._('API error: %s', str(exc))) from exc
