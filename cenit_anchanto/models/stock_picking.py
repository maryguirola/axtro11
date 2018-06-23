# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import Warning


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_customer_pickup = fields.Boolean(string='Is Customer Pickup?')
    
    carrier = fields.Selection([
        ('dhlpps', 'DHLPPS'),
        ('dhlps', 'DHLPS'),
        ('dtdc', 'DTDC'),
        ('express_post_signature', 'EXPRESS POST + SIGNATURE'),
        ('fba', 'FBA'),
        ('fbadhl', 'FBADHL'),
        ('ffgt', 'FFGT'),
        ('m12', 'M12'),
        ('mrt', 'MRT'),
        ('niktets', 'NIKTEST'),
        ('nr', 'NR'),
        ('parcel_post_signature', 'PARCEL POST + SIGNATURE'),
        ('registered_post_intl', 'REGISTERED POST INTL 8'),
        ('express_post_signature', 'EXPRESS POST SIGNATURE'),
        ('sc', 'SC'),
        ('sms', 'SMS'),
        ('sp', 'SP'),
        ('sppostage', 'SPPOSTAGE'),
        ('start_track_express', 'STARTRACK EXPRESS'),
        ('start_track_fixed_price_premium', 'STARTRACK FIXED PRICE PREMIUM'),
        ('start_premium', 'STARTRACK PREMIUM'),
        ('tm01', 'T M01'),
        ('tqb', 'TQB'),
        ('ups', 'UPS')
    ])

    picking_name = fields.Char(related='picking_type_id.name')
