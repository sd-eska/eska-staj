# -*- coding: utf-8 -*-
import logging
import re
import requests
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_TR_MOBILE_RE = re.compile(
    r'^(?:\+?90|0)?'
    r'(5\d{9})$'
)

_IYS_ENDPOINT = 'https://sms.verimor.com.tr/v2/iys_consents.json'


def _normalize_phone(phone):
    """Return a Verimor-compatible E.164 number (905XXXXXXXXX) or None."""
    if not phone:
        return None
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    m = _TR_MOBILE_RE.match(phone)
    if m:
        return '90' + m.group(1)
    return None


class ResPartner(models.Model):
    _inherit = 'res.partner'

    iys_sms_consent = fields.Selection(
        selection=[('ONAY', 'Approved'), ('RET', 'Rejected'), ('pending', 'Pending')],
        string='IYS SMS Consent (MESAJ)',
        default='pending',
        tracking=True,
    )
    iys_call_consent = fields.Selection(
        selection=[('ONAY', 'Approved'), ('RET', 'Rejected'), ('pending', 'Pending')],
        string='IYS Call Consent (ARAMA)',
        default='pending',
        tracking=True,
    )
    iys_email_consent = fields.Selection(
        selection=[('ONAY', 'Approved'), ('RET', 'Rejected'), ('pending', 'Pending')],
        string='IYS Email Consent (EPOSTA)',
        default='pending',
        tracking=True,
    )
    iys_consent_date = fields.Datetime(string='IYS Consent Date')
    iys_last_push_date = fields.Datetime(string='Last IYS Push', readonly=True)

    verimor_mobile = fields.Char(
        string='Verimor Mobile (E.164)',
        compute='_compute_verimor_mobile',
        store=True,
    )

    @api.depends('mobile', 'phone')
    def _compute_verimor_mobile(self):
        for partner in self:
            partner.verimor_mobile = (
                _normalize_phone(partner.mobile)
                or _normalize_phone(partner.phone)
            )

    def write(self, vals):
        res = super().write(vals)
        iys_fields = {'iys_sms_consent', 'iys_call_consent', 'iys_email_consent', 'iys_consent_date'}
        if iys_fields & set(vals.keys()):
            self._sync_iys_consent_records()
            self._push_iys_consents()
        return res

    def _sync_iys_consent_records(self):
        """Sync partner IYS field values into the iys.consent store."""
        Consent = self.env['iys.consent']
        for partner in self:
            mobile = partner.verimor_mobile
            email = partner.email

            consent_map = [
                (mobile, 'MESAJ', partner.iys_sms_consent),
                (mobile, 'ARAMA', partner.iys_call_consent),
                (email, 'EPOSTA', partner.iys_email_consent),
            ]
            for recipient, c_type, status in consent_map:
                if not recipient:
                    continue
                if status in ('ONAY', 'RET'):
                    Consent._add(
                        recipient=recipient,
                        consent_type=c_type,
                        status=status,
                        consent_date=partner.iys_consent_date or fields.Datetime.now(),
                    )
                elif status == 'pending':
                    Consent._remove(recipient, c_type)

    def _push_iys_consents(self):
        """Push consent updates to the Verimor IYS API."""
        account = self.env['iap.account'].search(
            [('provider', '=', 'iys_verimor')], limit=1
        )
        if not account or not account.iys_username or not account.iys_password:
            _logger.warning('iys: IYS push skipped – iap.account credentials not configured.')
            return

        for partner in self:
            consents = partner._build_iys_consents()
            if not consents:
                continue
            payload = {
                'username': account.iys_username,
                'password': account.iys_password,
                'source_addr': account.iys_source_addr or '',
                'consents': consents,
            }
            try:
                resp = requests.post(_IYS_ENDPOINT, json=payload, timeout=15)
                if resp.status_code == 200:
                    partner.sudo().write({'iys_last_push_date': fields.Datetime.now()})
                else:
                    _logger.error(
                        'iys: IYS push failed – HTTP %s: %s',
                        resp.status_code, resp.text,
                    )
            except requests.RequestException as exc:
                _logger.exception('iys: IYS push network error: %s', exc)

    def _build_iys_consents(self):
        """Build the consents list payload for the Verimor IYS API."""
        self.ensure_one()
        consents = []
        consent_date = (
            fields.Datetime.to_string(self.iys_consent_date)
            if self.iys_consent_date
            else fields.Datetime.to_string(fields.Datetime.now())
        )
        mobile = self.verimor_mobile

        if mobile and self.iys_sms_consent in ('ONAY', 'RET'):
            consents.append({
                'type': 'MESAJ', 'source': 'HS_WEB', 'status': self.iys_sms_consent,
                'recipient_type': 'BIREYSEL', 'consent_date': consent_date, 'recipient': mobile,
            })
        if mobile and self.iys_call_consent in ('ONAY', 'RET'):
            consents.append({
                'type': 'ARAMA', 'source': 'HS_WEB', 'status': self.iys_call_consent,
                'recipient_type': 'BIREYSEL', 'consent_date': consent_date, 'recipient': mobile,
            })
        if self.email and self.iys_email_consent in ('ONAY', 'RET'):
            consents.append({
                'type': 'EPOSTA', 'source': 'HS_WEB', 'status': self.iys_email_consent,
                'recipient_type': 'BIREYSEL', 'consent_date': consent_date, 'recipient': self.email,
            })
        return consents
