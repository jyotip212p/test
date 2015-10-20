from openerp.osv import osv, fields
import time
from openerp.tools.translate import _
import csv

class ImportBudgetLine(osv.osv_memory):
    
    _name = 'import.budget.line'
    
    _columns = {
                'budget_file':fields.binary('File'),
                'department_id':fields.many2one('hr.department','Department'),
                }
    
    _defaults = {
                 'department_id':lambda self, c, uid, ctx:self.pool.get('crossovered.budget.lines')._get_department(c, uid, context=ctx),
                 }
    
    def create_budget_line(self, cr, uid, ids, context=None):
        for bud in self.browse(cr, uid, ids, context=context):
            if not bud.budget_file:
                raise osv.except_osv(_('ERROR !!'),_('Please select the file.'))
            csvfile = bud.budget_file.decode('base64')
            print csvfile
            fileReader = csvfile.split('\n')
            flag = False
            for row in fileReader:
                if not flag:
                    flag = True
                    continue
                row = row.split(',')
                if len(row) < 5:
                    continue
                print '-----------ROW-----------',len(row)
                analytic_account_id = self.pool.get('account.analytic.account').search(cr, uid, [('name','=',row[0])])
                if not analytic_account_id:
                    raise osv.except_osv(_('ERROR !!'),_('There is no Analytic Account with name %s'%(row[0])))
                general_budget_id = self.pool.get('account.budget.post').search(cr, uid, [('name','=',row[1]),('analytic_account_id','=',analytic_account_id[0])])
                if not general_budget_id:
                    raise osv.except_osv(_('ERROR !!'),_('There is no Analytic Element with name %s or it may not be linked with Analytic Account %s'%(row[1],row[0])))
                
                data = {
                        'analytic_account_id':analytic_account_id[0],
                        'general_budget_id':general_budget_id[0],
                        'planned_amount':-abs(float(row[2])),
                        'date_from':row[3],
                        'date_to':row[4],
                        'department_id':bud.department_id.id,
                        }
                print "------------CSVDATA-----------",data
                self.pool.get('crossovered.budget.lines').create(cr, uid, data, context=context)
        return True
    
ImportBudgetLine()