# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, time, timedelta
import pytz
import time as basic_time


class RoadbullProductType(models.Model):
    _name = 'roadbull.producttype'
    producttype_id = fields.Integer()
    name = fields.Char('Product Type Name')
    close_window_time = fields.Integer('Close window time', default=55)
    size_ids = fields.Many2many('roadbull.size', column1='producttype_id', column2='size_id',
                                string='Sizes')


class RoadbullSize(models.Model):
    _name = 'roadbull.size'
    size_id = fields.Integer()
    name = fields.Char('Size name')
    from_weight = fields.Integer('From weight')
    to_weight = fields.Integer('To weight')
    from_length = fields.Integer('From length')
    to_length = fields.Integer('To length')
    service_ids = fields.Many2many('roadbull.service', column1='size_id', column2='service_id',
                                   string='Services')


class RoadbullService(models.Model):
    _name = 'roadbull.service'
    service_id = fields.Integer()
    name = fields.Char('Service name')
    cost = fields.Integer('Cost')
    is_delivery_date_allow = fields.Boolean('Is Delivery Date Allow', defaul=True)
    is_delivery_time_allow = fields.Boolean('Is Delivery Time Allow', default=True)
    is_pickup_time_allow = fields.Boolean('Is Pickup Time Allow', default=True)
    is_pickup_date_allow = fields.Boolean('Is Pickup Date Allow', default=True)
    available_delivery_date_range = fields.Char('Available Delivery Date Range', default='1,2')
    available_pickup_date_range = fields.Char('Available Pickup Date Range', default='0,4')
    available_delivery_time_slots = fields.Char('Available Delivery Time Slots', default='5')
    available_pickup_time_slots = fields.Char('Available Pickup Time Slots', default='26,27')
    pickup_time_slot_ids = fields.Many2many('roadbull.timeoption', 'roadbull_service_roadbull_pickup_time_slot_rel',
                                            column1='service_id',
                                            column2='timeoption_id', string='Pickup time slots')
    delivery_time_slot_ids = fields.Many2many('roadbull.timeoption', 'roadbull_service_roadbull_delivery_time_slot_rel',
                                              column1='service_id',
                                              column2='timeoption_id', string='Delivery time slots')


class RoadbullTimeOption(models.Model):
    _name = 'roadbull.timeoption'
    timeoption_id = fields.Integer()
    name = fields.Char('Time slot name')
    from_time = fields.Datetime('From time')
    to_time = fields.Datetime('To time')
    is_allow_pre_order = fields.Boolean('Is allow pre order', default=True)


class RoadbullOrder(models.Model):
    _inherit = 'stock.picking'

    def _create(self, vals):
        vals['number_of_packages'] = 1
        return super(RoadbullOrder, self)._create(vals)

    order_create_date = fields.Datetime(default=fields.Datetime.now)

    error_message = fields.Char()

    carrier_name = fields.Char(related='carrier_id.name')

    def _get_default_producttype_id(self):
        return self.env['roadbull.producttype'].search([('producttype_id', '=', 2)], limit=1)

    producttype_id = fields.Many2one('roadbull.producttype', 'Product type', states={'done': [('readonly', True)]},
                                     default=_get_default_producttype_id)

    def _get_default_size_id(self):
        return self.env['roadbull.size'].search([('size_id', '=', 1)])

    def _get_size_domain(self):
        producttype = self._get_default_producttype_id()
        return [('id', 'in', producttype.size_ids.ids)]

    size_id = fields.Many2one('roadbull.size', 'Size', states={'done': [('readonly', True)]},
                              default=_get_default_size_id, domain=_get_size_domain)

    def _get_default_service_id(self):
        return self.env['roadbull.service'].search([('service_id', '=', 1)])

    def _get_service_domain(self):
        size = self._get_default_size_id()
        return [('id', 'in', size.service_ids.ids)]

    service_id = fields.Many2one('roadbull.service', 'Service', states={'done': [('readonly', True)]},
                                 default=_get_default_service_id,
                                 domain=_get_service_domain)

    def _get_default_pickup_time_slot(self):
        timeoption_id = 26 if datetime.now(tz=pytz.timezone('Asia/Singapore')).time() < time(15) else 27
        return self.env['roadbull.timeoption'].search([('timeoption_id', '=', timeoption_id)])

    def _get_pickup_time_slot_domain(self):
        service = self._get_default_service_id()
        return [('id', 'in', service.pickup_time_slot_ids.ids)]

    pickup_time_slot = fields.Many2one('roadbull.timeoption', 'Pickup time slot', states={'done': [('readonly', True)]},
                                       default=_get_default_pickup_time_slot, domain=_get_pickup_time_slot_domain)

    def _get_default_pickup_date(self):
        tz = pytz.timezone('Asia/Singapore')
        create_date = datetime.now(tz)
        pickup_date = self._get_valid_date(create_date + timedelta(days=1))
        return pickup_date

    pickup_date = fields.Date('Pickup Date', states={'done': [('readonly', True)]}, default=_get_default_pickup_date)

    def _get_default_delivery_time_slot(self):
        return self.env['roadbull.timeoption'].search([('timeoption_id', '=', 5)])

    def _get_delivery_time_slot_domain(self):
        service = self._get_default_service_id()
        return [('id', 'in', service.delivery_time_slot_ids.ids)]

    delivery_time_slot = fields.Many2one('roadbull.timeoption', 'Delivery time slot',
                                         states={'done': [('readonly', True)]},
                                         default=_get_default_delivery_time_slot,
                                         domain=_get_delivery_time_slot_domain)

    def _get_default_delivery_date(self):
        return self._get_valid_date(self._get_default_pickup_date() + timedelta(days=1))

    delivery_date = fields.Date('Delivery Date', states={'done': [('readonly', True)]},
                                default=_get_default_delivery_date)

    is_exhange_order = fields.Boolean('Is Exchange Order?', states={'done': [('readonly', True)]}, default=False)

    is_do_order = fields.Boolean('Is DO Order?', states={'done': [('readonly', True)]}, default=True)

    remark = fields.Text(string='Remark',
                         default="1. Look for receiving personnel, delivery between 12-5pm (avoid lunch hrs).\n2. Collect back chop & signed DO. One copy to be passed to store,one copy to collect back the office.\n3. Complete delivery with EPOD -> full photo of DO. Exchange item = signed DO.")

    @api.onchange('carrier_id')
    def _set_producttype_id(self):
        if self.carrier_id.name == 'Roadbull':
            self.carrier_id.shipping_enabled = False

    @api.onchange('producttype_id')
    def _onchange_producttype_id(self):
        res = {}
        size_id = self.producttype_id.size_ids.ids[0] if len(self.producttype_id.size_ids.ids) > 0 else False
        self.size_id = self.env['roadbull.size'].search([('id', '=', size_id)])
        res['domain'] = {'size_id': [('id', 'in', self.producttype_id.size_ids.ids)]}
        return res

    @api.onchange('size_id')
    def _onchange_size_id(self):
        res = {}
        service_id = self.size_id.service_ids.ids[0] if self.size_id and len(
            self.size_id.service_ids.ids) > 0 else False
        self.service_id = self.env['roadbull.service'].search([('id', '=', service_id)])
        res['domain'] = {'service_id': [('id', 'in', self.size_id.service_ids.ids)]}

        return res

    @api.onchange('service_id')
    def _onchange_service_id(self):
        res = {'domain': {
            'pickup_time_slot': [('id', 'in', [])],
            'delivery_time_slot': [('id', 'in', [])]
        }}
        pickup_date = delivery_date = pickup_time_slot_id = delivery_time_slot_id = False
        if self.service_id:
            available_pickup_date_range = [1 if int(x) > 1 else int(x) for x in
                                           self.service_id.available_pickup_date_range.split(',')]
            tz = pytz.timezone('Asia/Singapore')
            create_date = datetime.now(tz)

            # Default values
            pickup_date = self._get_valid_date(create_date + timedelta(days=1))
            pickup_time_slot_id = self.service_id.pickup_time_slot_ids.ids[0] if len(
                self.service_id.pickup_time_slot_ids.ids) > 0 else False
            delivery_time_slot_id = self.service_id.delivery_time_slot_ids.ids[0] if len(
                self.service_id.delivery_time_slot_ids.ids) > 0 else False

            # Case in which the time pass 3:00PM
            if create_date.time() >= time(15):
                pickup_time_slot_id = self.service_id.pickup_time_slot_ids.ids[1] if len(
                    self.service_id.pickup_time_slot_ids.ids) > 1 else False
                if not pickup_time_slot_id:
                    if available_pickup_date_range[1] > 0:
                        pickup_time_slot_id = self.service_id.pickup_time_slot_ids.ids[0]
                    else:
                        self.pickup_date = self.delivery_date = self.pickup_time_slot = self.delivery_time_slot = False
                        return {
                            'warning': {'title': 'Warning',
                                        'message': 'You can not use this service for today at this time.'},
                        }

            # Avoid the case in which the Delivery Date is furthest from the Pickup Date
            # according to the Service selected for existing Intermediate holidays.
            delivery_date = self._get_valid_date(pickup_date + timedelta(days=1))
            res['domain']['pickup_time_slot'] = [('id', 'in', self.service_id.pickup_time_slot_ids.ids)]
            res['domain']['delivery_time_slot'] = [('id', 'in', self.service_id.delivery_time_slot_ids.ids)]
        self.pickup_date = pickup_date or False
        self.delivery_date = delivery_date or False
        self.pickup_time_slot = pickup_time_slot_id or False
        self.delivery_time_slot = delivery_time_slot_id or False
        return res

    @api.onchange('pickup_date')
    def _set_delivery_date(self):
        if self.pickup_date:
            if not self.service_id:
                self.pickup_date = False
                return {
                    'warning': {'title': 'Warning', 'message': 'You must first select the Service.'},
                }
            available_delivery_date_range = [1 if int(x) > 1 else int(x) for x in
                                             self.service_id.available_delivery_date_range.split(',')]
            pickup_date = datetime.strptime(self.pickup_date, DEFAULT_SERVER_DATE_FORMAT)
            self.delivery_date = self._get_valid_date(pickup_date + timedelta(days=available_delivery_date_range[0]))

    @api.constrains('pickup_date', 'delivery_date')
    def _validate_dates(self):
        if self.carrier_id.name == 'Roadbulls':
            pickup_date = datetime.strptime(self.pickup_date, DEFAULT_SERVER_DATE_FORMAT).date()
            delivery_date = datetime.strptime(self.delivery_date, DEFAULT_SERVER_DATE_FORMAT).date()
            available_pickup_date_range = [int(x) for x in self.service_id.available_pickup_date_range.split(',')]
            tz = pytz.timezone('Asia/Singapore')
            valid_date = self._get_valid_date(datetime.now(tz).date())
            if valid_date == datetime.now(tz).date() and datetime.now(tz).time() >= time(15):
                valid_date = self._get_valid_date(valid_date + timedelta(days=1))
            available_delivery_date_range = [int(x) for x in self.service_id.available_delivery_date_range.split(',')]
            delivery_valid_date = self._get_valid_date(valid_date + timedelta(days=available_delivery_date_range[0]))
            while delivery_valid_date > valid_date + timedelta(days=available_delivery_date_range[0]):
                valid_date = delivery_valid_date
                delivery_valid_date = self._get_valid_date(
                    valid_date + timedelta(days=available_delivery_date_range[0]))

            # Case in which the Pickup Date is less than the Valid Date
            if pickup_date < valid_date:
                raise exceptions.ValidationError(
                    "Pickup Date must be at least %s." % valid_date)

            # Case in which the Pickup Date is greater than the Valid Date as permitted by the Service.
            if pickup_date > self._get_valid_date(valid_date + timedelta(days=available_pickup_date_range[1])):
                raise exceptions.ValidationError("Pickup Date should be at most %s." % self._get_valid_date(
                    valid_date + timedelta(days=available_pickup_date_range[1])))

            # Case in which the Delivery Date is less than the Pickup Date as permitted by the Service.
            if delivery_date < pickup_date + timedelta(available_delivery_date_range[0]):
                raise exceptions.ValidationError(
                    "The Delivery Date must be greater than %s day(s) or %s day(s) than the Pickup Date." %
                    (available_delivery_date_range[0], available_delivery_date_range[1]))

            # Case in which the Delivery Date is greater than the Pickup Date as permitted by the Service.
            if delivery_date > pickup_date + timedelta(days=available_delivery_date_range[1]):
                raise exceptions.ValidationError("Delivery Date should be at most %s." % self._get_valid_date(
                    pickup_date + timedelta(days=available_delivery_date_range[1])))

            if pickup_date.isoweekday() in (6, 7):
                raise exceptions.ValidationError(
                    "Pickup Date can´t be a Saturday or Sunday.\nThe next Day to pick up would be %s." % self._get_valid_date(
                        available_delivery_date_range[0]))
            if delivery_date.isoweekday() in (6, 7):
                raise exceptions.ValidationError(
                    "Delivery Date can´t be a Saturday or Sunday.\nThe next Day to pick up would be %s." % self._get_valid_date(
                        available_delivery_date_range[0]))
            if self.is_a_holyday(self.pickup_date):
                raise exceptions.ValidationError(
                    "Pickup Date can´t be a Holiday.\nThe next Day to pick up would be %s." % self._get_valid_date(
                        available_delivery_date_range[0]))
            if self.is_a_hollyday(self.delivery_date):
                raise exceptions.ValidationError(
                    "Delivery Date can´t be a Holiday.\nThe next Day to pick up would be %s." % self._get_valid_date(
                        available_delivery_date_range[0]))

    @api.constrains('pickup_time_slot')
    def _validate_pickup_time_slot(self):
        if self.carrier_id.name == 'Roadbull':
            pickup_date = datetime.strptime(self.pickup_date, DEFAULT_SERVER_DATE_FORMAT).date()
            tz = pytz.timezone('Asia/Singapore')
            if datetime.now(tz).date() == pickup_date:
                if datetime.now(tz).time() >= time(15) and self.pickup_time_slot.timeoption_id != 27:
                    valid_pickup_time_slot = self.env['roadbull.timeoption'].search(
                        [('timeoption_id', '=', self.pickup_time_slot.timeoption_id)], limit=1)
                    raise exceptions.ValidationError(
                        "Pick up Date must be '%s' after 3:00 PM." % valid_pickup_time_slot.name)
                elif datetime.now(tz).time() < time(15) and self.pickup_time_slot.timeoption_id != 26:
                    valid_pickup_time_slot = self.env['roadbull.timeoption'].search(
                        [('timeoption_id', '=', self.pickup_time_slot.timeoption_id)], limit=1)
                    raise exceptions.ValidationError(
                        "Pick up Date must be '%s' before 3:00 PM." % valid_pickup_time_slot.name)

    def _check_mandatory_values(self, address, field_name):
        error_message = ""
        street = address.street if address.street else address.parent_id.street if address.parent_id else False
        if not street:
            error_message += "%s it has no value for the 'street' field." % field_name
        zip_code = address.zip if address.zip else address.parent_id.zip if address.parent_id else False
        if not zip_code:
            error_message += "\n" if error_message else error_message
            error_message += "%s it has no value for the 'zip' field." % field_name
        contact_phone = address.mobile if address.mobile else address.parent_id.mobile if address.parent_id and address.parent_id.mobile else address.phone if address.phone else address.parent_id.phone if address.parent_id and address.parent_id.phone else False
        if not contact_phone:
            error_message += "\n" if error_message else error_message
            error_message += "%s it has no value for the 'mobile' or 'phone' field." % field_name
        if error_message:
            raise exceptions.ValidationError(error_message)

    def _get_valid_date(self, valid_date):
        while self.is_a_holyday(valid_date) or valid_date.isoweekday() in (6, 7):
            valid_date += timedelta(days=1)
        return valid_date

    def is_a_holyday(self, my_date):
        holydays = self.env['calendar.event'].search(
            [('allday', '=', 1), ('categ_ids.name', '=', 'Public Holiday'), ('privacy', '=', 'public'), '|',
             ('start_date', '<', my_date),
             ('start_date', '=', my_date), '|', ('stop_date', '>', my_date), ('stop_date', '=', my_date)])
        return len(holydays) > 0

    def _get_quantity(self):
        quantity = 0
        for line in self.move_lines:
            quantity += line.quantity_done if line.quantity_done else line.product_uom_qty
        return quantity

    def _get_delivery_time(self):
        from_time = datetime.strptime(self.delivery_time_slot.from_time, DEFAULT_SERVER_DATETIME_FORMAT).strftime(
            "%H%p")
        to_time = datetime.strptime(self.delivery_time_slot.to_time, DEFAULT_SERVER_DATETIME_FORMAT).strftime("%H%p")
        return from_time + ' - ' + to_time

    def _get_mobile_phone(self):
        mobile_phone = self.partner_id.mobile if self.partner_id.mobile else self.partner_id.phone
        if not mobile_phone and self.partner_id.parent_id:
            mobile_phone = self.partner_id.parent_id.mobile if self.partner_id.parent_id.mobile else self.partner_id.parent_id.phone
        return mobile_phone or ""

    def button_validate(self):
        cenit_api = self.env['cenit.api']
        for pick in self:
            for move_line in pick.move_lines:
                # Validate only if the Warehouse is 'ANC' and the Delivery type 'Roadbull'
                # and there is at least a defined amount
                if pick.picking_type_id.warehouse_id.code == 'ANC' and pick.carrier_id.name == 'Roadbull' and move_line.product_uom_qty > 0:
                    pick._validate_dates()
                    pick._validate_pickup_time_slot()
                    pick._check_mandatory_values(pick.partner_id, 'Shipping Address')
                    pick._check_mandatory_values(pick.picking_type_id.warehouse_id.partner_id, 'Warehouse Address')
                    result = cenit_api.get('/anchanto/product_stock', {'sku': move_line.product_id.barcode})
                    if result['count'] == 0 or result['product_stocks'][0]['quantity'] < move_line.product_qty:
                        raise exceptions.Warning('Insufficient qty in warehouse')
                    if pick.error_message is False and pick.carrier_tracking_ref is False:
                        for mapping in pick.env['cenit.data_type'].search([('name', 'in', (
                                'Create Delivery Order as Anchanto Order', 'Create Delivery Order as Roadbull Order'))],
                                                                          order="name"):
                            mapping.trigger_flows(pick)
                        error_message = carrier_tracking_ref = False
                        num_retries = 1
                        max_retries = 10
                        write_date = pick.write_date
                        from odoo.modules.registry import Registry
                        from odoo.api import Environment
                        from odoo import SUPERUSER_ID
                        db_name = self.pool.db_name
                        registry = Registry(db_name)
                        while error_message is False and carrier_tracking_ref is False and num_retries <= max_retries:
                            basic_time.sleep(num_retries * 2)
                            with registry.cursor() as cr:
                                env = Environment(cr, SUPERUSER_ID, {})
                                do = env['stock.picking'].search([('id', '=', pick.id)])
                                error_message = do.error_message if do.write_date > write_date else False
                                write_date = do.write_date
                                carrier_tracking_ref = do.carrier_tracking_ref
                                num_retries += 1
                        if error_message:
                            raise exceptions.ValidationError(error_message)
                        elif num_retries > max_retries and carrier_tracking_ref is False:
                            raise exceptions.ValidationError(
                                "The maximum number of attempts is reached to obtain a response from Roadbull and/or Anchanto.")
        return super(RoadbullOrder, self).button_validate()


class ProviderRoadbull(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('roadbull', "Roadbull")])
    shipping_enabled = fields.Boolean(string="Shipping enabled", default=False,
                                      help="Uncheck this box to disable package shipping while validating Delivery Orders")

    def roadbull_get_shipping_price_from_so(self, orders):
        return [0]  # TODO Implement the quote of a shipment in Roadbull from the Sales Order

    def roadbull_get_tracking_link(self, picking):
        return 'https://sandcds.roadbull.com/order/track/%s' % picking.carrier_tracking_ref

