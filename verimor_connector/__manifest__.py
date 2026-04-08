# -*- coding: utf-8 -*-
{
    'name': 'Verimor Connector',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'Verimor SMS, VoIP (Bulutsantralim) and IYS consent integration',
    'description': """
        Integrates Verimor's SMS gateway, Bulutsantralim PBX API and
        IYS (İleti Yönetim Sistemi) consent management into Odoo 18's
        native communication stack.

        Features:
        - Route all outgoing SMS through Verimor's v2 API with IYS filtering
        - Push IYS consent records (MESAJ / ARAMA / EPOSTA) upon partner save
        - Block commercial e-mails for partners with IYS e-mail rejection
        - Click-to-call from res.partner form view via Bulutsantralim API
        - Incoming call popup via Odoo bus (WebSocket)
        - Full call event log (verimor.call.log)
        - Two webhook endpoints: /verimor/call/event and /verimor/call/advisory
    """,
    'author': 'Eska',
    'website': 'https://www.eska.com.tr',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'sms',
        'bus',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/verimor_call_log_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
