from odoo import _
def test():
    raise Exception(_("Hello %s") % 'World')
    raise Exception(_("Hello %(name)s and %(last)s") % {'name': 'John', 'last': 'Doe'})
