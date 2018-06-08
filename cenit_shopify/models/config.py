# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010, 2014 Tiny SPRL (<http://tiny.be>).
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

import logging

from odoo import models, api

_logger = logging.getLogger(__name__)

COLLECTION_NAME = "shopify_odoo"
COLLECTION_VERSION = "1.0.0"
COLLECTION_PARAMS = {
    # WITHOUT COLLECTION_PARAMS.
}


class CenitIntegrationSettings(models.TransientModel):
    _name = "cenit.shopify.settings"
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
        return installer.install_collection({'id': collection_id})
        # self.update_connection_role(cr, uid, context)
        # self.update_connection(cr, uid, context)

    def update_connection(self, cr, uid, context):
        conn_pool = self.pool.get("cenit.connection")
        conn_id = conn_pool.search(cr, uid, [('name', '=', 'My Odoo host')])
        conn = conn_pool.browse(cr, uid, conn_id[0], context) if conn_id else None
        if conn:
            conn_data = {
                "_reference": "True",
                "_primary": ["namespace", "name"],
                "namespace": conn.namespace.id,
                "name": "My Odoo host",
                "headers": [{
                    "key": "X_USER_ACCESS_KEY",
                    "value": conn.key
                },
                    {
                        "key": "X_USER_ACCESS_TOKEN",
                        "value": conn.token
                    },
                    {
                        "key": "TENANT_DB",
                        "value": cr.dbname
                    }
                ]

            }
            conn_pool.post(cr, uid, "/setup/connection", conn_data)

    def update_connection_role(self, cr, uid, context):
        role_pool = self.pool.get("cenit.connection.role")
        conn_rol = role_pool.get(cr, uid, "/setup/connection_role", {'name': 'My Odoo role'})
        if conn_rol:
            if len(conn_rol["connection_role"]) > 0:
                conn_rol = conn_rol["connection_role"][0]
                webhook = {
                    "_reference": "True",
                    "namespace": "Odoo",
                    "name": "Send order"
                }
                conn_rol["webhooks"].append(webhook)
                role_pool.post(cr, uid, "/setup/connection_role", conn_rol)
