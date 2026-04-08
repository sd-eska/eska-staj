# -*- coding: utf-8 -*-
{
    'name': 'Verimor Connector',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'Verimor SMS, VoIP (Bulutsantralim) and IYS consent integration',
    'author': 'Odoo Community Association (OCA), Eska',
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
}
