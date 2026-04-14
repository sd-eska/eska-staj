# -*- coding: utf-8 -*-
{
    'name': 'SMS Verimor',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'Verimor SMS Gateway — pure SMS sending integration',
    'description': """
        Integrates the Verimor v2/send.json API as an Odoo SMS provider.
        No IYS logic here — this module only handles the transport layer.
        IYS consent blocking is handled by the iys_sms module.
    """,
    'author': 'ESKA',
    'website': 'https://www.eska.com.tr',
    'license': 'LGPL-3',
    'depends': [
        'sms',
        'iap',
    ],
    'data': [
        'views/iap_account_views.xml',
    ],
}
