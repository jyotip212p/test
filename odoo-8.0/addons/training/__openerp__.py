# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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


{
    'name': 'Module for Training Employees',
    'version': '1.0',
    'category': 'Customized integration',
    'author': 'Credativ Software (I) Pvt. Ltd.',
    'website': 'http://www.credativ.in',
    'description': """
ERP for Somtel.
===================================================

Includes:
1. Training

    """,
    'depends': ['base','account','account_accountant','sale','purchase', 'stock','sale_stock','hr','hr_contract', 'hr_holidays', 'hr_payroll','hr_expense','hr_recruitment','hr_evaluation','multi_company','document'],
    'data': [
           'training_view.xml',
           'hr_skill_view.xml',
    ],
    'demo': [
             ],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
