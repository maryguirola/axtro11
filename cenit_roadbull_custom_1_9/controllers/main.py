from odoo import http, SUPERUSER_ID
from odoo.api import Environment
from odoo.http import request
from odoo.modules.registry import Registry
import logging, json

_logger = logging.getLogger(__name__)


class RoadbullController(http.Controller):
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

    @http.route(['/deliveryorder/write'],
                type='json', auth='none', methods=['POST'], csrf=False)
    def update_delivery_order(self):
        """
        Updates a field of the delivery order receipt
        """
        registry = self.get_registry(request)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            data = request.jsonrequest
            delivery_order = env['stock.picking'].search([('id', '=', data["id"])])
            if delivery_order and delivery_order.carrier_tracking_ref is False:
                for field in data:
                    if field == "error_message" or data[field]:
                        delivery_order.write({field: data[field]})
                if not data['error_message']:
                    msg = "Shipment sent to carrier %s for expedition with tracking number %s" % (
                        delivery_order.carrier_id.name, delivery_order.carrier_tracking_ref)
                    delivery_order.message_post(body=msg)
                return {'response': 'success'}
            if not delivery_order:
                return {'response': 'failure', 'message': 'Delivery order id ' + data['id'] + ' not found'}
