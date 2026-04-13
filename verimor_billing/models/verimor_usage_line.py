# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VerimorUsageLine(models.Model):
    """
    Records each billable Verimor usage event (SMS send, VoIP call).

    One record per event. The monthly billing cron groups these lines
    by partner and creates a draft invoice (account.move).
    """
    _name = 'verimor.usage.line'
    _description = 'Verimor Usage Line'
    _order = 'event_date desc, id desc'
    _rec_name = 'usage_type'

    usage_type = fields.Selection(
        selection=[
            ('sms', 'SMS'),
            ('call', 'VoIP Call'),
        ],
        string='Usage Type',
        required=True,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='restrict',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    event_date = fields.Datetime(
        string='Event Date',
        required=True,
        default=fields.Datetime.now,
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        help='Number of SMS messages or call minutes.',
    )
    unit_price = fields.Float(
        string='Unit Price',
        digits=(16, 4),
        help='Price per unit in company currency.',
    )
    amount = fields.Float(
        string='Amount',
        compute='_compute_amount',
        store=True,
        digits=(16, 2),
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
    )
    invoice_line_id = fields.Many2one(
        'account.move.line',
        string='Invoice Line',
        readonly=True,
        ondelete='set null',
        help='Set when this usage line has been invoiced.',
    )
    invoiced = fields.Boolean(
        string='Invoiced',
        compute='_compute_invoiced',
        store=True,
        index=True,
    )
    reference = fields.Char(
        string='Reference',
        help='SMS UUID, VoIP call ID, or other identifier.',
    )
    description = fields.Char(string='Description')

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.unit_price

    @api.depends('invoice_line_id')
    def _compute_invoiced(self):
        for line in self:
            line.invoiced = bool(line.invoice_line_id)

    @api.model
    def _register_sms_usage(self, partner, quantity=1, reference=None, unit_price=0.0):
        """
        Register an SMS sending event.

        Call this from sms_verimor after a successful Verimor API response.

        :param partner: res.partner record (the customer/owner)
        :param quantity: number of SMS sent
        :param reference: SMS UUID or batch ID
        :param unit_price: price per SMS (0.0 until a pricing model is configured)
        """
        return self.create({
            'usage_type': 'sms',
            'partner_id': partner.id,
            'quantity': quantity,
            'unit_price': unit_price,
            'reference': reference or '',
            'description': f'SMS × {quantity}',
        })

    @api.model
    def _register_call_usage(self, partner, duration_seconds=0, reference=None, unit_price=0.0):
        """
        Register a VoIP call event.

        Call this from iys_pbx when a voip.call terminates.

        :param partner: res.partner record
        :param duration_seconds: call duration in seconds
        :param reference: voip.call ID
        :param unit_price: price per minute (0.0 until pricing configured)
        """
        minutes = round(duration_seconds / 60, 4)
        return self.create({
            'usage_type': 'call',
            'partner_id': partner.id,
            'quantity': minutes,
            'unit_price': unit_price,
            'reference': reference or '',
            'description': f'VoIP call – {duration_seconds}s',
        })
