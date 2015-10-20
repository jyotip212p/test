from openerp.osv import fields, osv
from openerp.osv.orm import browse_record, browse_null

class crm_lead(osv.osv):
    _inherit='crm.lead'
    _columns={
              'rating':fields.selection([('hot','Hot'),('cold','Cold'),('neutral','Neutral')],'Rating')
              }
    
crm_lead()