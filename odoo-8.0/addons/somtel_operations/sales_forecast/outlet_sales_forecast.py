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
        
class outlet_sales_forecast(osv.osv):
    _description="Sales forecast of a Shop"
    _name = 'outlet.sales.forecast'
    _inherit = ['mail.thread','ir.needaction_mixin']
    _order = 'id desc'
    
    def _get_shop_id(self, cr, uid, context=None):
        retids = self.pool.get('sale.shop').search(cr, uid, [('manager_id','=',uid)])
        return retids and retids[0] or False        
    
    def _check_from_to_date(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        obj = self.browse(cr, uid, ids[0])
        if obj.from_date and obj.to_date:
            if (datetime.strptime(obj.to_date, '%Y-%m-%d')-datetime.strptime(obj.from_date, '%Y-%m-%d')).days < 0:
                return False
        return True
    
    def _get_total_quantity(self, cr, uid, ids, field, arg, context=None):
        res = {}
        for obj in self.browse(cr,uid,ids,context=context):
            total = 0.00
            for line in obj.forecast_lines:
                total+=line.quantity
            res[obj.id] = total
        print '******************************TOTAL Quantity*************************', res
        return res
    
    def _get_total_amount(self, cr, uid, ids, field, arg, context=None):
        res = {}
        for obj in self.browse(cr,uid,ids,context=context):
            total = 0.00
            for line in obj.forecast_lines:
                total+=line.total_price
            res[obj.id] = total
        print '******************************TOTAL AMOUNT*************************', res
        return res
    
#    def _get_sales_orders_data(self, cr, uid, ids, field, arg, context=None):
#        obj = self.pool[sale.order]
#        selfobj = self.browse(cr,uid,ids,context=context)
#        res = {}
#        for id in ids:
#            res[id] = {}
#            actual_domain = [('shop_id', '=', selfobj.shop_id.id), ('state', '=', 'done'), ('date_order', '>=', selfobj.from_date), ('date_order', '<=', selfobj.to_date)]
#            res[id]['actual_sale_orders'] = json.dumps(self.__get_bar_values(cr, uid, obj, actual_domain, ['amount_total', 'date_order'], 'amount_total', 'date_order', context=context))
#        return res
    
    def _get_sales_orders_data(self, cr, uid, ids, field, arg, context=None):
        res = {}     
   
        for selfobj in self.browse(cr,uid,ids,context=context):
            total_qty = 0.0
            total_amt = 0.0
#            forecast_lines = list(set([x.name.id for x in selfobj.forecast_lines]))
#            print 'DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDd', selfobj.from_date, forecast_lines
            search_ids = self.pool.get('sale.order').search(cr,uid,[('shop_id', '=', selfobj.shop_id.id), ('state', '=', 'done'), ('date_order', '>=', selfobj.from_date), ('date_order', '<=', selfobj.to_date)])
            print 'SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS', search_ids
            for obj in self.pool.get('sale.order').browse(cr,uid,search_ids,context=context):
                order_lines = list(set([x.product_id.id for x in obj.order_line]))
                for i in selfobj.forecast_lines:
                    for j in obj.order_line:
                        if i.name.id==j.product_id.id:
                            total_qty += j.product_uom_qty
                            total_amt += j.price_subtotal
            print 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF', total_qty, total_amt
#                        if (forecast_lines==order_lines):
#                            total_qty += obj.total_prod_quantity
#                            total_amt += obj.amount_total
            for id in ids:
                res[id] = {}
                res[selfobj.id]['actual_sales_quantity'] = total_qty
                res[selfobj.id]['actual_sales_amount'] = total_amt
        return res
        
    _columns = {
        'name': fields.char('Forecast Number', size=64, required=False, readonly=False, select=True, track_visibility='always'),
        'shop_id':fields.many2one('sale.shop','Shop', track_visibility='always'),
        'from_date': fields.date('From Date', track_visibility='always'),
        'to_date':fields.date('To Date', track_visibility='always'),
        'validated_by':fields.many2one('res.users','Validated By', track_visibility='onchange'),
        'approved_by':fields.many2one('res.users','Approved By', track_visibility='onchange'),
        'reject_reason':fields.text('Reason'),
        'state':fields.selection([('new','Draft'), ('wait_validate','Waiting for Validation'), ('wait_approve','Waiting for Approval'), ('done','Completed'), ('reject','Rejected'),('cancel','Cancelled')],'State', track_visibility='always'),
        'forecast_lines':fields.one2many('outlet.sales.forecast.line','forecast_id','Forecast Product Lines', copy=True),
        'comment':fields.text('Comment'),
        #'forecast_id':fields.many2one('sales.forecast','Sales Forecast'),
        'total_quantity':fields.function(_get_total_quantity, type='integer',readonly=True, string="Total Quantity of Products"),
        'total_amount':fields.function(_get_total_amount, type='float',readonly=True, string="Total Amount of Products"),
        'color': fields.integer('Color'),
        'actual_sales_quantity':fields.function(_get_sales_orders_data, type='float', readonly=True, multi='_get_sales_orders_data', string="Actual Sales Quantity"),
        'actual_sales_amount':fields.function(_get_sales_orders_data, type='float', readonly=True, multi='_get_sales_orders_data', string="Actual Sales Amount")
    }
    
    _defaults = {
    	'state':'new',
    	'name': lambda obj, cr, uid, context: '/',
    	'shop_id':_get_shop_id
    }
    _constraints = [
        (_check_from_to_date, 'Error! To Date Should be Greater Than/Equal to From Date!', ['To Date'])
        ]
        
    def _needaction_domain_get(self, cr, uid, context=None):
        forecast_obj = self.pool.get('outlet.sales.forecast')
        if self.pool.get('res.users').has_group(cr, uid, 'somtel_operations.group_retail_sale_outlet'):
            dom = [('state', '=', 'new')]
        if self.pool.get('res.users').has_group(cr, uid, 'somtel_operations.group_retail_sale_sector'):
            dom = [('state', '=', 'wait_validate')]
        if self.pool.get('res.users').has_group(cr, uid, 'base.group_sale_manager'):
            dom = [('state', '=', 'wait_approve')]
        return dom
    
    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'outlet.sales.forecast') or '/'
        if vals.has_key('forecast_id') and vals['forecast_id']:
            line_obj = self.pool.get('sales.forecast').browse(cr, uid, vals['forecast_id'])
            vals['from_date'] = line_obj.from_date
            vals['to_date'] = line_obj.to_date
        retvals = super(outlet_sales_forecast, self).create(cr, uid, vals, context=context)
        return retvals        
        
    def unlink(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state != 'new':
                raise osv.except_osv(_('Error'),_('You Can\'t delete the Processed Sales Forecast.'))
                return False
        return super(outlet_sales_forecast, self).unlink(cr, uid, ids, context=context)        
        
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}        
        default.update({
            'state':'new',
            'name':'/'
        })
        retval = super(outlet_sales_forecast, self).copy(cr, uid, id, default, context)
        return retval
        
    def onchange_main_forecast(self, cr, uid, ids, forecast_id, context=None):
        val = {}
        forecast = self.pool.get('sales.forecast').browse(cr, uid, forecast_id)
        val['from_date'] = forecast.from_date
        val['to_date'] = forecast.to_date
        return {'value':val}
        
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
        
    def send_for_validate(self, cr, uid, ids, context=None):
        try:
            dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'somtel_operations', 'wizard_sales_forecast_send_for_validate_id')
        except ValueError, e:
            view_id = False
        return {
            'name':_("Update and Send for Validate"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'sales.forecast.send.for.validate',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'forecast_id': ids
            }
        }
        
    def send_to_validate(self, cr, uid, ids, comment,context=None):
        if not context:
            context = {}
        for forecast in self.browse(cr, uid, ids, context=context):
            forecast.write({'approved_by':uid, 'state':'wait_validate', 'comment':comment})
        return True       
        
    def submit_forecast(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for forecast in self.browse(cr, uid, ids, context=context):
            forecast.write({'state':'wait_validate'})
            if len(forecast.forecast_lines)<=0:
                raise osv.except_osv(_('Error!'),_('No Forecast Lines To Submit the Sales Forecast!'))
            # send the email            
            composer_values = {}
            email_ctx = context
            partner_ids = []
            user = self.pool.get('res.users').browse(cr, uid, uid)
            partner_ids.append(forecast.shop_id.sector_id.manager_id.partner_id.id)
            if forecast:
                
                post_values = {
                                   'email_from': user.partner_id.email or False,  
                                   'partner_ids': partner_ids,
                                   'subject':forecast.name + ' Forecast is Waiting for Validation',
                                   'body':forecast.name + ' Forecast is Waiting for Validation created for the shop ' + forecast.shop_id.name + ' by ' + user.name + ' For the Period ' + datetime.strptime(forecast.from_date, '%Y-%m-%d').strftime('%d/%m/%Y') + ' - ' + datetime.strptime(forecast.to_date, '%Y-%m-%d').strftime('%d/%m/%Y') + '.',
                                }  
                msg_id = self.message_post(cr, uid,[forecast.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
        return True
        
    def validate_forecast(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for forecast in self.browse(cr, uid, ids, context=context):
            forecast.write({'validated_by':uid, 'state':'wait_approve'})
        return True
        
    def approve_forecast(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for forecast in self.browse(cr, uid, ids, context=context):
            forecast.write({'approved_by':uid, 'state':'done'})
            user = self.pool.get('res.users').browse(cr, uid, uid)
            post_values = {
                                   'email_from': user.partner_id.email or False,
                                   'partner_ids': [forecast.shop_id.manager_id.partner_id.id],
                                   'subject':forecast.name + ' Forecast Approval',
                                   'body':forecast.name + ' Forecast gets Approved by '+user.partner_id.name+'.',
                                }  
            msg_id = self.message_post(cr, uid,[forecast.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
                
        return True 
        
    def reject_forecast(self, cr, uid, ids, context=None):
        try:
            dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'somtel_operations', 'wizard_sales_forecast_reject_reason_id')
        except ValueError, e:
            view_id = False
        return {
            'name':_("Reject Forecast"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'sales.forecast.reject.reason',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'forecast_id': ids
            }
        }
        
    def reject_sale_forecast(self, cr, uid, ids, reason, context=None):
        for obj in self.browse(cr, uid, ids):
            if obj.state == 'wait_validate':
                obj.write({'validated_by':uid, 'reject_reason':reason,'state':'reject'})
                #Notify the Outlet manager
                composer_values = {}
                email_ctx = context
                partner_ids = []
                user = self.pool.get('res.users').browse(cr, uid, uid)
                partner_ids.append(obj.shop_id.manager_id.partner_id.id)
                post_values = {
                                   'email_from': obj.shop_id.sector_id.manager_id.partner_id.email,
                                   'partner_ids': partner_ids,
                                   'subject':obj.name + ' Forecast Rejection',
                                   'body':obj.name + ' Forecast is Rejected for the following Reason : "' + reason + '".',
                                }  
                msg_id = self.message_post(cr, uid,[obj.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
                
            elif obj.state == 'wait_approve':
                obj.write({'approved_by':uid, 'reject_reason':reason,'state':'reject'})
        return True
        
    def cancel_forecast(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for forecast in self.browse(cr, uid, ids, context=context):
            forecast.write({'validated_by':uid, 'state':'cancel'})
        return True
        
    def reset_to_draft_forecast(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for forecast in self.browse(cr, uid, ids, context=context):
            forecast.write({'state':'new'})
        return True          
        
    def validate_outlet_sale_forecast(self, cr, uid, ids, context=None):
        self.validate_forecast(cr, uid, ids, context=context)
        return True 
        
    def approve_outlet_sale_forecast(self, cr, uid, ids, context=None):
        self.approve_forecast(cr, uid, ids, context=context)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        return True  
        
    def reject_outlet_sale_forecast(self, cr, uid, ids, context=None):
        return self.reject_forecast(cr, uid, ids, context=context)
        
    def cancel_outlet_sale_forecast(self, cr, uid, ids, context=None):
        return self.cancel_forecast(cr, uid, ids, context=context)
        
    def send_back_outlet_sale_forecast(self, cr, uid, ids, context=None):
        return self.send_for_validate(cr, uid, ids, context=context)
        
outlet_sales_forecast()

        
class outlet_sales_forecast_line(osv.osv):
    _description="Sale forecast Lines"
    _name = 'outlet.sales.forecast.line'
    
    _columns = {
        'forecast_id':fields.many2one('outlet.sales.forecast','Forecast'),
        'name': fields.many2one('product.product', 'Product'),
        'category_id':fields.many2one('product.category','Category'),
        'quantity':fields.integer('Qty'),
        'unit_price':fields.float('Unit Price'),
        'total_price':fields.float('Total Price'),
    }
    
    def create(self, cr, uid, vals, context=None):        
        if vals['name']:
            product = self.pool.get('product.product').browse(cr, uid, vals['name'])
            unit_price = product.list_price
            vals['unit_price'] = unit_price
            if unit_price and vals['quantity']:
                vals['total_price'] = unit_price * vals['quantity']
        retvals = super(outlet_sales_forecast_line, self).create(cr, uid, vals, context=context)
        return retvals
    
    def write(self, cr, uid, ids, vals, context=None):        
        unit_price =False
        quantity = False
        if vals.has_key('name'):
            product = self.pool.get('product.product').browse(cr, uid, vals['name'])
            unit_price = product.list_price
            vals['unit_price'] = unit_price
        else:
            line = self.pool.get('outlet.sales.forecast.line').browse(cr, uid, ids[0])
            unit_price = line.name.list_price
            vals['unit_price'] = unit_price
        if vals.has_key('quantity'):
            quantity = vals['quantity']
        else:
            line = self.pool.get('outlet.sales.forecast.line').browse(cr, uid, ids[0])    
            quantity = line.quantity
        if unit_price and quantity:
            vals['total_price'] = unit_price * quantity
        retvals = super(outlet_sales_forecast_line, self).write(cr, uid, ids, vals, context=context)
        return retvals
    
    def copy_data(self, cr, uid, id, default=None, context=None):
        default = default or {}
        return super(outlet_sales_forecast_line, self).copy_data(cr, uid, id, default, context)                    
        
    def onchange_product(self, cr, uid, ids, product_id, quantity, context=None):
        val={}
        product = self.pool.get('product.product').browse(cr, uid, product_id)
        if quantity:
            temp_val = self.onchange_quantity(cr, uid, ids, quantity, product.list_price, context=context)
            if temp_val.has_key('value') and temp_val['value'].has_key('total_price'):
                val['total_price'] = temp_val['value']['total_price']
        val['unit_price'] = product.list_price
        return {'value':val}            
        
    def onchange_quantity(self, cr, uid, ids, qty, unit_price, context=None):
        val={}
        if qty and unit_price:
            val['total_price'] = qty * unit_price
        return {'value':val}
    
outlet_sales_forecast_line()

