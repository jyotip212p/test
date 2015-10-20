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

from openerp.osv import fields, osv
import datetime
from datetime import datetime
import time
from datetime import timedelta,date
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

class sales_forecast_reject_reason(osv.osv):

    _name = "sales.forecast.reject.reason"
    _description = "Sales Forecast Reject Reason"

    _columns = {
        'name': fields.text('Reason'),
        'date': fields.date('Date'),
        'forecast_id':fields.many2one('outlet.sales.forecast', 'Forecast'),
    }
    _defaults ={
        'date':lambda *a: time.strftime('%Y-%m-%d'),
    }
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        if context.has_key('forecast_id') and len(context['forecast_id']):
            vals['forecast_id'] = context['forecast_id'][0] 
        retvals = super(sales_forecast_reject_reason, self).create(cr, uid, vals, context=context)
        return retvals
    
    def call_reject_forecast(self, cr, uid, ids, context=None):
        return self.pool.get('outlet.sales.forecast').reject_sale_forecast(cr, uid, context['forecast_id'], context['reason'], context=context)

sales_forecast_reject_reason()
