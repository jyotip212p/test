from openerp.osv import fields, osv
from openerp.osv.orm import browse_record, browse_null


class hr_skill(osv.osv):
    _name='hr.skill'
    _description='Skill'
    _order='skill desc'
    _columns={
              'name':fields.char('Skill',size=120),
              'description':fields.text('Description'),
              'company_id':fields.many2one('res.company','Company'),
          
              }
    
    
hr_skill()