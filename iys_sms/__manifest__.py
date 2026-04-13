# -*- coding: utf-8 -*-
{
    'name': 'IYS SMS',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'IYS MESAJ consent blocking for outgoing SMS',
    'author': 'Eska',
    'website': 'https://www.eska.com.tr',
    'license': 'LGPL-3',
    'depends': [
        'iys',
        'sms_verimor',
    ],
    'data': [
        'views/iap_account_views.xml',
        'views/res_partner_views.xml',
    ],
}
