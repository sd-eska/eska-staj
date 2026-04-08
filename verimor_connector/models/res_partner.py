# -*- coding: utf-8 -*-
import logging
import re
import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Regular expression to standardise Turkish mobile numbers to E.164 (905XXXXXXXXX)
_TR_MOBILE_RE = re.compile(
    r'^(?:\+?90|0)?'   # optional country/trunk code
    r'(5\d{9})$'       # must start with 5, total 10 digits after country code
)

# Verimor IYS consent endpoint
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

    # ── IYS consent fields ─────────────────────────────────────────────────────
    iys_sms_consent = fields.Selection(
        selection=[('ONAY', 'Approved'), ('RET', 'Rejected'), ('pending', 'Pending')],
        string='IYS SMS Consent (MESAJ)',
        default='pending',
        tracking=True,
        help='IYS consent status for commercial SMS messages.',
    )
    iys_call_consent = fields.Selection(
        selection=[('ONAY', 'Approved'), ('RET', 'Rejected'), ('pending', 'Pending')],
        string='IYS Call Consent (ARAMA)',
        default='pending',
        tracking=True,
        help='IYS consent status for commercial voice calls.',
    )
    iys_email_consent = fields.Selection(
        selection=[('ONAY', 'Approved'), ('RET', 'Rejected'), ('pending', 'Pending')],
        string='IYS Email Consent (EPOSTA)',
        default='pending',
        tracking=True,
        help='IYS consent status for commercial e-mails.',
    )
    iys_consent_date = fields.Datetime(
        string='IYS Consent Date',
        help='Timestamp of the last consent change recorded in IYS.',
    )
    iys_last_push_date = fields.Datetime(
        string='Last IYS Push',
        help='Timestamp of the last successful consent push to Verimor IYS endpoint.',
        readonly=True,
    )

    # ── Normalised mobile phone ────────────────────────────────────────────────
    verimor_mobile = fields.Char(
        string='Verimor Mobile (E.164)',
        compute='_compute_verimor_mobile',
        store=True,
        help='Phone number normalised to Verimor E.164 format (905XXXXXXXXX).',
    )

    @api.depends('mobile', 'phone')
    def _compute_verimor_mobile(self):
        for partner in self:
            partner.verimor_mobile = (
                _normalize_phone(partner.mobile)
                or _normalize_phone(partner.phone)
            )

    # ── IYS push on save ───────────────────────────────────────────────────────
    def write(self, vals):
        res = super().write(vals)
        iys_fields = {'iys_sms_consent', 'iys_call_consent', 'iys_email_consent', 'iys_consent_date'}
        if iys_fields & set(vals.keys()):
            # Push consent changes after commit to avoid blocking the save
            self._push_iys_consents()
        return res

    def _push_iys_consents(self):
        """Push current IYS consent records to Verimor.

        Verimor accepts up to a 3-business-day legal window; we push immediately
        upon save so that the deadline is never missed.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        username = ICP.get_param('verimor.sms.username')
        password = ICP.get_param('verimor.sms.password')
        source_addr = ICP.get_param('verimor.sms.source_addr')

        if not (username and password and source_addr):
            _logger.warning(
                'verimor_connector: IYS push skipped – Verimor SMS credentials not configured.'
            )
            return

        for partner in self:
            consents = partner._build_iys_consents()
            if not consents:
                continue

            payload = {
                'username': username,
                'password': password,
                'source_addr': source_addr,
                'consents': consents,
            }
            try:
                resp = requests.post(
                    _IYS_ENDPOINT,
                    json=payload,
                    timeout=15,
                )
                if resp.status_code == 200:
                    partner.sudo().write({'iys_last_push_date': fields.Datetime.now()})
                    _logger.info(
                        'verimor_connector: IYS consent pushed for partner %s (id=%s)',
                        partner.name, partner.id,
                    )
                else:
                    _logger.error(
                        'verimor_connector: IYS push failed for partner %s – HTTP %s: %s',
                        partner.name, resp.status_code, resp.text,
                    )
            except requests.RequestException as exc:
                _logger.exception(
                    'verimor_connector: IYS push network error for partner %s: %s',
                    partner.name, exc,
                )

    def _build_iys_consents(self):
        """Return a list of consent dict entries for this partner."""
        self.ensure_one()
        consents = []
        consent_date = (
            fields.Datetime.to_string(self.iys_consent_date)
            if self.iys_consent_date
            else fields.Datetime.to_string(fields.Datetime.now())
        )

        # MESAJ – requires normalised mobile
        mobile = self.verimor_mobile
        if mobile and self.iys_sms_consent in ('ONAY', 'RET'):
            consents.append({
                'type': 'MESAJ',
                'source': 'HS_WEB',
                'status': self.iys_sms_consent,
                'recipient_type': 'BIREYSEL',
                'consent_date': consent_date,
                'recipient': mobile,
            })

        # ARAMA – requires normalised mobile
        if mobile and self.iys_call_consent in ('ONAY', 'RET'):
            consents.append({
                'type': 'ARAMA',
                'source': 'HS_WEB',
                'status': self.iys_call_consent,
                'recipient_type': 'BIREYSEL',
                'consent_date': consent_date,
                'recipient': mobile,
            })

        # EPOSTA – requires e-mail address
        if self.email and self.iys_email_consent in ('ONAY', 'RET'):
            consents.append({
                'type': 'EPOSTA',
                'source': 'HS_WEB',
                'status': self.iys_email_consent,
                'recipient_type': 'BIREYSEL',
                'consent_date': consent_date,
                'recipient': self.email,
            })

        return consents

    # ── Click-to-call button ───────────────────────────────────────────────────
    def action_verimor_click_to_call(self):
        """Initiate a Bulutsantralim click-to-call from this partner's number."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('verimor.pbx.api_key')
        extension = ICP.get_param('verimor.pbx.extension')

        if not api_key:
            raise UserError(self.env._('Bulutsantralim API key is not configured in Settings → Verimor.'))

        destination = _normalize_phone(self.mobile or self.phone or '')
        if not destination:
            raise UserError(
                self.env._('No valid Turkish mobile number found on partner %s.') % (self.name,)
            )

        if self.iys_call_consent == 'RET':
            raise UserError(
                self.env._('Partner %s has rejected IYS call consent (ARAMA). Outgoing call blocked.')
                % (self.name,)
            )

        url = 'https://pbx.verimor.com.tr/v2/call.json'
        payload = {
            'api_key': api_key,
            'source_addr': extension or '',
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
                        'message': self.env._('Call to %s is being connected.') % (self.name,),
                        'type': 'success',
                        'sticky': False,
                    },
                }
            else:
                raise UserError(
                    self.env._('Bulutsantralim call failed (HTTP %(code)s): %(text)s') % {'code': resp.status_code, 'text': resp.text}
                )
        except requests.RequestException as exc:
            raise UserError(self.env._('Bulutsantralim API error: %s') % (str(exc),)) from exc
