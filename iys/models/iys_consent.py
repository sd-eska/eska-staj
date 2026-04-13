# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

CONSENT_TYPES = ['MESAJ', 'ARAMA', 'EPOSTA']


class IysConsent(models.Model):
    """
    Central IYS consent store – works like mail.blacklist / phone.blacklist.

    One record per (recipient, consent_type) pair:
      - status='RET'  + active=False  → blacklisted (blocked)
      - status='ONAY' + active=True   → explicitly allowed
      - no record                     → pending (unknown)
    """
    _name = 'iys.consent'
    _description = 'IYS Consent'
    _order = 'write_date desc, id desc'
    _rec_name = 'recipient'

    recipient = fields.Char(
        string='Recipient',
        required=True,
        index=True,
        help='E.164 phone number (905XXXXXXXXX) or e-mail address',
    )
    consent_type = fields.Selection(
        selection=[
            ('MESAJ', 'SMS (MESAJ)'),
            ('ARAMA', 'Voice Call (ARAMA)'),
            ('EPOSTA', 'E-Mail (EPOSTA)'),
        ],
        string='Consent Type',
        required=True,
        index=True,
    )
    status = fields.Selection(
        selection=[
            ('ONAY', 'Approved'),
            ('RET', 'Rejected'),
        ],
        string='Status',
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help='False means the recipient is blacklisted for this consent type.',
    )
    source = fields.Char(
        string='Source',
        default='HS_WEB',
        help='IYS source code (HS_WEB, HS_CAGRI_MERKEZI, etc.)',
    )
    recipient_type = fields.Selection(
        selection=[('BIREYSEL', 'Individual'), ('TACIR', 'Merchant')],
        string='Recipient Type',
        default='BIREYSEL',
    )
    consent_date = fields.Datetime(string='Consent Date', default=fields.Datetime.now)

    _sql_constraints = [
        (
            'unique_recipient_type',
            'UNIQUE(recipient, consent_type)',
            'A consent record already exists for this recipient and consent type.',
        ),
    ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @api.model
    def _add(self, recipient, consent_type, status, source='HS_WEB',
             recipient_type='BIREYSEL', consent_date=None):
        """
        Add or update a consent record.

        :param recipient: E.164 phone or e-mail
        :param consent_type: 'MESAJ' | 'ARAMA' | 'EPOSTA'
        :param status: 'ONAY' | 'RET'
        :param source: IYS source code
        :param recipient_type: 'BIREYSEL' | 'TACIR'
        :param consent_date: datetime or None (defaults to now)
        :return: iys.consent record
        """
        if consent_type not in CONSENT_TYPES:
            raise ValidationError(
                f"Invalid consent_type '{consent_type}'. Must be one of {CONSENT_TYPES}."
            )
        if status not in ('ONAY', 'RET'):
            raise ValidationError(
                f"Invalid status '{status}'. Must be 'ONAY' or 'RET'."
            )

        recipient = (recipient or '').strip().lower() if '@' in (recipient or '') else (recipient or '').strip()

        existing = self.search([
            ('recipient', '=', recipient),
            ('consent_type', '=', consent_type),
        ], limit=1)

        vals = {
            'status': status,
            'active': status == 'ONAY',
            'source': source,
            'recipient_type': recipient_type,
            'consent_date': consent_date or fields.Datetime.now(),
        }

        if existing:
            existing.sudo().write(vals)
            return existing
        else:
            vals.update({
                'recipient': recipient,
                'consent_type': consent_type,
            })
            return self.sudo().create(vals)

    @api.model
    def _remove(self, recipient, consent_type):
        """
        Remove (archive) a consent record – effectively sets it back to pending.

        :param recipient: E.164 phone or e-mail
        :param consent_type: 'MESAJ' | 'ARAMA' | 'EPOSTA'
        """
        recipient = (recipient or '').strip().lower() if '@' in (recipient or '') else (recipient or '').strip()
        record = self.search([
            ('recipient', '=', recipient),
            ('consent_type', '=', consent_type),
        ], limit=1)
        if record:
            record.sudo().unlink()

    @api.model
    def _lookup(self, recipient, consent_type):
        """
        Return the consent status for a given recipient and type.

        :return: 'ONAY' | 'RET' | 'pending'
        """
        recipient = (recipient or '').strip().lower() if '@' in (recipient or '') else (recipient or '').strip()
        record = self.with_context(active_test=False).search([
            ('recipient', '=', recipient),
            ('consent_type', '=', consent_type),
        ], limit=1)
        if not record:
            return 'pending'
        return record.status

    @api.model
    def _is_blocked(self, recipient, consent_type):
        """Return True if the recipient has explicitly rejected this consent type."""
        return self._lookup(recipient, consent_type) == 'RET'
