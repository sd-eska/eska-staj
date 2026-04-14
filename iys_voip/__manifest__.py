# -*- coding: utf-8 -*-
{
    'name': 'IYS VoIP',
    'version': '17.0.1.0.0',
    'category': 'Technical',
    'summary': 'IYS ARAMA consent blocking for Odoo VoIP',
    'description': """
        A bridge module that adds IYS ARAMA consent checks to the native
        Odoo Enterprise VoIP softphone. It blocks outgoing calls if the
        destination has rejected voice calling consents in IYS.
    """,
    'author': 'ESKA',
    'website': 'https://www.eska.com.tr',
    'license': 'LGPL-3',
    'depends': [
        'iys',
        'voip',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
    ],
}
