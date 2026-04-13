# -*- coding: utf-8 -*-
{
    'name': 'IYS PBX',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'Bulutsantralim PBX integration with IYS call consent',
    'author': 'Eska',
    'website': 'https://www.eska.com.tr',
    'license': 'LGPL-3',
    'depends': [
        'iys',
        'bus',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/iap_account_views.xml',
        'views/iys_call_log_views.xml',
        'views/res_partner_views.xml',
    ],
}
