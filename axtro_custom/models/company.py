from odoo import api, fields, models, _


class JmdResCompany(models.Model):
    _inherit = 'res.company'
    _name = 'res.company'

    jmd_footer_logo = fields.Binary(string='Footer logo')
    jmd_header_logo = fields.Binary(string='Header logo')