from openerp.osv import osv, fields
import time
from datetime import datetime, timedelta
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class BudgetLines(osv.osv):
    
    _name = 'crossovered.budget.lines'
    _inherit = ['crossovered.budget.lines','mail.thread','ir.needaction_mixin']
    _order = 'id desc'

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.analytic_account_id and line.general_budget_id:
                result.append((line.id, line.analytic_account_id.name+' - '+line.general_budget_id.name))                
        return result

    _columns = {
                'department_id':fields.many2one('hr.department','Department',readonly=True,states={'draft': [('readonly', False)]}),
                'employee_id':fields.many2one('hr.employee','Employee',readonly=True,states={'draft': [('readonly', False)]}),
                'crossovered_budget_id': fields.many2one('crossovered.budget', 'Budget', ondelete='cascade', copy=False, select=True, required=False,readonly=True,states={'draft': [('readonly', False)]}),
                'state':fields.selection([('draft','Draft'),('waiting','Waiting'),('confirmed','Confirmed'),('cancel','Cancel')], string='Status', readonly=True, copy=False, track_visibility='onchange'),
                'reject_comments':fields.text('Comments', copy=False),
                'approved_by':fields.many2one('res.users','Users',readonly=True,copy=False),
                'extra_budget_lines': fields.one2many('extra.budget', 'budget_line_id', 'Extra Budget Lines'),
                }

    def _check_budget_line(self, cr, uid, ids, context=None):
        for bd in self.browse(cr, uid, ids, context=context):
            company_id = bd.company_id.id
            cr.execute('SELECT id FROM crossovered_budget_lines WHERE company_id = %s AND general_budget_id = %s and analytic_account_id = %s and (date_from between %s and %s or date_to between %s and %s)',(company_id,bd.general_budget_id.id,bd.analytic_account_id.id,bd.date_from,bd.date_to,bd.date_from,bd.date_to))
            bd_ids = cr.fetchall()     
            if len(bd_ids) > 1:
                return False
        return True
    
#     _constraints = [(_check_budget_line,"A company already has a budget line for the defined period",['analytic_account_id','general_budget_id','date_from','date_to'])]
    
    def _get_employee(self, cr, uid, context=None):
        emp_pool = self.pool.get('hr.employee')
        emp_id = emp_pool.search(cr, uid, [('user_id','=',uid)])
        return emp_id and emp_id[0] or False
    
    def _get_department(self, cr, uid, context=None):
        emp_id = self._get_employee(cr, uid, context=context)
        dept_id = False
        if emp_id:
            dept_id = self.pool.get('hr.employee').read(cr, uid, emp_id, ['department_id'], context=context)
        return dept_id and dept_id['department_id'] and dept_id['department_id'][0] or False
    
    def _get_analytic_account(self, cr, uid, context=None):
        dept_id = self._get_department(cr, uid, context=context)
        analytic_account_id = False
        if dept_id:
            analytic_account_id = self.pool.get('hr.department').read(cr, uid, dept_id, ['analytic_account_id'], context=context)
        return analytic_account_id and analytic_account_id['analytic_account_id'] and analytic_account_id['analytic_account_id'][0] or False
    
    _defaults = {
                 'employee_id':_get_employee,
                 'department_id':_get_department,
                 'analytic_account_id':_get_analytic_account,
                 'state':'draft',
                 }

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        raise osv.except_osv(_('ERROR !!'),_('Duplication not Allowed!!'))
        return super(BudgetLines,self).copy(cr, uid, id, default, context=context)

    def onchange_date(self, cr, uid, ids, date_to, date_from):
        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise osv.except_osv(_('Warning!'),_('The start date must be anterior to the end date.'))
        result = {'value': {}}
        return result

    def action_submit(self, cr, uid, ids, context=None):
        for req in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [req.id], {'state':'waiting'}, context=context)
        return True
    
    def action_confirm(self, cr, uid, ids, context=None):
        for req in self.browse(cr, uid, ids, context=context):
            budgets = self.pool.get('crossovered.budget').search(cr, uid, [('date_from','=',req.date_from),('date_to','=',req.date_to),('state','=','draft')])
            if not budgets:
                raise osv.except_osv(_('ERROR !!'),_('Start date and End date are not matching with the Main Budget configured / Main Budget is Already Approved. Please contact Accounts Department for the further process'))
            self.pool.get('crossovered.budget').write(cr, uid, [budgets[0]], {'crossovered_budget_line':[(4, req.id)]})
            self.write(cr, uid, [req.id], {'state':'confirmed','approved_by':uid}, context=context)
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        for req in self.browse(cr, uid, ids, context=context):
            if not req.reject_comments:
                raise osv.except_osv(_('ERROR !!'),_('Please enter the comments for cancel.'))
            self.write(cr, uid, [req.id], {'state':'cancel','approved_by':uid}, context=context)
        return True
    
    def unlink(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.state != 'draft':
                raise osv.except_osv(_('ERROR !!'),_('Only Draft requests can be deleted.'))
        return super(BudgetLines, self).unlink(cr, uid, ids, context=context)

    def create_extra_budget(self, cr, uid, ids, context=None):
        res={}
        eb_obj = self.pool.get('extra.budget')
        for line in self.browse(cr, uid, ids, context=context):
            if line.extra_budget_lines:
                return {
                        'type': 'ir.actions.act_window',
                        'name': _('Extra Budget'),
                        'res_model': 'extra.budget',
                        'view_type': 'form',
                        'view_mode': 'tree,form',            
                        'view_id': False,
                        'target': 'current',
                        'domain': [('id','in', [ed.id for ed in line.extra_budget_lines])],
                        'nodestroy': True,
                        'context': {
                                    'search_default_id':ids[0],
                                    'default_budget_line_id':line.id,
                                    'default_analytic_account_id':line.analytic_account_id.id,
                                    'default_general_budget_id':line.general_budget_id.id,
                                    },
                        }                   
            res = {
                   'budget_line_id':line.id,
                   'analytic_account_id':line.analytic_account_id.id,
                   'general_budget_id':line.general_budget_id.id,
                   'planned_amount':line.planned_amount,
                   }
            eb_id = eb_obj.create(cr, uid, res, context=context)
        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'somtel_operations', 'view_extra_budget_form')
        return {
                'type': 'ir.actions.act_window',
                'name': _('Extra Budget'),
                'res_model': 'extra.budget',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'nodestroy': True,
                'res_id':eb_id,
                }     
    
BudgetLines()

class Budget(osv.osv):
    
    _name = 'crossovered.budget'
    _inherit = ['crossovered.budget','mail.thread','ir.needaction_mixin']
    _order = 'id desc'
    
    def budget_confirm(self, cr, uid, ids, *args):
        for budget in self.browse(cr, uid, ids, context=args):
            if not budget.crossovered_budget_line:
                raise osv.except_osv(_("ERROR !!"),_("No lines added to the budget. Please add before confirm."))
            for line in budget.crossovered_budget_line:
                if line.state in ('draft', 'waiting'):
                    raise osv.except_osv(_("ERROR !!"),_("All the lines should be approved, before confirming the Main budget."))
        return super(Budget, self).budget_confirm(cr, uid, ids, args)
    
    def action_send_notification(self, cr, uid, ids, context=None):
        res = {}
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'crossovered.budget',
            'default_res_id': ids[0],
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
    
Budget()

class ExtraBudget(osv.osv):
    _name = 'extra.budget'
    _inherit = ['mail.thread','ir.needaction_mixin']
    _order = 'id desc'      

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.analytic_account_id and line.general_budget_id:
                result.append((line.id, 'Extra Budget for '+line.analytic_account_id.name+' - '+line.general_budget_id.name))                
        return result
    
    _columns = {
            'budget_line_id': fields.many2one('crossovered.budget.lines', 'Budget Line', readonly=True,states={'draft': [('readonly', False)]}),
            'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
            'general_budget_id': fields.many2one('account.budget.post', 'Budgetary Position',required=True),
            'planned_amount':fields.float('Planned Amount', required=True, digits_compute=dp.get_precision('Account')),
            'extra_amount':fields.float('Extra Amount', digits_compute=dp.get_precision('Account'),readonly=True,states={'draft': [('readonly', False)]}),
            'comments':fields.char('Reason',size=254,help='Enter the reason for Extra Budget',readonly=True,states={'draft': [('readonly', False)]}),
            'state':fields.selection([('draft','Draft'),('waiting','Waiting'),('confirmed','Confirmed'),('cancel','Cancel')], string='Status', readonly=True, copy=False),
            
                }
    _defaults = {
                 'state':'draft',
                 'planned_amount':0.0,
                 }

    def button_submit(self,cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'waiting'}, context=context)
    
    def button_confirm(self,cr, uid, ids, context=None):
        bline_obj = self.pool.get('crossovered.budget.lines')
        planned_amt = 0.0
        for extra in self.browse(cr, uid, ids, context=context):
            planned_amt = abs(extra.budget_line_id.planned_amount) + abs(extra.extra_amount)
            bline_obj.write(cr, uid, [extra.budget_line_id.id], {'planned_amount':-planned_amt})
        return self.write(cr, uid, ids, {'state':'confirmed'}, context=context)    

ExtraBudget()

class AccountBudgetPost(osv.osv):
    
    _inherit = 'account.budget.post'
    
    _columns = {
                'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
                'type':fields.selection([('sale','Sale'),('purchase','Purchase')], string='Type'),
                }
    
AccountBudgetPost()