# -*- coding: utf-8 -*-
"""Override the SMS API to route all outgoing SMS through Verimor's v2 endpoint.

Odoo 18 architecture:
  - sms.sms._split_by_api() yields (SmsApiInstance, sms_recordset) pairs.
  - Each batch is sent via sms_api._send_sms_batch(messages, delivery_reports_url).
  - The return value must be a list of dicts:
      [{'uuid': str, 'state': str, 'failure_reason': str|None}, ...]
    where `state` is one of: 'success', 'processing', 'server_error',
    'wrong_number_format', 'insufficient_credit', …

Strategy:
  - Inherit res.company and override _get_sms_api_class() to return
    VerimorSmsApi instead of the default IAP-based SmsApi.
  - VerimorSmsApi subclasses SmsApiBase (the common ABC) and re-implements
    _send_sms_batch() to POST to Verimor's v2/send.json.
"""
import logging
import requests

from odoo import models
from odoo.addons.sms.tools.sms_api import SmsApiBase

_logger = logging.getLogger(__name__)

_VERIMOR_SMS_ENDPOINT = 'https://sms.verimor.com.tr/v2/send.json'


class VerimorSmsApi(SmsApiBase):
    """Verimor-specific SMS provider implementing the SmsApiBase interface."""

    # Map Verimor HTTP response codes to Odoo sms.sms `state` / failure_type tokens
    PROVIDER_TO_SMS_FAILURE_TYPE = SmsApiBase.PROVIDER_TO_SMS_FAILURE_TYPE | {
        'server_error': 'sms_server',
        'wrong_number_format': 'sms_number_format',
    }

    def _get_credentials(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'username': ICP.get_param('verimor.sms.username', ''),
            'password': ICP.get_param('verimor.sms.password', ''),
            'source_addr': ICP.get_param('verimor.sms.source_addr', ''),
        }

    def _send_sms_batch(self, messages, delivery_reports_url=False):
        """Send a batch of SMS messages via Verimor v2 API.

        :param list messages: list of dicts, each with:
            {
                'content': str,                         # message body
                'numbers': [{'uuid': str, 'number': str}, ...]
            }
        :param str delivery_reports_url: ignored (Verimor uses its own callback)
        :return list: list of dicts:
            [{'uuid': str, 'state': str, 'failure_reason': str|None}, ...]
        """
        creds = self._get_credentials()
        if not creds['username'] or not creds['password']:
            _logger.error(
                'verimor_connector: Verimor SMS credentials not configured. '
                'Set verimor.sms.username and verimor.sms.password in System Parameters.'
            )
            return [
                {'uuid': rec['uuid'], 'state': 'server_error', 'failure_reason': 'credentials_missing'}
                for msg in messages
                for rec in msg['numbers']
            ]

        results = []

        for message in messages:
            content = message.get('content', '')
            numbers = message.get('numbers', [])

            verimor_messages = [
                {
                    'msg': content,
                    'dest': rec['number'],
                    'id': rec['uuid'],           # Verimor echoes this back as campaign ID suffix
                }
                for rec in numbers
            ]

            payload = {
                'username': creds['username'],
                'password': creds['password'],
                'source_addr': creds['source_addr'],
                'is_commercial': True,           # IYS filtering done by Verimor on their side
                'iys_recipient_type': 'BIREYSEL',
                'messages': verimor_messages,
            }

            try:
                resp = requests.post(
                    _VERIMOR_SMS_ENDPOINT,
                    json=payload,
                    timeout=20,
                )
            except requests.RequestException as exc:
                _logger.exception(
                    'verimor_connector: Verimor SMS network error for batch of %d messages: %s',
                    len(numbers), exc,
                )
                results.extend([
                    {'uuid': rec['uuid'], 'state': 'server_error', 'failure_reason': str(exc)}
                    for rec in numbers
                ])
                continue

            if resp.status_code == 200:
                _logger.info(
                    'verimor_connector: SMS batch of %d messages sent successfully. '
                    'Verimor campaign: %s',
                    len(numbers), resp.text.strip(),
                )
                results.extend([
                    {'uuid': rec['uuid'], 'state': 'success'}
                    for rec in numbers
                ])
            else:
                error_text = resp.text.strip()
                _logger.error(
                    'verimor_connector: Verimor SMS API error HTTP %s: %s',
                    resp.status_code, error_text,
                )
                results.extend([
                    {
                        'uuid': rec['uuid'],
                        'state': 'server_error',
                        'failure_reason': error_text,
                    }
                    for rec in numbers
                ])

        return results

    def _get_sms_api_error_messages(self):
        error_dict = super()._get_sms_api_error_messages()
        error_dict.update({
            'server_error': 'An error occurred on the Verimor SMS gateway.',
            'wrong_number_format': 'The phone number is not in a valid format for Verimor.',
            'credentials_missing': 'Verimor SMS credentials are not configured.',
        })
        return error_dict


class ResCompany(models.Model):
    """Override company's SMS API class selector to use Verimor."""
    _inherit = 'res.company'

    def _get_sms_api_class(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        # Only intercept if Verimor credentials are configured; fall back to IAP otherwise
        if ICP.get_param('verimor.sms.username'):
            return VerimorSmsApi
        from odoo.addons.sms.tools.sms_api import SmsApi  # noqa: PLC0415
        return SmsApi
