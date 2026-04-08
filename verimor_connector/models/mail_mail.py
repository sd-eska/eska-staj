# -*- coding: utf-8 -*-
"""Override mail.mail._send() to block commercial e-mails for IYS-rejected partners.

Rules:
  - A Boolean field `is_commercial` on mail.mail distinguishes commercial vs.
    transactional mail (invoices, order confirmations, etc.).
  - If is_commercial is True AND a recipient partner has iys_email_consent == 'RET',
    that partner is removed from the recipients before sending.
  - If ALL recipients are blocked (or there are no recipients remaining), the mail
    is cancelled rather than sent.
  - Non-commercial mails (is_commercial=False or not set) are never touched.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = 'mail.mail'

    is_commercial = fields.Boolean(
        string='Commercial Message',
        default=False,
        help=(
            'Mark as True for marketing / commercial e-mails that require IYS consent. '
            'Transactional messages (invoices, order confirmations, etc.) should NOT '
            'be marked as commercial so they are never blocked by IYS filtering.'
        ),
    )

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None, alias_domain_id=False):
        """Intercept commercial e-mail sending to enforce IYS e-mail consent."""
        for mail in self:
            if not mail.is_commercial:
                # Non-commercial: pass straight through without any IYS check
                continue

            blocked_partners = mail.recipient_ids.filtered(
                lambda p: p.iys_email_consent == 'RET'
            )
            if not blocked_partners:
                continue

            allowed_partners = mail.recipient_ids - blocked_partners

            _logger.info(
                'verimor_connector: IYS e-mail blocking – mail %s: '
                'blocked %d recipient(s) [%s], %d allowed.',
                mail.id,
                len(blocked_partners),
                ', '.join(blocked_partners.mapped('name')),
                len(allowed_partners),
            )

            if not allowed_partners and not mail.email_to:
                # Every individual recipient has rejected; cancel the mail
                mail.write({
                    'state': 'cancel',
                    'failure_reason': self.env._(
                        'All recipients have rejected IYS e-mail consent (EPOSTA RET). '
                        'Commercial e-mail blocked.'
                    ),
                })
                # Skip super()._send() for this mail record – it is cancelled
                continue

            # Remove only the rejecting partners; let the rest through
            mail.write({'recipient_ids': [(3, p.id) for p in blocked_partners]})

        # Now delegate to the original _send() for all mails still in 'outgoing' state
        remaining = self.filtered(lambda m: m.state == 'outgoing')
        if remaining:
            return super(MailMail, remaining)._send(
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                smtp_session=smtp_session,
                alias_domain_id=alias_domain_id,
            )
        return True
