from odoo import api, fields, models, _


class JmdSaleOrder(models.Model):
    _inherit = 'sale.order'
    _name = 'sale.order'

# Fields for printing of invoice ----------------------------
    jmd_po_number_so = fields.Char(string='P/O Number')
    jmd_nodiscount_so = fields.Boolean(string='Display disc. on SO', compute='_assess_show_print')
    jmd_print_barcode = fields.Boolean(string='Print barcode', compute='_assess_show_print')

    def _assess_show_print(self):
        for rec in self:
            line_ids = rec.order_line
            hide_discount = all(item.discount == 0.0 for item in line_ids)
            hide_barcode = all(not item.jmd_product_barcode for item in line_ids)
            rec.update({'jmd_nodiscount_so': not hide_discount,
                        'jmd_print_barcode': not hide_barcode})


class JmdSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _name = 'sale.order.line'

    jmd_product_barcode = fields.Char(related='product_id.barcode', string='Barcode', readonly=True)
