# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IysCallLog(models.Model):
    _name = 'iys.call.log'
    _description = 'IYS Call Log'
    _order = 'call_time desc, id desc'
    _rec_name = 'caller_number'

    call_uuid = fields.Char(string='Call UUID', index=True, copy=False)
    caller_number = fields.Char(index=True)
    called_number = fields.Char()
    partner_id = fields.Many2one('res.partner', ondelete='set null')
    event_type = fields.Selection(
        selection=[
            ('INCOMING', 'Incoming'), ('OUTGOING', 'Outgoing'),
            ('ANSWERED', 'Answered'), ('HANGUP', 'Hung Up'),
            ('MISSED', 'Missed'), ('VOICEMAIL', 'Voicemail'),
        ],
        required=True, default='INCOMING',
    )
    call_time = fields.Datetime(required=True, default=fields.Datetime.now)
    duration = fields.Integer(string='Duration (s)', default=0)
    hangup_cause = fields.Char()
    raw_payload = fields.Text(readonly=True)

    iys_call_consent = fields.Char(
        string='IYS Call Consent',
        compute='_compute_iys_call_consent',
        store=False,
    )

    @api.depends('partner_id', 'caller_number')
    def _compute_iys_call_consent(self):
        Consent = self.env['iys.consent']
        for log in self:
            recipient = None
            if log.partner_id and log.partner_id.verimor_mobile:
                recipient = log.partner_id.verimor_mobile
            elif log.caller_number:
                recipient = log.caller_number
            if recipient:
                log.iys_call_consent = Consent._lookup(recipient, 'ARAMA')
            else:
                log.iys_call_consent = 'pending'

    @api.model
    def _match_partner(self, phone_number):
        """Find the best-matching res.partner for a given phone number."""
        if not phone_number:
            return self.env['res.partner']

        partner = self.env['res.partner'].search(
            [('verimor_mobile', '=', phone_number)], limit=1
        )
        if not partner:
            partner = self.env['res.partner'].search(
                ['|',
                 ('mobile', 'like', phone_number[-9:]),
                 ('phone', 'like', phone_number[-9:])],
                limit=1,
            )
        return partner
