# -*- coding: utf-8 -*-
import logging
from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IapAccount(models.Model):
    _inherit = 'iap.account'

    provider = fields.Selection(
        selection_add=[('sms_verimor', 'SMS Verimor')],
        ondelete={'sms_verimor': 'cascade'},
    )
    sms_username = fields.Char(
        string='SMS Username',
        help='Verimor account username (e.g. 908501234567)',
    )
    sms_password = fields.Char(string='SMS Password')
    sms_source_addr = fields.Char(
        string='Sender ID (Başlık)',
        help='Approved sender name registered on Verimor OIM panel',
    )

    def _get_service_from_provider(self):
        if self.provider == 'sms_verimor':
            return 'sms'
        return super()._get_service_from_provider()

    def action_check_sms_balance(self):
        """Fetch and display the current SMS balance from Verimor."""
        self.ensure_one()
        if self.provider != 'sms_verimor':
            raise UserError(self.env._('Only applicable for SMS Verimor accounts.'))
        if not self.sms_username or not self.sms_password:
            raise UserError(self.env._('SMS credentials are not configured.'))

        import requests
        try:
            resp = requests.get(
                'https://sms.verimor.com.tr/v2/balance',
                params={'username': self.sms_username, 'password': self.sms_password},
                timeout=10,
            )
            if resp.status_code == 200:
                raise UserError(self.env._('Verimor SMS Balance: %s', resp.text.strip()))
            else:
                raise UserError(
                    self.env._('Balance check failed (HTTP %s): %s', resp.status_code, resp.text)
                )
        except requests.RequestException as exc:
            raise UserError(self.env._('Network error: %s', str(exc))) from exc
