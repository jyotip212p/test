from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.osv import osv, fields
from lxml import etree
from openerp.tools.translate import _
import openerp.tools
#import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
import werkzeug

from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug
        
class sales_forecast(osv.osv):
    _description="Sales forecast"
    _name = 'sales.forecast'
    _inherit = ['mail.thread','ir.needaction_mixin']
    _order = 'id desc'
         
    
    def _check_from_to_date(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        obj = self.browse(cr, uid, ids[0])
        if obj.from_date and obj.to_date:
            if (datetime.strptime(obj.to_date, '%Y-%m-%d')-datetime.strptime(obj.from_date, '%Y-%m-%d')).days < 0:
                return False
        return True  
        
    def _check_forecast_exists(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        obj = self.browse(cr, uid, ids[0])
        sear_ids  = self.search(cr, uid, [('sector_id','=',obj.sector_id.id), ('from_date','=',obj.from_date), ('to_date','=',obj.to_date), ('id','!=',obj.id)])
        print 'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL',sear_ids, obj.sector_id.id,obj.from_date,obj.to_date
        if len(sear_ids):
            return False
        return True          
    
    def onchange_sector(self, cr, uid, ids, sector_id, context=None):
        #sectids = self.pool.get('sale.sector').search(cr, uid, [('manager_id','=',uid)])
        shopids = self.pool.get('sale.shop').search(cr, uid, [('sector_id','=',sector_id)])
        val = []
        vals = {}
        for shop in self.pool.get('sale.shop').browse(cr, uid, shopids):
            val.append((0,0,{'name':shop.id,'flg_sent_reminder':False}))        
        vals['remind_outlet_forecast_submit_ids'] = val  
        return {'value':vals}
        
    def _get_to_validate_lines(self, cr, uid, ids, fields, args, context=None):
        line_obj = self.pool.get('outlet.sales.forecast')
        res = {}
        for script in self.browse(cr, uid, ids):
	    args = [('shop_id.sector_id', '=', script.sector_id.id),('state', '=', 'wait_validate'),('from_date','=',script.from_date),('to_date','=',script.to_date)]
	    line_ids = line_obj.search(cr, uid, args)
	    res[script.id] = line_ids
	return res

    def _set_to_validate_lines(self, cr, uid, id, name, value, inv_arg, context):
	line_obj = self.pool.get('outlet.sales.forecast')
	for line in value:
	    if line[0] == 1: # one2many Update
		line_id = line[1]
		line_obj.write(cr, uid, [line_id], line[2])
	return True
        
    def _get_to_approve_lines(self, cr, uid, ids, fields, args, context=None):
        line_obj = self.pool.get('outlet.sales.forecast')
        res = {}
        for script in self.browse(cr, uid, ids):
	    args = [('shop_id.sector_id', '=', script.sector_id.id),('state', '=', 'wait_approve'),('from_date','=',script.from_date),('to_date','=',script.to_date)]
	    line_ids = line_obj.search(cr, uid, args)
	    res[script.id] = line_ids
	return res

    def _set_to_approve_lines(self, cr, uid, id, name, value, inv_arg, context):
	line_obj = self.pool.get('outlet.sales.forecast')
	for line in value:
	    if line[0] == 1: # one2many Update
		line_id = line[1]
		line_obj.write(cr, uid, [line_id], line[2])
	return True
        
    def _get_reject_lines(self, cr, uid, ids, fields, args, context=None):
        line_obj = self.pool.get('outlet.sales.forecast')
        res = {}
        for script in self.browse(cr, uid, ids):
	    args = [('shop_id.sector_id', '=', script.sector_id.id),('state', '=', 'reject'),('from_date','=',script.from_date),('to_date','=',script.to_date)]
	    line_ids = line_obj.search(cr, uid, args)
	    res[script.id] = line_ids
	return res

    def _set_reject_lines(self, cr, uid, id, name, value, inv_arg, context):
	line_obj = self.pool.get('outlet.sales.forecast')
	for line in value:
	    if line[0] == 1: # one2many Update
		line_id = line[1]
		line_obj.write(cr, uid, [line_id], line[2])
	return True
        
    def _get_approved_lines(self, cr, uid, ids, fields, args, context=None):
        line_obj = self.pool.get('outlet.sales.forecast')
        res = {}
        for script in self.browse(cr, uid, ids):
	    args = [('shop_id.sector_id', '=', script.sector_id.id),('state', '=', 'done'),('from_date','=',script.from_date),('to_date','=',script.to_date)]
	    line_ids = line_obj.search(cr, uid, args)
	    res[script.id] = line_ids
	return res

    def _set_approved_lines(self, cr, uid, id, name, value, inv_arg, context):
	line_obj = self.pool.get('outlet.sales.forecast')
	for line in value:
	    if line[0] == 1: # one2many Update
		line_id = line[1]
		line_obj.write(cr, uid, [line_id], line[2])
	return True
        
    _columns = {
        'name': fields.char('Forecast Number', size=64, required=False, readonly=False, select=True, track_visibility='always'),
        'sector_id':fields.many2one('sale.sector','Sector', track_visibility='always'),
        'from_date': fields.date('From Date', track_visibility='always'),
        'to_date':fields.date('To Date', track_visibility='always'),
        'state':fields.selection([('new','New'), ('done','Submitted')],'State', track_visibility='onchange'),
        'remind_outlet_forecast_submit_ids':fields.one2many('remind.outlet.forecast.submit','forecast_id','Remind Outlets for Sales Forecast', copy=True),
        #'outlet_sales_forecast_ids':fields.one2many('outlet.sales.forecast','forecast_id','Outlet Sales Forecast'),
        'outlet_sales_forecast_validate_ids':fields.function(_get_to_validate_lines, fnct_inv=_set_to_validate_lines, string='Outlet Sales Forecast', relation="outlet.sales.forecast", method=True, type="one2many"),
        'outlet_sales_forecast_approve_ids':fields.function(_get_to_approve_lines, fnct_inv=_set_to_approve_lines, string='Outlet Sales Forecast', relation="outlet.sales.forecast", method=True, type="one2many"),
        'outlet_sales_forecast_reject_ids':fields.function(_get_reject_lines, fnct_inv=_set_reject_lines, string='Outlet Sales Forecast', relation="outlet.sales.forecast", method=True, type="one2many"),
        'outlet_sales_forecast_approved_ids':fields.function(_get_approved_lines, fnct_inv=_set_approved_lines, string='Outlet Sales Forecast', relation="outlet.sales.forecast", method=True, type="one2many"),
    }
    _defaults = {
    	'state':'new',
    	'name': lambda obj, cr, uid, context: '/',
    }
    _constraints = [
        #(_check_from_to_date, 'Error! To Date Should be Greater Than/Equal to From Date!', ['to_date']),
        (_check_forecast_exists, 'Error! For this Sector and for this Period Sales Forecast Already Exists!', ['sector_id','from_date','to_date'])
        ]
        
    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'sales.forecast') or '/'
        retvals = super(sales_forecast, self).create(cr, uid, vals, context=context)
        return retvals              
        
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}        
        default.update({
            'state':'new',
            'name':'/'
        })
        retval = super(sales_forecast, self).copy(cr, uid, id, default, context)
        return retval
        
    def onchange_from_date(self, cr, uid, ids, from_date, to_date, context=None):
        val = {}
        if from_date and to_date and (datetime.strptime(to_date, '%Y-%m-%d')-datetime.strptime(from_date, '%Y-%m-%d')).days < 0:
            raise osv.except_osv(_('Error'),_('From Date Should be Less than/Equal to To Date'))
        
        return {'value':val}
        
    def onchange_to_date(self, cr, uid, ids, from_date, to_date, context=None):
        val = {}
        if from_date and to_date and (datetime.strptime(to_date, '%Y-%m-%d')-datetime.strptime(from_date, '%Y-%m-%d')).days < 0:
            raise osv.except_osv(_('Error'),_('To Date Should be Greater than/Equal to From Date'))
        
        return {'value':val}
        
    def remind_sale_forecast_submission(self, cr, uid, ids, context=None):
        for forecast in self.browse(cr, uid, ids, context=context):
            for shop in forecast.remind_outlet_forecast_submit_ids:
                outlet = shop.name.id
                manager = shop.name.manager_id.id
                #Check Outlet Forecast Already Submitted by that Shop or not
                outforeids = self.pool.get('outlet.sales.forecast').search(cr, uid, [('shop_id','=',outlet), ('from_date','=',forecast.from_date), ('to_date','=',forecast.to_date)], context=context)
                if not len(outforeids):
                    #Send Notification
                    if shop.name.manager_id.partner_id.email:
                        user = self.pool.get('res.users').browse(cr, uid, uid)
                        post_values = {
                                   'email_from': user.partner_id.email or False,  
                                   'partner_ids': [shop.name.manager_id.partner_id.id],
                                   'subject':'Submit Sales Forecast of ' +shop.name.name + ' for the Period ' + datetime.strptime(shop.forecast_id.from_date, '%Y-%m-%d').strftime('%d/%m/%Y') + ' - ' + datetime.strptime(shop.forecast_id.to_date, '%Y-%m-%d').strftime('%d/%m/%Y'),
                                   'body':'Hello ' + shop.name.manager_id.partner_id.name + ',\nPlease Submit the Sales Forecast of "' + shop.name.name + '" Outlet for the Period "' + datetime.strptime(shop.forecast_id.from_date, '%Y-%m-%d').strftime('%d/%m/%Y') + ' - ' + datetime.strptime(shop.forecast_id.to_date, '%Y-%m-%d').strftime('%d/%m/%Y') +' ".',
                                }
                        print '@@@@@@@@@@@@@@@@@@@@',post_values          
                        msg_id = self.message_post(cr, uid,[forecast.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
                    #Send a Mail
                    mail_temp_id = self.pool.get('email.template').search(cr, uid, [('name','=','Remind Outlets to Submit Sales Forecast')])
                    temp_obj = self.pool.get('email.template').browse(cr, uid, mail_temp_id[0])            
                    if shop.name.manager_id.partner_id.email:
                        mail_id = self.pool.get('email.template').send_mail(cr, uid, temp_obj.id, shop.id, force_send=True, context=context)
            
        return True
        
    def validate_all_outlets_sales_forecast(self, cr, uid, ids, context=None):
        #Check for All the Outlets Submitted the Sales Forecast and then Validate All
        outlet_obj = self.pool.get('outlet.sales.forecast')        
        for forecast in self.browse(cr, uid, ids, context=context):
            for shop in forecast.remind_outlet_forecast_submit_ids:
                args = [('shop_id', '=', shop.name.id),('state','in', ('wait_validate','wait_approve','done')),('from_date','=', forecast.from_date),('to_date', '=', forecast.to_date)]
                sear_ids = outlet_obj.search(cr, uid, args)
                if not len(sear_ids):
                    raise osv.except_osv(_('Error'),_('Sales Forecast is Not Submitted by All the Outlets.'))
                args = [('shop_id', '=', shop.name.id),('state','=', 'wait_validate'),('from_date','=', forecast.from_date),('to_date', '=', forecast.to_date)]
                sear_ids = outlet_obj.search(cr, uid, args)    
                outlet_obj.validate_forecast(cr, uid, sear_ids, context=context)    
        return True
        
    def approve_all_outlets_sales_forecast(self, cr, uid, ids, context=None):
        #Check for All the Outlets Submitted the Sales Forecast and then Approve All
        outlet_obj = self.pool.get('outlet.sales.forecast')        
        for forecast in self.browse(cr, uid, ids, context=context):
            for shop in forecast.remind_outlet_forecast_submit_ids:
                args = [('shop_id', '=', shop.name.id),('state','in', ('wait_approve','done')),('from_date','=', forecast.from_date),('to_date', '=', forecast.to_date)]
                sear_ids = outlet_obj.search(cr, uid, args)
                if not len(sear_ids):
                    raise osv.except_osv(_('Error'),_('Sales Forecast is Not Submitted by All the Outlets or few Forecasts Still Waiting to Validate.'))
                args = [('shop_id', '=', shop.name.id),('state','=', 'wait_approve'),('from_date','=', forecast.from_date),('to_date', '=', forecast.to_date)]
                sear_ids = outlet_obj.search(cr, uid, args)
                outlet_obj.approve_forecast(cr, uid, sear_ids, context=context)    
        return True
     
        
sales_forecast()

class remind_outlet_forecast_submit(osv.osv):
    _name = 'remind.outlet.forecast.submit'
    _description='Remind Outlets for Sales Forecast Submission'
    _columns ={
        'forecast_id':fields.many2one('sales.forecast','Forecast'),
        'name':fields.many2one('sale.shop','Outlet'),
        'flg_sent_reminder':fields.boolean('Reminder Sent?'),
    }
    _defaults={
        'flg_sent_reminder':False,
    }
remind_outlet_forecast_submit()


