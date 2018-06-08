from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    profit = fields.Float('Profit no tax', compute='_compute_margin')
    margin_no_tax = fields.Float('Margin no tax (%)', compute='_compute_margin')
    height = fields.Float('Height', help='in cm')
    depth = fields.Float('Depth', help='in cm')
    width = fields.Float('Width', help='in cm')
    volumetric_weight = fields.Float('Volumetric weight', help='in kg')

    @api.onchange('height', 'depth', 'width')
    def onchange_volumetric_weight(self):
        self.ensure_one()
        self.volumetric_weight = self.height * self.depth * self.width / 5000

    @api.multi
    def _compute_margin(self):
        for rec in self:
            sale_tax_id = rec.taxes_id and rec.taxes_id[0] or False
            sale_tax_included = sale_tax_id and sale_tax_id.price_include
            purchase_tax_id = rec.supplier_taxes_id and rec.supplier_taxes_id[0]
            purchase_tax_included = purchase_tax_id and purchase_tax_id.price_include

            sale_price_net = sale_tax_included and rec.list_price * 100 / (100 + sale_tax_id.amount) or rec.list_price
            purchase_price_net = purchase_tax_included and rec.standard_price * 100 / (100 + purchase_tax_id.amount) or rec.standard_price

            rec.profit = sale_price_net - purchase_price_net
            rec.margin_no_tax = sale_price_net and rec.profit * 100 / sale_price_net or 0.0


class JMDProductProduct(models.Model):
    _inherit = 'product.product'
    _name = 'product.product'

    barcode = fields.Char(string='Barcode', oldname='ean13', copy=False, help="International Article Number used for product identification.")
    default_code = fields.Char('Internal Reference', select=True)

    @api.constrains('barcode', 'default_code')
    @api.one
    def _check_duplicate(self):
        if self.barcode:
            list_rec = self.env['product.product'].search([('barcode', '=', self.barcode)])
            list_rec = list_rec - self
            if len(list_rec) > 0:
                raise UserError(_('Barcode already exists'))

        if self.default_code:
            list_rec = self.env['product.product'].search([('default_code', '=', self.default_code)])
            list_rec = list_rec - self
            if len(list_rec) > 0:
                raise UserError(_('Internal reference already exists'))
