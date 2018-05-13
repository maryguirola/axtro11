from odoo import api, fields, models, _


class JmdStockPicking(models.Model):
    _inherit = 'stock.picking'
    _name = 'stock.picking'

    jmd_partner_invoice_id_do = fields.Many2one('res.partner', string='Invoice Address', compute='_get_partner_invoice',
                                                help="Invoice address for current Invoice.")

    def _get_partner_invoice(self):
        for rec in self:
            rec.jmd_partner_invoice_id_do = rec.sale_id.partner_invoice_id or False

    # @api.one
    # @api.depends('pack_operation_product_ids.qty_done')
    # def _compute_qty(self):
    #     self.quantity_total = sum(line.qty_done for line in self.pack_operation_product_ids)

    @api.one
    @api.depends('move_lines')
    def _compute_qty(self):
        self.quantity_total = int(sum(move.product_uom_qty for move in self.move_lines))

    quantity_total = fields.Integer(string='Total Quantity',
                             readonly=True, compute='_compute_qty',
                             track_visibility='always')


class JmdStockMove(models.Model):
    _inherit = 'stock.move'
    _name = 'stock.move'

    sale_description = fields.Char('Sale Description', compute='_get_description_from_sale')

    @api.one
    def _get_description_from_sale(self):
        # proc = self.env['procurement.order'].search([('move_ids', 'in', self.id)])
        # if len(proc) == 0:
        #     self.sale_description = False
        #     return
        #
        # sale_line = proc[0].sale_line_id
        # if len(sale_line) == 0:
        #     self.sale_description = False
        #     return

        self.sale_description = self.sale_line_id and self.sale_line_id.name or False

    @api.multi
    def action_done(self):
        result = super(JmdStockMove, self).action_done()

        # update the sale_description in the pack operation
        for rec in self:
            linked_list = rec.linked_move_operation_ids
            linked_operation = linked_list.mapped('operation_id')
            sale_description = rec.sale_description
            len(linked_operation) > 0 and sale_description and linked_operation.write({'sale_description': sale_description})
        return result


# class JmdStockPackOperation(models.Model):
#     _inherit = 'stock.pack.operation'
#     _name = 'stock.pack.operation'
#
#     sale_description = fields.Char('Sale Description')