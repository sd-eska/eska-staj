# -*- coding: utf-8 -*-
import json
import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

_EVENT_MAP = {
    'INCOMING': 'INCOMING',
    'OUTGOING': 'OUTGOING',
    'ANSWERED': 'ANSWERED',
    'HANGUP': 'HANGUP',
    'HUNG_UP': 'HANGUP',
    'MISSED': 'MISSED',
    'VOICEMAIL': 'VOICEMAIL',
}


class IysPbxWebhookController(http.Controller):

    @http.route('/iys/call/event', type='json', auth='public', methods=['POST'], csrf=False)
    def call_event(self, **kwargs):
        """
        Receive call lifecycle events from Bulutsantralim and log them as iys.call.log records.
        Broadcasts bus notification to internal users for incoming calls.
        """
        try:
            payload = json.loads(request.httprequest.data) if request.httprequest.data else {}
        except (ValueError, TypeError):
            payload = kwargs

        call_uuid = payload.get('uuid') or payload.get('call_uuid', '')
        event_type_raw = (payload.get('event') or payload.get('event_type', 'INCOMING')).upper()
        caller = payload.get('caller') or payload.get('caller_number', '')
        callee = payload.get('callee') or payload.get('called_number', '')
        duration = int(payload.get('duration') or 0)
        hangup_cause = payload.get('hangup_cause') or ''

        event_type = _EVENT_MAP.get(event_type_raw, 'INCOMING')

        CallLog = request.env['iys.call.log'].sudo()
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

        if event_type == 'INCOMING':
            Consent = request.env['iys.consent'].sudo()
            iys_consent = 'pending'
            if partner and partner.verimor_mobile:
                iys_consent = Consent._lookup(partner.verimor_mobile, 'ARAMA')

            notification_payload = {
                'call_log_id': log.id,
                'call_uuid': call_uuid,
                'caller': caller,
                'callee': callee,
                'partner_id': partner.id or False,
                'partner_name': partner.name or caller,
                'iys_call_consent': iys_consent,
            }
            internal_users = request.env['res.users'].sudo().search(
                [('share', '=', False), ('active', '=', True)]
            )
            for user in internal_users:
                request.env['bus.bus'].sudo()._sendone(
                    user.partner_id,
                    'iys_pbx.incoming_call',
                    notification_payload,
                )

        return {'status': 'ok', 'log_id': log.id}

    @http.route('/iys/call/advisory', type='http', auth='public', methods=['GET'], csrf=False)
    def call_advisory(self, caller=None, callee=None, **kwargs):
        """
        Advisory endpoint: allow or reject an incoming call based on IYS ARAMA consent.
        Returns JSON: { action: 'ALLOW'|'REJECT', reason: str, ... }
        """
        CallLog = request.env['iys.call.log'].sudo()
        partner = CallLog._match_partner(caller or '')

        Consent = request.env['iys.consent'].sudo()
        iys_consent = 'pending'
        if partner and partner.verimor_mobile:
            iys_consent = Consent._lookup(partner.verimor_mobile, 'ARAMA')
        elif caller:
            iys_consent = Consent._lookup(caller, 'ARAMA')

        if iys_consent == 'RET':
            action, reason = 'REJECT', 'IYS ARAMA consent is RET – call rejected.'
        else:
            action, reason = 'ALLOW', 'Call allowed.'

        response_data = {
            'action': action,
            'reason': reason,
            'partner_id': partner.id if partner else None,
            'partner_name': partner.name if partner else None,
            'iys_call_consent': iys_consent,
        }
        return request.make_response(
            json.dumps(response_data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json')],
        )
