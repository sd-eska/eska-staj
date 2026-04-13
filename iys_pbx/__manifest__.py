# -*- coding: utf-8 -*-
{
    'name': 'IYS PBX',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'IYS ARAMA consent integration with Odoo VoIP',
    'author': 'Eska',
    'website': 'https://www.eska.com.tr',
    'license': 'LGPL-3',
    'depends': [
        'iys',
        'voip',
    ],
    'data': [
        'views/iap_account_views.xml',
        'views/res_partner_views.xml',
    ],
}
