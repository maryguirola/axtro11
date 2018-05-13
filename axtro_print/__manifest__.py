# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Print-outs and views JMD",
    "version": "11.01",
    "author": "Elico Solutions Pte Ltd",
    "category": "Tools",
    "description": """
Custom Print outs for JMD
------------------------------------
""",
    "depends": ['account', 'sale', 'stock', 'axtro_custom'],
    "data": [
        "print/layouts.xml",
        "print/report_invoice_jmd.xml",
        # "print/report_saleorder_jmd.xml",
        # "print/report_deliveryslip_jmd.xml",
        # "print/report_stockpicking_operations_jmd.xml",
        # "print/report_purchase_jmd.xml",
        # "print/report_payment_receipt.xml",
    ],
    "demo": [],
    "installable": False,
}