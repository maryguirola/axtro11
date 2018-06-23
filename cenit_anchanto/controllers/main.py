__author__ = 'mary'

import logging
import json
from odoo import http, api
from odoo.http import request
from odoo import SUPERUSER_ID
from odoo.modules.registry import Registry
from datetime import datetime
from odoo.api import Environment
from operator import attrgetter

_logger = logging.getLogger(__name__)


class AnchantoController(http.Controller):
    @http.route(['/product'],
                type='http', auth='none', methods=['GET'], csrf=False)
    def get_product(self, key_search, value):
        """
          Gets a product from the inventory module by a key and value specified

          :param key_search: Filter of the search
          :param value: Value of the filter
          :return: Product found
        """
        db_name = self.search_connection(request)
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            domain = [(key_search, '=', value)]
            product = env['product.template'].search(domain)
            # product = env['product.template'].browse(product_id)
            if product:
                data = {
                    "response": "success",
                    "product": {
                        "id": product["id"],
                        "name": product["name"],
                        "barcode": product["barcode"],
                        "cost": product["standard_price"],
                        "list_price": product['list_price']
                    }
                }
            else:
                data = {
                    "response": "Product not found"
                }
            return request.make_response(data=json.dumps(data), headers={'Content-Type': 'application/json'})

    @http.route(['/products'],
                type='http', auth='none', methods=['GET'], csrf=False)
    def get_products(self, offset):
        """
          Gets all products from the inventory module

          :return: List of products
       """
        db_name = self.search_connection(request)
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            prod_tm = env['product.template']
            products = prod_tm.search_read(fields=['id', 'name', 'barcode', 'standard_price', 'weight', 'default_code'],
                                           order='id', limit=50, offset=int(offset))
            return request.make_response(data=json.dumps(products), headers={'Content-Type': 'application/json'})

    @http.route(['/product'],
                type='json', auth='none', methods=['PUT'], csrf=False)
    def update_product_weight(self):
        """
          Updates the product's weight by its id
        """
        db_name = self.search_connection(request)
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            data = request.jsonrequest
            prod = env['product.template'].search([('id', '=', data["odoo_product_id"])])

            if prod:
                result = prod.write({'weight': data["weight"]})
                if result:
                    return {'response': 'success'}
            else:
                return {'response': 'Product with id ' + str(data["odoo_product_id"]) + ' wasn\'t found'}

    @http.route(['/purchaseorder'],
                type='json', auth='none', methods=['PUT'], csrf=False)
    def update_receipt_from_purchase_order(self):
        """
        Updates a field of the purchase order receipt
        """
        db_name = self.search_connection(request)
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            data = request.jsonrequest
            po = env['stock.picking'].search([('id', '=', data["id"])])
            if po:
                po.write({data["field"]: data["value"]})
                return {'response': 'success'}
            else:
                return {'response': 'Purchase order number ' + data['name'] + 'not found'}

    @http.route(['/purchaseorder/shipment'],
                type='json', auth='none', methods=['PUT'], csrf=False)
    def update_shipment_purchase_order(self):
        '''
        Set to DONE the transfer associated with the Purchase order
        :return:
        '''
        db_name = self.search_connection(request)
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            data = request.jsonrequest
            data_products = data["products"]
            pick = env['stock.picking'].search([('id', '=', data["id"])])
            if pick:
                products = pick.move_lines
                for prod in products:
                    if prod['product_id']['barcode'] in data_products:
                        barcode = prod['product_id']['barcode']
                        prod.write(
                            {'qty_done': data_products[barcode]})  # Updating product's quantities in stock.picking

                # Validate transfer(stock.picking)
                if pick.check_backorder(pick):  # Check if create back order
                    back_order = env['stock.backorder.confirmation'].create({'pick_id': pick.id})
                    back_order.process()
                else:
                    pick.do_new_transfer()  # Else, update product's quantities and set to done the Transfer.
                return {'response': 'success'}
            else:
                return {'response': 'Shipment ' + data['name'] + 'not found'}

    def search_connection(self, my_request):
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
                return db_name
            else:
                status_code = 404
        r = {'status': status_code}

        return json.dumps(r)

    @http.route(['/purchaseorder/products'],
                type='http', auth='none', methods=['GET'], csrf=False)
    def get_products_purchase_order(self, id, po_number):
        '''
        Gets the products of a purchase order's receipt
        :return: Products
        '''
        db_name = self.search_connection(request)
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            pick = env['stock.picking'].search([('id', '=', id)])
            po = env['purchase.order'].search([('name', '=', po_number)])
            if pick:
                if po:
                    prods = []
                    products = pick.move_lines  # Products of Receipt

                    for p in products:
                        prod_line = po['order_line'].search([('product_id', '=', p['product_id']['id']),
                                                             ('order_id', '=', po_number)])
                        if len(prod_line) > 0:
                            # If there are more than one line with the same product, it takes the line with highest price
                            prod_line = sorted(prod_line, key=attrgetter('price_unit'), reverse=True)[0]

                        data = {
                            'sku': p['product_id']['barcode'],
                            'cost_price': prod_line['price_unit'],
                            'expiry_date': prod_line['date_planned'],
                            'quantity': p['product_qty']
                        }
                        prods.append(data)
                        data = prods
                else:
                    data = {'errors':{'notify': 'Purchase order number ' + po_number + 'not found'}}

            else:
                data ={'errors': {'notify': 'Not found', 'state': 404}}

            return request.make_response(data=json.dumps(data), headers={'Content-Type': 'application/json'})

    @http.route(['/salesorder/delivery'],
                type='json', auth='none', methods=['POST'], csrf=False)
    def validate_delivery_order(self):
        '''
        Validates the delivery order associated with the Sales Order
        :return:
        '''
        db_name = self.search_connection(request)
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            data = request.jsonrequest
            pick = env['stock.picking'].search([('name', '=', data["number"])])
            if pick:
                origin = pick['origin'] + " / " + data['tracking_number']
                pick.write({'origin': origin})  # Updating delivery order's source document

                pick.button_validate()  # Set to DONE the delivery order.

                stock_transf_id = env['stock.immediate.transfer'].create({'pick_id': pick.id})
                stock_transf = env['stock.immediate.transfer'].search([('id', '=', stock_transf_id.id)])
                stock_transf.process()

                return {'response': 'success'}
            else:
                return {'response': 'Delivery order ' + data['number'] + ' not found'}

    @http.route(['/delivery_order/delivery_slip/pdf/<int:order_id>'],
                type='http', auth='none', methods=['GET'], csrf=False)
    def retrieve_delivery_slip_as_pdf(self, order_id=1):
        """
        Retrieve Delivery Order PDF (Picking Operations)
        :return:
        """
        db_name = self.search_connection(request)
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            # data = request.jsonrequest
            pick = env['stock.picking'].search([('id', '=', order_id)])
            if pick:
                pdf = env.ref('stock.action_report_delivery').render_qweb_pdf([order_id])[0]
                import base64
                vals = {'response': 'success', 'code': 200, 'pdf': str(base64.encodebytes(pdf), 'utf-8'), 'pdf_name': pick.name}
            else:
                vals = {'response': 'Delivery order ' + order_id + ' not found'}
            return json.dumps(vals)
