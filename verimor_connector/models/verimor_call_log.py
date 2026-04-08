# -*- coding: utf-8 -*-
"""verimor.call.log – stores all Bulutsantralim PBX call events."""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VerimorCallLog(models.Model):
    _name = 'verimor.call.log'
    _description = 'Verimor Call Log'
    _order = 'call_time desc, id desc'
    _rec_name = 'caller_number'

    # ── Call identification ────────────────────────────────────────────────────
    call_uuid = fields.Char(
        string='Call UUID',
        index=True,
        copy=False,
        help='Unique identifier provided by Bulutsantralim for this call leg.',
    )
    caller_number = fields.Char(
        string='Caller Number',
        index=True,
        help='The phone number of the calling party (E.164 format).',
    )
    called_number = fields.Char(
        string='Called Number',
        help='The DID / extension that was dialled.',
    )

    # ── Matched partner ────────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        ondelete='set null',
        help='Matched res.partner record (looked up by caller_number).',
    )

    # ── Event data ─────────────────────────────────────────────────────────────
    event_type = fields.Selection(
        selection=[
            ('INCOMING', 'Incoming'),
            ('OUTGOING', 'Outgoing'),
            ('ANSWERED', 'Answered'),
            ('HANGUP', 'Hung Up'),
            ('MISSED', 'Missed'),
            ('VOICEMAIL', 'Voicemail'),
        ],
        string='Event Type',
        required=True,
        default='INCOMING',
    )
    call_time = fields.Datetime(
        string='Call Time',
        required=True,
        default=fields.Datetime.now,
    )
    duration = fields.Integer(
        string='Duration (s)',
        default=0,
        help='Call duration in seconds (populated on HANGUP events).',
    )
    hangup_cause = fields.Char(
        string='Hangup Cause',
        help='SIP hangup cause code / reason returned by Bulutsantralim.',
    )

    # ── Raw webhook payload ────────────────────────────────────────────────────
    raw_payload = fields.Text(
        string='Raw Payload',
        readonly=True,
        help='Full JSON body received from the Bulutsantralim webhook.',
    )

    # ── IYS advisory result ───────────────────────────────────────────────────
    iys_call_consent = fields.Selection(
        related='partner_id.iys_call_consent',
        string='IYS Call Consent',
        readonly=True,
        store=False,
    )

    @api.model
    def _match_partner(self, phone_number):
        """Return the first res.partner whose mobile or phone matches `phone_number`."""
        if not phone_number:
            return self.env['res.partner']
        # Search normalised verimor_mobile first (stored computed field)
        partner = self.env['res.partner'].search(
            [('verimor_mobile', '=', phone_number)], limit=1
        )
        if not partner:
            # Fallback: raw phone/mobile field search
            partner = self.env['res.partner'].search(
                ['|', ('mobile', 'like', phone_number[-9:]),
                      ('phone', 'like', phone_number[-9:])],
                limit=1,
            )
        return partner
