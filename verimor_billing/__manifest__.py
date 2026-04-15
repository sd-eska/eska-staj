# -*- coding: utf-8 -*-
{
    'name': 'Verimor Billing',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Billing',
    'summary': 'Post-paid billing for Verimor SMS and VoIP usage',
    'author': 'Eska, Odoo Community Association (OCA)',
    'website': 'https://www.eska.com.tr',
    'license': 'LGPL-3',
    'depends': [
        'iys',
        'sms_verimor',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/verimor_usage_line_views.xml',
    ],
}
