import datetime
import time
from datetime import  date
import math
from openerp import tools
from openerp.osv import fields, osv
from openerp.osv.orm import browse_record, browse_null


class training(osv.osv):
    _name ='training'
    _description = "Training Request"
    _order = 'name desc ,date desc'
    
    _inherit = ['mail.thread', 'ir.needaction_mixin']
     
     
    _columns ={
     'name':fields.char('Reference',size = 120),
     'employee_id':fields.many2one('hr.employee','Employee'),
     'skill_id':fields.many2one('hr.skill','Skill'),
     'department_id':fields.many2one('hr.department','Department'),
     'date':fields.date("Date"),
     'reason':fields.char('Description',size=120),
     'training_reason':fields.text('Reasons',size=240),  
      'state':fields.selection([('draft','Draft'),
                                        ('waiting_approval','Waiting Approval'),
                                        ('approved','Approved'),
                                        ('training_in_progress','Training Progress'),
                                        ('training_done','Training Completed'),
                                        ('feedback','Feedback'),
                                        ('done','Done'),
                                        ('cancel','Cancel')],'Status',readonly=True,track_visibility="onchange"),
     
     }
    
    _defaults={
               'state':'draft'
               }
    
    def _get_employee(selfself,cr,uid,ids,context=None):
        emp_id = self.pool.get('hr.employee').search(cr,uid,[("user_id",'=',uid)])
        if emp_id:
            return emp_id[0]
        return False
    def button_submit(self,cr,uid,ids,context=None):
               
         return self.write (cr,uid,ids,{'state':'waiting_approval'},context=context)
     


training()