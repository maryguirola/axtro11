# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class JmdInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

# Fields for printing of invoice ----------------------------

    jmd_partner_shipping_id = fields.Many2one('res.partner',compute='_get_from_so', string='Delivery Address',
                                              help="Delivery address for current Invoice.")
    jmd_po_number = fields.Char('P/O Number', compute='_get_from_so')
    jmd_nodiscount = fields.Boolean(string='Print discount', compute='_assess_show_print')
    jmd_print_barcode = fields.Boolean(string='Print barcode', compute='_assess_show_print')

    @api.depends('origin')
    def _get_from_so(self):
        for rec in self:
            so = self.env['sale.order'].search([('name','=',rec.origin)]) and \
                          self.env['sale.order'].search([('name','=',rec.origin)])[0] or False

            customer_po = so and so.jmd_po_number_so or False
            shipping_id = so and so.partner_shipping_id or False

            rec.update({'jmd_po_number': customer_po,
                       'jmd_partner_shipping_id': shipping_id and shipping_id.id or False})

    def _assess_show_print(self):
        for rec in self:
            line_ids = rec.invoice_line_ids
            hide_discount = all(item.discount == 0.0 for item in line_ids)
            hide_barcode = all(item.jmd_product_barcode == False for item in line_ids)
            rec.update({'jmd_nodiscount':not hide_discount,
                       'jmd_print_barcode': not hide_barcode})
        return

# Fields for printing - End ------------------------------------------

    @api.multi
    def add_po_number_in_name(self):
        """
        Add po number on ref if it exists
        """

        for rec in self:
            if not rec.name and rec.jmd_po_number:
                rec.write({'name': rec.jmd_po_number})
        return True


class JmdInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    _name = 'account.invoice.line'

    jmd_product_barcode = fields.Char(related='product_id.barcode',string='Barcode', readonly=True)