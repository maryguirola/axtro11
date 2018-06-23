# -*- coding: utf-8 -*-
from odoo import models


class RoadbullSaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_delivery_line(self, carrier, price_unit):
        if price_unit == 0:
            return None
        return super(RoadbullSaleOrder, self)._create_delivery_line(carrier, price_unit)
