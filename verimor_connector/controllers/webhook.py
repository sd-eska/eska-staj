# -*- coding: utf-8 -*-
"""Webhook controllers for Verimor Bulutsantralim PBX integration.

Routes:
  POST /verimor/call/event
    - Receives call-state events from Bulutsantralim
    - Logs them to verimor.call.log
    - Matches caller to res.partner by phone number
    - Pushes a bus notification to all internal users (incoming call popup)

  GET /verimor/call/advisory
    - Bulutsantralim calls this before routing an incoming call
    - Looks up the caller in res.partner
    - Checks iys_call_consent
    - Returns a JSON routing decision

Both endpoints:
  - csrf=False  (webhook payloads do not carry Odoo CSRF tokens)
  - auth='public' (called by Bulutsantralim servers, not logged-in users)
"""
import json
import logging

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class VerimorWebhookController(http.Controller):

    # ── POST /verimor/call/event ───────────────────────────────────────────────

    @http.route(
        '/verimor/call/event',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def call_event(self, **kwargs):
        """Process a Bulutsantralim call event webhook.

        Expected JSON body (example):
        {
            "uuid": "abc123",
            "event": "INCOMING",           # INCOMING | ANSWERED | HANGUP | MISSED | ...
            "caller": "905301234567",
            "callee": "908501234567",
            "duration": 0,
            "hangup_cause": null
        }
        """
        try:
            payload = json.loads(request.httprequest.data) if request.httprequest.data else {}
        except (ValueError, TypeError):
            payload = kwargs  # already parsed by Odoo's JSON dispatcher

        call_uuid = payload.get('uuid') or payload.get('call_uuid', '')
        event_type_raw = (payload.get('event') or payload.get('event_type', 'INCOMING')).upper()
        caller = payload.get('caller') or payload.get('caller_number', '')
        callee = payload.get('callee') or payload.get('called_number', '')
        duration = int(payload.get('duration') or 0)
        hangup_cause = payload.get('hangup_cause') or ''

        # Normalise event_type to our selection values
        _EVENT_MAP = {
            'INCOMING': 'INCOMING',
            'OUTGOING': 'OUTGOING',
            'ANSWERED': 'ANSWERED',
            'HANGUP': 'HANGUP',
            'HUNG_UP': 'HANGUP',
            'MISSED': 'MISSED',
            'VOICEMAIL': 'VOICEMAIL',
        }
        event_type = _EVENT_MAP.get(event_type_raw, 'INCOMING')

        CallLog = request.env['verimor.call.log'].sudo()
        partner = CallLog._match_partner(caller)

        log = CallLog.create({
            'call_uuid': call_uuid,
            'caller_number': caller,
            'called_number': callee,
            'event_type': event_type,
            'call_time': fields.Datetime.now(),
            'duration': duration,
            'hangup_cause': hangup_cause,
            'partner_id': partner.id or False,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        })
        _logger.info(
            'verimor_connector: call event logged (id=%s, uuid=%s, event=%s, caller=%s)',
            log.id, call_uuid, event_type, caller,
        )

        # Push bus notification for incoming calls so the UI can show a popup
        if event_type == 'INCOMING':
            notification_payload = {
                'call_log_id': log.id,
                'call_uuid': call_uuid,
                'caller': caller,
                'callee': callee,
                'partner_id': partner.id or False,
                'partner_name': partner.name or caller,
                'iys_call_consent': partner.iys_call_consent if partner else 'pending',
            }
            # Send to every internal user so any agent can pop up the call dialog
            internal_users = request.env['res.users'].sudo().search(
                [('share', '=', False), ('active', '=', True)]
            )
            for user in internal_users:
                request.env['bus.bus'].sudo()._sendone(
                    user.partner_id,
                    'verimor_connector.incoming_call',
                    notification_payload,
                )

        return {'status': 'ok', 'log_id': log.id}

    # ── GET /verimor/call/advisory ─────────────────────────────────────────────

    @http.route(
        '/verimor/call/advisory',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
    )
    def call_advisory(self, caller=None, callee=None, **kwargs):
        """Respond to Bulutsantralim's pre-routing advisory request.

        Bulutsantralim sends a GET with query params:
          ?caller=905XXXXXXXXX&callee=908XXXXXXXXX

        We return a JSON routing decision:
        {
            "action": "ALLOW" | "REJECT" | "VOICEMAIL",
            "reason": "...",
            "partner_id": int | null,
            "partner_name": str | null,
            "iys_call_consent": "ONAY" | "RET" | "pending" | null
        }
        """
        CallLog = request.env['verimor.call.log'].sudo()
        partner = CallLog._match_partner(caller or '')

        iys_consent = partner.iys_call_consent if partner else None

        if iys_consent == 'RET':
            action = 'REJECT'
            reason = 'IYS ARAMA consent is RET – call rejected per legal requirement.'
        else:
            action = 'ALLOW'
            reason = 'Call allowed.'

        response_data = {
            'action': action,
            'reason': reason,
            'partner_id': partner.id if partner else None,
            'partner_name': partner.name if partner else None,
            'iys_call_consent': iys_consent,
        }

        _logger.info(
            'verimor_connector: advisory for caller=%s → action=%s partner=%s',
            caller, action, partner.name if partner else 'unknown',
        )

        return request.make_response(
            json.dumps(response_data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json')],
        )
