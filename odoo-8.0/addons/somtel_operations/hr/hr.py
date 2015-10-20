from openerp.osv import osv, fields
import time
from openerp.tools.translate import _


class HrEmployee(osv.osv):
    
    _inherit = 'hr.employee'
    
    _columns = {
                'sector_id':fields.many2one('sale.sector','Region'),
                'branch_id':fields.many2one('sale.branch', 'Branch'),
                }
    
HrEmployee()


class HrDepartment(osv.osv):
    
    _inherit = 'hr.department'

    def _get_analytic_account(self, cr, uid, user_id, context=None):
        res = {}
        emp_id = self.pool.get('hr.employee').search(cr,uid, [('user_id','=',user_id)])
        if not emp_id:
            return False
        emp_obj = self.pool.get('hr.employee').browse(cr,uid,emp_id[0],context=context)
        return emp_obj.department_id and emp_obj.department_id.analytic_account_id and emp_obj.department_id.analytic_account_id.id or False    
    
    _columns = {
                'analytic_account_id':fields.many2one('account.analytic.account','Analytic Account'),
                }
    
HrDepartment()

class HrTraining(osv.osv):
    
    _inherit = 'hr.training'
    
    
    _defaults = {
                 'budget_id':lambda self, cr, uid, c:self.pool.get('hr.department')._get_analytic_account(cr, uid, uid, context=c),
                 }
    
    def action_create_invoice(self, cr, uid, ids, context=None):
        context = context or None
        for train in self.browse(cr, uid, ids, context=context):
            if not train.partner_id.property_account_payable:
                raise osv.except_osv(_("ERROR"),_("Please define payable account for the Supplier %s"%(train.partner_id.name)))
            if not (train.product_id.property_account_expense and train.product_id.property_account_expense.id or train.product_id.categ_id.property_account_expense_categ):
                raise osv.except_osv(_("ERROR"),_("Please define expense account for the Product %s"%(train.product_id.name)))
            journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'purchase'), ('company_id', '=', train.company_id.id)],
            limit=1)
            if not journal_ids:
                raise osv.except_osv(_('Error!'),
                    _('Please define Purchase journal for this company: "%s" (id:%d).') % (train.company_id.name, train.company_id.id))
            invoice_lines = {
                             'product_id':train.product_id.id,
                             'quantity':'1',
                             'name':train.employee_id.name,
                             'prod_type':train.product_id.product_type,
                             'price_unit':train.price or train.product_id.list_price,
                             'account_analytic_id':train.budget_id and train.budget_id.id or False,
                             'account_id':train.product_id.property_account_expense and train.product_id.property_account_expense.id or train.product_id.categ_id.property_account_expense_categ.id,
                             }
            invoice = {
                       'partner_id':train.partner_id.id,
                       'journal_id':journal_ids[0],
                       'account_id':train.partner_id.property_account_payable and train.partner_id.property_account_payable.id,
                       'pricelist_id':train.pricelist_id.id,
                       'origin':train.name,
                       'invoice_line':[(0, 0, invoice_lines)],
                       'type':'in_invoice'
                       }
            invoice_id = self.pool.get('account.invoice').create(cr, uid, invoice, context=context)
            self.write(cr, uid, [train.id], {'invoice_id':invoice_id}, context=context)
            part_ids=[]
            finance_mgr_ids = self.pool.get('res.groups').search(cr,uid,[('category_id','=','Accounting & Finance'),('name','=','Financial Manager')])
            if finance_mgr_ids:
                for grp in finance_mgr_ids:
                    grp_obj = self.pool.get('res.groups').browse(cr,uid,grp, context=context)
                    part_ids = [usr.partner_id.id for usr in grp_obj.users]
                    if part_ids:
                        post_values = {
                                    'partner_ids': part_ids,
                                    'subject':"Vendor Invoice for Training Request %s"%(train.name),
                                    'body':"Please the process the payment for %s."%(train.name)
                                   }
                        msg_id = self.pool.get('account.invoice').message_post(cr, uid, [invoice_id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            dummy,view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
        return {
                    'type': 'ir.actions.act_window',
                    'name': _('Invoice for Training'),
                    'res_model': 'account.invoice',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'current',
                    'nodestroy': True,
                    'res_id':invoice_id,
                      }
    
HrTraining()


class HrGroupedTraining(osv.osv):
    
    _inherit = 'hr.grouped.training'
    
    def action_create_invoice(self, cr, uid, ids, context=None):
        context = context or None
        for train in self.browse(cr, uid, ids, context=context):
            if not train.partner_id.property_account_payable:
                raise osv.except_osv(_("ERROR"),_("Please define payable account for the Supplier %s"%(train.partner_id.name)))
            if not (train.product_id.property_account_expense and train.product_id.property_account_expense.id or train.product_id.categ_id.property_account_expense_categ):
                raise osv.except_osv(_("ERROR"),_("Please define expense account for the Product %s"%(train.product_id.name)))
            journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'purchase'), ('company_id', '=', train.company_id.id)],
            limit=1)
            if not journal_ids:
                raise osv.except_osv(_('Error!'),
                    _('Please define purchase journal for this company: "%s" (id:%d).') % (train.company_id.name, train.company_id.id))
            invoice_lines = {
                             'product_id':train.product_id.id,
                             'quantity':'1',
                             'name':'Organized Training' ,
                             'prod_type':train.product_id.product_type,
                             'price_unit':train.price or train.product_id.standard_price,
                             'account_analytic_id':train.analytic_account_id and train.analytic_account_id.id or False,
                             'account_id':train.product_id.property_account_expense and train.product_id.property_account_expense.id or train.product_id.categ_id.property_account_expense_categ.id,
                             }
            invoice = {
                       'partner_id':train.partner_id.id,
                       'journal_id':journal_ids[0],
                       'account_id':train.partner_id.property_account_payable and train.partner_id.property_account_payable.id,
                       'currency_id':train.currency_id.id,
                       'origin':train.name,
                       'invoice_line':[(0, 0, invoice_lines)],
                       'type':'in_invoice'
                       }
            invoice_id = self.pool.get('account.invoice').create(cr, uid, invoice, context=context)
            self.write(cr, uid, [train.id], {'invoice_id':invoice_id}, context=context)
            part_ids=[]
            finance_mgr_ids = self.pool.get('res.groups').search(cr,uid,[('category_id','=','Accounting & Finance'),('name','=','Financial Manager')])
            if finance_mgr_ids:
                for grp in finance_mgr_ids:
                    grp_obj = self.pool.get('res.groups').browse(cr,uid,grp, context=context)
                    part_ids = [usr.partner_id.id for usr in grp_obj.users]
                    if part_ids:
                        post_values = {
                                    'partner_ids': part_ids,
                                    'subject':"Vendor Invoice for Training Request %s"%(train.name),
                                    'body':"Please the process the payment for %s."%(train.name)
                                   }
                        msg_id = self.pool.get('account.invoice').message_post(cr, uid, [invoice_id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            dummy,view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
        return {
                    'type': 'ir.actions.act_window',
                    'name': _('Invoice for Training'),
                    'res_model': 'account.invoice',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'current',
                    'nodestroy': True,
                    'res_id':invoice_id,
                      }
    
    

HrGroupedTraining()
class HrExpenseLine(osv.osv):
    _inherit="hr.expense.line"

    def onchange_product_id(self,cr,uid,ids,product_id,department_id,grade_id,context=None):
        domain = {'analytic_account':[]}
        values = super(HrExpenseLine,self).onchange_product_id(cr, uid, ids, product_id, department_id, grade_id, context=context)
        dpt_obj=self.pool.get('hr.department')
        domain = {'analytic_account':[]}
        if department_id:
             department=dpt_obj.browse(cr,uid,department_id,context=context)
             dpt_id=department.analytic_account_id and department.analytic_account_id.id
             if dpt_id:
                 values['domain'].update({'analytic_account':[('id','=',dpt_id)]})
        return {'value': values['value'],'domain':values['domain']}                 

HrExpenseLine()

class hr_travel(osv.osv):
    _inherit='hr.travel'
    
    def onchange_department_id(self, cr, uid, ids,department_id, context=None):
        value = {'analytic_account_id': False}
        if department_id:
            dept = self.pool.get('hr.department').browse(cr, uid, department_id)
            value['analytic_account_id']=dept.analytic_account_id.id
        return {'value': value}

hr_travel()    

class hr_requisition(osv.osv):
    _inherit='hr.requisition'
    
    def onchange_department_id(self, cr, uid, ids,department_id, context=None):
        values = super(hr_requisition,self).onchange_department_id(cr, uid, ids, department_id, context=context)
        if department_id:
            dept = self.pool.get('hr.department').browse(cr, uid, department_id)
            values['value'].update({'analytic_account':dept.analytic_account_id.id})
        return values

hr_requisition()   

class hr_expense(osv.osv):
    _inherit='hr.expense.expense'
    
    def onchange_department_id(self, cr, uid, ids,department_id, context=None):
        value = {'analytic_account': False}
        if department_id:
            dept = self.pool.get('hr.department').browse(cr, uid, department_id)
            value['analytic_account']=dept.analytic_account_id.id
        return {'value': value}

hr_expense()  

class hr_travel_desk(osv.osv):
    _inherit='hr.travel.desk'
    
    def button_invoice_traveldesk(self,cr,uid,ids,context=None):
        dummy,view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
        travel_id=0
        for travel in self.browse(cr, uid, ids, context=context):
            self.pool.get('hr.travel').write(cr,uid,travel.travel_id.id,{'travel_desk_id':travel.id})
            for j in travel.travel_itinerary:
                ticket_price=j.ticket_price
                if ticket_price==0:
                    raise osv.except_osv(_('Warning!'),_('Cannot proceed further!! Please enter Ticket Price'))
            if travel.invoice_id:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Invoice for Travel'),
                    'res_model': 'account.invoice',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'current',
                    'nodestroy': True,
                    'res_id':travel.invoice_id.id
                    }
            journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'purchase'), ('company_id', '=', travel.company_id.id)],
            limit=1)
            if not journal_ids:
                raise osv.except_osv(_('Error!'),_('Please define purchase journal for this company: "%s" (id:%d).') % (travel.company_id.name, travel.company_id.id))
            invoice_lines = {
                            'product_id':travel.product_id.id,
                            'quantity':1,
                            'price_unit':travel.total_amount,
                            'prod_type':travel.product_id.product_type,
                            'account_analytic_id':travel.travel_id.department_id.analytic_account_id and travel.travel_id.department_id.analytic_account_id.id or False,
                            'name':travel.name+' : '+travel.product_id.name,
                            'account_id':travel.product_id.property_account_expense and travel.product_id.property_account_expense.id or travel.product_id.categ_id.property_account_expense_categ.id,
                            }
            invoice = {
                    'partner_id':travel.supplier_id.id,
                    'account_id':travel.supplier_id.property_account_payable and travel.supplier_id.property_account_payable.id,
                    'pricelist_id':travel.pricelist_id.id,
                    'origin':travel.name,
                    'invoice_line':[(0, 0, invoice_lines)],
                    'type':'in_invoice',
                    'journal_id':journal_ids[0],
                    }
            invoice_id = self.pool.get('account.invoice').create(cr, uid, invoice, context=context)
            self.write(cr, uid, [travel.id], {'state':'invoice','user_id':uid,'invoice_id':invoice_id}, context=context)
            part_ids=[]
            finance_mgr_ids = self.pool.get('res.groups').search(cr,uid,[('category_id','=','Accounting & Finance'),('name','=','Financial Manager')])
            if finance_mgr_ids:
                for grp in finance_mgr_ids:
                    grp_obj = self.pool.get('res.groups').browse(cr,uid,grp, context=context)
                    part_ids = [usr.partner_id.id for usr in grp_obj.users]
                    if part_ids:
                        post_values = {
                                    'partner_ids': part_ids,
                                    'subject':"Vendor Invoice for Travel Request %s"%(travel.travel_id.name),
                                    'body':"Please the process the payment for %s."%(travel.travel_id.name)
                                   }
                        msg_id = self.pool.get('account.invoice').message_post(cr, uid, [invoice_id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
        return {
                    'type': 'ir.actions.act_window',
                    'name': _('Invoice for Travel'),
                    'res_model': 'account.invoice',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'current',
                    'nodestroy': True,
                    'res_id':invoice_id
                }

hr_travel_desk()