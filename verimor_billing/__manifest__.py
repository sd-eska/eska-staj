# -*- coding: utf-8 -*-
{
    'name': 'Verimor Billing',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Billing',
    'summary': 'Post-paid billing for Verimor SMS and VoIP usage',
    'description': """
        Tracks Verimor SMS sends and VoIP calls per company/partner,
        and generates draft invoices (account.move) at the end of each
        billing cycle via a scheduled action (cron job).

        Usage flows tracked:
        - SMS sent via sms_verimor
        - VoIP calls via iys_pbx / voip

        Billing model:
        - One verimor.usage.line per transaction
        - Monthly cron groups lines by partner → creates account.move
    """,
    'author': 'Eska',
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
