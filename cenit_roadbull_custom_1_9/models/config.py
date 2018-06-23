# -*- coding: utf-8 -*-
# #############################################################################
#
# OpenERP, Open Source Management Solution
# Copyright (C) 2004-2010, 2014 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging, os
from odoo import models, api
from datetime import datetime

_logger = logging.getLogger(__name__)

COLLECTION_NAME = "roadbull_1_9"
COLLECTION_VERSION = "1.0.0"
COLLECTION_PARAMS = {
    # WITHOUT COLLECTION_PARAMS.
}


class CenitIntegrationSettings(models.TransientModel):
    _name = "cenit.roadbull_1_9.settings"
    _inherit = 'cenit.hub.settings'

    ############################################################################
    # Pull Parameters
    ############################################################################
    # WITHOUT PULL PARAMETERS.

    ############################################################################
    # Default Getters
    ############################################################################
    # WITHOUT GETTERS.

    ############################################################################
    # Default Setters
    ############################################################################
    # WITHOUT SETTERS.

    ############################################################################
    # Actions
    ############################################################################
    @api.model
    def install(self):
        cenit_api = self.env['cenit.api']
        path = "/setup/collection?"
        path = "%s%s=%s" % (path, 'name', COLLECTION_NAME)
        rc = cenit_api.get(path)
        if isinstance(rc, list):
            rc = rc[0]
        collection_id = rc['collections'][0]['id']
        del rc
        installer = self.env['cenit.collection.installer']
        installer.install_collection({'id': collection_id})
        self.import_roadbull_data()
        self.import_roadbull_mapping()

    @api.multi
    def update_collection(self):
        self.install()

    def import_roadbull_data(self):
        def _get_delivery_time(from_time, to_time):
            from_time = datetime.strptime(from_time, "%Y-%m-%dT%H:%M:%S").strftime("%H:%M")
            to_time = datetime.strptime(to_time, "%Y-%m-%dT%H:%M:%S").strftime("%H:%M")
            return '(' + from_time + ' - ' + to_time + ')'

        cenit_api = self.env['cenit.api']
        producttypes = cenit_api.get('/roadbull/product_type')['product_types']
        producttype_obj = self.env['roadbull.producttype']
        size_obj = self.env['roadbull.size']
        service_obj = self.env['roadbull.service']
        timeoption_obj = self.env['roadbull.timeoption']
        for producttype in producttypes:
            size_ids = []
            sizes = producttype['Sizes'] if 'Sizes' in producttype.keys() else []
            for size in sizes:
                services_ids = []
                services = size['Services'] if 'Services' in size.keys() else []
                for service in services:
                    pickup_time_slot_ids = []
                    pickup_time_slots = service['PickupTimeSlots'] if 'PickupTimeSlots' in service.keys() else []
                    for pickup_time_slot in pickup_time_slots:
                        timeoption = timeoption_obj.search([('timeoption_id', '=', pickup_time_slot['Id'])])
                        vals = {
                            'timeoption_id': pickup_time_slot['Id'],
                            'name': pickup_time_slot['TimeSlotName'] + ' ' + _get_delivery_time(
                                pickup_time_slot['FromTime'], pickup_time_slot['ToTime']),
                            'from_time': pickup_time_slot['FromTime'],
                            'to_time': pickup_time_slot['ToTime'],
                            'is_allow_pre_order': pickup_time_slot['IsAllowPreOrder']
                        }
                        if not timeoption:
                            timeoption = timeoption_obj.create(vals)
                        else:
                            timeoption.write(vals)
                        pickup_time_slot_ids.append(timeoption.id)

                    delivery_time_slot_ids = []
                    delivery_time_slots = service['DeliveryTimeSlots'] if 'DeliveryTimeSlots' in service.keys() else []
                    for delivery_time_slot in delivery_time_slots:
                        timeoption = timeoption_obj.search([('timeoption_id', '=', delivery_time_slot['Id'])])
                        vals = {
                            'timeoption_id': delivery_time_slot['Id'],
                            'name': delivery_time_slot['TimeSlotName'] + ' ' + _get_delivery_time(
                                delivery_time_slot['FromTime'], delivery_time_slot['ToTime']),
                            'from_time': delivery_time_slot['FromTime'],
                            'to_time': delivery_time_slot['ToTime'],
                            'is_allow_pre_order': delivery_time_slot['IsAllowPreOrder']
                        }
                        if not timeoption:
                            timeoption = timeoption_obj.create(vals)
                        else:
                            timeoption.write(vals)
                        delivery_time_slot_ids.append(timeoption.id)

                    service_exist = service_obj.search([('service_id', '=', service['Id'])])
                    vals = {
                        'service_id': service['Id'],
                        'name': service['ServiceName'],
                        'cost': service['Cost'],
                        'is_delivery_date_allow': service['IsDeliveryDateAllow'],
                        'is_delivery_time_allow': service['IsDeliveryTimeAllow'],
                        'is_pickup_time_allow': service['IsPickupTimeAllow'],
                        'is_pickup_date_allow': service['IsPickupDateAllow'],
                        'available_delivery_date_range': service['AvailableDeliveryDateRange'],
                        'available_pickup_date_range': service['AvailablePickupDateRange'],
                        'available_delivery_time_slots': service['AvailableDeliveryTimeSlots'],
                        'available_pickup_time_slots': service['AvailablePickupTimeSlots'],
                        'pickup_time_slot_ids': [(6, 0, pickup_time_slot_ids)],
                        'delivery_time_slot_ids': [(6, 0, delivery_time_slot_ids)]
                    }
                    if not service_exist:
                        service_exist = service_obj.create(vals)
                    else:
                        service_exist.write(vals)
                    services_ids.append(service_exist.id)

                size_exist = size_obj.search([('size_id', '=', size['Id'])])
                vals = {
                    'size_id': size['Id'],
                    'name': size['SizeName'],
                    'from_weight': size['FromWeight'],
                    'to_weight': size['ToWeight'],
                    'from_length': size['FromLength'],
                    'to_length': size['ToLength'],
                    'service_ids': [(6, 0, services_ids)]
                }
                if not size_exist:
                    size_exist = size_obj.create(vals)
                else:
                    size_exist.write(vals)
                size_ids.append(size_exist.id)
            producttype_exist = producttype_obj.search([('producttype_id', '=', producttype['Id'])])
            vals = {
                'producttype_id': producttype['Id'],
                'name': producttype['ProductTypeName'],
                'close_window_time': 55,
                'size_ids': [(6, 0, size_ids)]
            }
            if not producttype_exist:
                producttype_obj.create(vals)
            else:
                producttype_exist.write(vals)

    def import_roadbull_mapping(self):
        basepath = os.path.dirname(__file__)
        filepath = os.path.abspath(os.path.join(basepath, "..", "data/mappings.json"))
        with open(filepath) as json_file:
            import base64
            vals = {
                'filename': 'mappings.json',
                'b_file': base64.encodebytes(json_file.read().encode("utf-8"))
            }
            cenit_import_export = self.env['cenit.import_export'].create(vals)
            return cenit_import_export.import_data_types()
