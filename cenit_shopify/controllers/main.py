# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

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

        registry = Registry.new(db_name=db_name)
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
        status_code = 400

        registry = self.get_registry(request)
        with registry.cursor() as cr:
            if action == 'push':
                r = self.create_order(cr, request, Environment(cr, SUPERUSER_ID, context=request.context))
                if not r:
                    status_code = '200'
                else:
                    return r
            else:
                status_code = 404

        return {'status': status_code}

    def create_order(self, cr, my_request, registry):
        order_data = my_request.jsonrequest

        partner_name = order_data['partner_id']['name']
        context = my_request.context

        order_id = self.get_id_from_record(cr, 'sale.order',
                                           [('jmd_po_number_so', '=', order_data.get('jmd_po_number_so'))],
                                           context=context)
        if order_id and not order_data['force_creation']:
            return {
                'errors': {'notify': 'The order ' + order_data.get('jmd_po_number_so') + ' is already created in Odoo'}}

        partner_id = self.get_id_from_record(cr, 'res.partner', [('name', '=', partner_name)],
                                             context=context)
        if partner_id:
            order_data['partner_id'] = partner_id  # Updating partner_id(Customer)
            order_data['partner_invoice_id'] = partner_id  # Updating invoice address
            order_data['partner_shipping_id'] = partner_id  # Updating shipping address

            # partner = registry['res.partner'].browse(cr, SUPERUSER_ID, partner_id, context=context)[0]
            partner = registry['res.partner'].browse(partner_id)[0]
            order_data['payment_term_id'] = partner['property_payment_term_id']['id']

            order_data['warehouse_id'] = self.get_id_from_record(cr, 'stock.warehouse',
                                                                 [('name', '=', order_data['warehouse_id'])],
                                                                 context=context)

            order_data['user_id'] = self.get_id_from_record(cr, 'res.users',
                                                            [('name', '=', order_data['user_id'])],
                                                            context=context)  # Updating sales person

            order_data['team_id'] = self.get_id_from_record(cr, 'crm.team',
                                                            [('name', '=', order_data['team_id'])],
                                                            context=context)
            errors = None

            lines = {}
            if order_data.get('order_line'):
                lines = order_data.pop('order_line')
                saleorder_registry = registry['sale.order']
            try:
                order_id = self.get_id_from_record(cr, 'sale.order', [('name', '=', order_data.get('name'))],
                                                   context=context)
                if not order_id:
                    order_id = saleorder_registry.create(order_data)
                else:
                    saleorder_registry.write(order_id, order_data)
                if order_id:
                    # Create order lines
                    if lines:
                        for line in lines:
                            i_registry = registry['product.product']
                            domain = [('barcode', '=', line['jmd_product_barcode'])]
                            line['product_id'] = self.get_id_from_record(cr, 'product.product', domain,
                                                                         context=context)

                            if not line['product_id']:
                                errors = 'Product ' + line['name'] + ' -' + line[
                                    'jmd_product_barcode'] + ' is found in Shopify but not in Odoo'
                            else:
                                product = i_registry.browse(cr, SUPERUSER_ID, line['product_id'], context=context)[0]
                                line['name'] = product['name']
                                line['order_id'] = order_id
                                line['product_uom'] = product['uom_id']['id']

                                line['customer_lead'] = product['sale_delay']

                                line['tax_id'] = [[x.id] for x in product['taxes_id']]
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
                                                                   ('product_id', '=', product['id'])], context=context)
                                if not line_id:
                                    registry['sale.order.line'].create(line)
                                else:
                                    registry['sale.order.line'].write(line_id, line)
            except Exception as e:
                _logger.error(e)
                errors = e

            if not errors:
                order_data['order_line'] = lines
                ord_id = self.get_id_from_record(cr, 'sale.order', [('name', '=', order_data['name'])],
                                                 context=context)
                ord = registry['sale.order'].browse(cr, SUPERUSER_ID, ord_id, context=context)[0]
                try:
                    ord.action_confirm()  # Creating delivery
                    # STOCK
                    stock_pick_id = self.get_id_from_record(cr, 'stock.picking',
                                                            [('origin', '=', order_data['name'])], context=context)
                    stock_pick = registry['stock.picking'].browse(stock_pick_id, context=context)[0]

                    if stock_pick["state"] == "confirmed":
                        stock_pick.force_assign()  # Forcing assign
                    else:
                        stock_pick.do_new_transfer()  # Validating assign

                    stock_transf_id = registry['stock.immediate.transfer'].create({'pick_id': stock_pick.id})
                    stock_transf = \
                        registry['stock.immediate.transfer'].browse(cr, SUPERUSER_ID, stock_transf_id, context=context)[
                            0]
                    stock_transf.process()

                    inv_id = ord.action_invoice_create()  # Creating invoice

                    if order_data['amount_total'] == 0:
                        inv = registry['account.invoice'].browse(cr, SUPERUSER_ID, inv_id, context=context)[0]
                        inv.action_move_create()
                        inv_date = order_data.get('date_order', datetime.now())
                        registry['account.invoice'].write(inv_id, {'date_invoice': inv_date, 'state': 'paid'})
                        inv._onchange_payment_term_date_invoice()

                    ord.action_done()  # Confirm order to status "Done"

                except Exception as e:
                    _logger.error(e)
                    errors = e

            return {'errors': {'notify': errors}} if errors else None

        return {'errors:': {'notify': 'There is no Customer named ' + partner_name}}

    def get_id_from_record(self, cr, model, domain, context):
        env = Environment(cr, SUPERUSER_ID, context=context)
        i_registry = env[model]
        try:
            rc = i_registry.search(domain, limit=1)  # Returns id
        except Exception as e:
            rc = None
        if rc:
            return rc.id
        else:
            return None
