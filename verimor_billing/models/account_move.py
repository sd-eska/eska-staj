# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _create_verimor_invoices(self):
        """
        Scheduled action entry point — creates draft invoices for all
        uninvoiced verimor.usage.line records grouped by partner.

        Called monthly by the ir.cron defined in data/ir_cron.xml.
        Override this method to add custom pricing logic, product mapping,
        or multi-company support.
        """
        UsageLine = self.env['verimor.usage.line']
        uninvoiced = UsageLine.search([('invoiced', '=', False)])

        if not uninvoiced:
            _logger.info('verimor_billing: no uninvoiced usage lines, skipping billing run.')
            return

        # Group by (partner, company)
        grouped = {}
        for line in uninvoiced:
            key = (line.partner_id.id, line.company_id.id)
            grouped.setdefault(key, self.env['verimor.usage.line'])
            grouped[key] |= line

        invoices_created = []
        for (partner_id, company_id), lines in grouped.items():
            partner = self.env['res.partner'].browse(partner_id)
            company = self.env['res.company'].browse(company_id)

            # Build invoice lines
            invoice_line_vals = []
            for line in lines:
                invoice_line_vals.append((0, 0, {
                    'name': line.description or f'Verimor {line.usage_type}',
                    'quantity': line.quantity,
                    'price_unit': line.unit_price,
                    # TODO: map to a proper product_id for accounting
                }))

            move = self.with_company(company).create({
                'move_type': 'out_invoice',
                'partner_id': partner_id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_line_vals,
                'narration': f'Verimor usage billing — {fields.Date.today()}',
            })
            invoices_created.append(move)

            # Mark lines as invoiced — link to the first invoice line for traceability
            for line, inv_line in zip(lines, move.invoice_line_ids):
                line.sudo().write({'invoice_line_id': inv_line.id})

            _logger.info(
                'verimor_billing: created invoice %s for partner %s (%d lines)',
                move.name, partner.name, len(lines),
            )

        return invoices_created
