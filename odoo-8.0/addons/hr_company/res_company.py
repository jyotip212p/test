import datetime
import time
from itertools import groupby
from datetime import  date
import math
from openerp import netsvc
from openerp.tools.translate import _
from openerp import tools
from openerp.osv import fields, osv
from openerp.osv.orm import browse_record, browse_null


class res_company(osv.osv):
    _inherit='res.company'
    _columns={
              'tin':fields.char('TIN',size=120),
              'cst':fields.char('CST',size=120),
              'service_tax':fields.char('Service Tax No',size=120),
              'pan_no':fields.char('PAN No',size=120),  
                 
              }
    
    
res_company()