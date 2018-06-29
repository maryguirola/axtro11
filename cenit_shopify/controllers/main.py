# -*- coding: utf-8 -*-
import json
import logging

from odoo import SUPERUSER_ID
from odoo import http
from odoo.api import Environment
from odoo.http import request
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


class ShopifyController(http.Controller):
    def get_registry(self, my_request):
        environ = my_request.httprequest.headers.environ.copy()

        key = environ.get('HTTP_X_USER_ACCESS_KEY', False)
        token = environ.get('HTTP_X_USER_ACCESS_TOKEN', False)
        db_name = environ.get('HTTP_TENANT_DB', False)

        if not db_name:
            host = environ.get('HTTP_HOST', "")
            db_name = host.replace(".", "_").split(":")[0]

        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            connection_model = env['cenit.connection']
            domain = [('key', '=', key), ('token', '=', token)]
            _logger.info(
                "Searching for a 'cenit.connection' with key '%s' and "
                "matching token", key)
            rc = connection_model.search(domain)
            _logger.info("Candidate connections: %s", rc)
            if rc is not None:
                return registry
            else:
                status_code = 404
        r = {'status': status_code}

        return json.dumps(r)

    """
      Creates a sales order
    """

    @http.route(['/orders/<string:action>',
                 '/orders/<string:action>/<string:root>'],
                type='json', auth='none', methods=['POST'], csrf=False)
    def create_sales_orders(self, action, root=None):
        registry = self.get_registry(request)
        with registry.cursor() as cr:
            if action == 'push':
                res = self.create_order(cr, request.jsonrequest, Environment(cr, SUPERUSER_ID, context=request.context))
                if not res:
                    res = {
                        'status': 201,
                        'name': self.get_id_from_record(cr, 'sale.order', [
                            ('client_order_ref', '=', request.jsonrequest.get('client_order_ref'))], 'name')
                    }
                else:
                    res['status'] = 202
                    res['name'] = self.get_id_from_record(cr, 'sale.order', [
                        ('client_order_ref', '=', request.jsonrequest.get('client_order_ref'))], 'name')
            else:
                res = {'status': 404}
        return res

    def create_order(self, cr, order_data, env):

        partner_name = order_data['partner_id']['name']

        order_id = self.get_id_from_record(cr, 'sale.order',
                                           [('client_order_ref', '=', order_data.get('client_order_ref'))])
        if order_id and not order_data['force_creation']:
            return {
                'errors': {'notify': 'The order with Customer Reference: ' + order_data.get(
                    'client_order_ref') + ' is already created in Odoo'}}

        partner_id = self.get_id_from_record(cr, 'res.partner', [('name', '=', partner_name)])
        if partner_id:
            order_data['partner_id'] = partner_id  # Updating partner_id(Customer)
            order_data['partner_invoice_id'] = partner_id  # Updating invoice address
            order_data['partner_shipping_id'] = partner_id  # Updating shipping address

            partner = env['res.partner'].browse(partner_id)[0]
            order_data['payment_term_id'] = partner['property_payment_term_id']['id']

            order_data['warehouse_id'] = self.get_id_from_record(cr, 'stock.warehouse',
                                                                 [('code', '=', order_data['warehouse_id'])])

            order_data['user_id'] = self.get_id_from_record(cr, 'res.users',
                                                            [('name', '=',
                                                              order_data['user_id'])])  # Updating sales person

            order_data['team_id'] = self.get_id_from_record(cr, 'crm.team',
                                                            [('name', '=', order_data['team_id'])])
            lines = {}
            if order_data.get('order_line'):
                lines = order_data.pop('order_line')
                # Verify if all the products included in the Order lines exist before creating the Order.
                missing_products = ""
                for line in lines:
                    domain = [('barcode', '=', line['barcode'])]
                    line['product_id'] = self.get_id_from_record(cr, 'product.product', domain)
                    if not line['product_id']:
                        if missing_products:
                            missing_products += "\n"
                        missing_products = "- [" + line['barcode'] + "] " + line['name'] + "."
                if missing_products:
                    return {
                        'errors': {
                            'notify': "The following product(s) is(are) found in Shopify but not in Odoo:\n" + missing_products}}
            else:
                return {
                    'errors': {
                        'notify': "The Order does not have orders lines."}}

            errors = None
            try:
                saleorder_registry = env['sale.order']
                if not order_id:
                    order_id = saleorder_registry.create(order_data).id
                else:
                    saleorder_registry.browse(order_id).write(order_data)
                if order_id:
                    # Create order lines
                    if lines:
                        for line in lines:
                            i_registry = env['product.product']
                            domain = [('barcode', '=', line['barcode'])]
                            line['product_id'] = self.get_id_from_record(cr, 'product.product', domain)

                            product = i_registry.browse(line['product_id'])[0]
                            line['name'] = product['name']
                            line['order_id'] = order_id
                            line['product_uom'] = product['uom_id']['id']

                            line['customer_lead'] = product['sale_delay']

                            line['tax_id'] = [[x.id] for x in product['taxes_id']]
                            if line['tax_id']:
                                line['tax_id'] = [(6, 0, line['tax_id'][0])]

                            if product['property_account_income_id']['id']:
                                line['property_account_income_id'] = product['property_account_income_id']['id']
                            else:
                                line['property_account_income_id'] = \
                                    product['categ_id']['property_account_income_categ_id']['id']

                            if product['property_account_expense_id']['id']:
                                line['property_account_expense_id'] = product['property_account_expense_id']['id']
                            else:
                                line['property_account_expense_id'] = \
                                    product['categ_id']['property_account_expense_categ_id']['id']

                            line_id = self.get_id_from_record(cr, 'sale.order.line',
                                                              [('order_id', '=', order_id),
                                                               ('product_id', '=', product['id'])])
                            if not line_id:
                                env['sale.order.line'].create(line)
                            else:
                                env['sale.order.line'].browse(line_id).write(line)

                order_data['order_line'] = lines
                order = env['sale.order'].browse(order_id)
                if order.action_confirm():  # Creating delivery
                    # STOCK
                    stock_pick_id = self.get_id_from_record(cr, 'stock.picking',
                                                            [('origin', '=', order.name)])
                    if stock_pick_id:
                        stock_pick = env['stock.picking'].browse(stock_pick_id)[0]

                        if stock_pick["state"] == "confirmed":
                            stock_pick.force_assign()  # Forcing assign

                        env['stock.immediate.transfer'].create({'pick_ids': [(6, 0, [stock_pick.id])]}).process()

                    invoice_id = order.action_invoice_create()  # Creating invoice
                    invoice = env['account.invoice'].browse(invoice_id)
                    invoice.date_invoice = order_data.get('date_order', False)
                    if invoice.action_invoice_open():
                        invoice.pay_and_reconcile(invoice.journal_id.id)

                order.action_done()  # Confirm order to status "Done"

            except Exception as e:
                _logger.error(e)
                errors = e

            return {'errors': {'error': errors}} if errors else None

        return {'errors': {'notify': "There is no Customer named '" + partner_name + "'"}}

    def get_id_from_record(self, cr, model, domain, field='id'):
        env = Environment(cr, SUPERUSER_ID, {})
        i_registry = env[model]
        try:
            rc = i_registry.search(domain, limit=1)  # Returns id
        except Exception as e:
            rc = None
        if rc:
            return rc[field]
        else:
            return False
