# -*- coding: utf-8 -*-

from openerp import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    _name = 'account.payment'

    invoices_total = fields.Monetary('Invoices Total', compute='_compute_invoice_total')
    residual_total = fields.Monetary('Amount Due Total', compute='_compute_invoice_total')

    @api.multi
    def _compute_invoice_total(self):
        for rec in self:
            if rec.invoice_ids:
                invoices_total = sum(rec.invoice_ids.mapped('amount_total_signed'))
                residual_total = sum(rec.invoice_ids.mapped('residual'))
                rec.update({'invoices_total': invoices_total,
                            'residual_total': residual_total})
        return
