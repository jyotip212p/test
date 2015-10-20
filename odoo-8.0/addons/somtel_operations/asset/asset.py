from openerp.osv import osv, fields
import time
from openerp.tools.translate import _

class AssetRequisition(osv.osv):
    
    _name = 'asset.requisition'
    _description = 'Asset Requisition'
    _inherit = ['mail.thread','ir.needaction_mixin']
    
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
    
    _columns = {
                'name':fields.char('Reference',size=64,copy=False,readonly=True,states={'draft': [('readonly', False)]}),
                'date':fields.date('Date',copy=False,readonly=True,states={'draft': [('readonly', False)]}),
                'expected_date':fields.date('Expected Date',copy=False,readonly=True,states={'draft': [('readonly', False)]}),
                'employee_id':fields.many2one('hr.employee','Employee',readonly=True,states={'draft': [('readonly', False)]}),
                'department_id':fields.many2one('hr.department','Department',readonly=True,states={'draft': [('readonly', False)]}),
                'analytic_account_id':fields.many2one('account.analytic.account','Analytic Account'),
                'product_id':fields.many2one('product.product','Product',readonly=True,states={'draft': [('readonly', False)]}),
                'quantity':fields.float('Quantity',readonly=True,states={'draft': [('readonly', False)]}),
                'uom_id':fields.many2one('product.uom','UOM',readonly=True,states={'draft': [('readonly', False)]}),
                'asset_name':fields.char('Asset Name',size=100),
                'state':fields.selection([('draft','Draft'),
                                          ('waiting','Waiting Approval'),
                                          ('waiting_reception','Waiting for Reception'),
                                          ('pick_exception','Material Exception'),
                                          ('done','Received'),
                                          ('cancel','Cancel')],string='Status',copy=False,track_visibility='onchange'),
                'validated_by':fields.many2one('res.users','Validated By',copy=False,readonly=True),
                'company_id':fields.many2one('res.company','Company',readonly=True,states={'draft': [('readonly', False)]}),
                'asset_id':fields.many2one('account.asset.asset','Related Asset',copy=False,readonly=True),
                'picking_id':fields.many2one('stock.picking','Internal Move',copy=False,readonly=True),
                'notes':fields.text('Notes'),
                'reason':fields.char('Reason',size=264,readonly=True,states={'draft': [('readonly', False)]}),
                'type':fields.selection([('in','In'),('out','Out')],string='Type'),
                'picking_lines':fields.one2many('stock.picking','asset_requisition_id','Pickings'),
                'return_id':fields.many2one('asset.requisition','Reference',readonly=True,copy=False),
                'prod_type':fields.selection([('inventory','Inventory')
                                                 ,('non-inventory','Non Inventory')
                                                 ,('asset','Asset')
                                                 ,('service','service')], string="Product Type"),
                }
    
    _defaults = {
                 'date':time.strftime("%Y-%m-%d"),
                 'type':'in',
                 'name':'Request For Asset/',
                 'employee_id':lambda s, cr, uid, c:s._get_employee(cr, uid, c),
                 'department_id':lambda s, cr, uid, c:s._get_department(cr, uid, c),
                 'state':'draft',
                 'quantity':1.0,
                 'company_id':lambda s, cr, uid, c:s.pool.get('res.company')._company_default_get(cr, uid, 'asset.requisition',context=c)
                 }
    
    def create(self, cr, uid, vals, context=None):
        if vals.get('type') == 'in':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'asset.requisition.in')
        else:
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'asset.requisition.out')
        return super(AssetRequisition, self).create(cr, uid, vals, context=context)
    
    def action_submit(self, cr, uid, ids, context=None):
        for req in self.browse(cr, uid, ids, context=context):
            manager_id =self.pool.get('hr.department').browse(cr,uid,req.department_id.id,context=context).manager_id.user_id.partner_id.id
            if manager_id:
                 post_values = {
                                'partner_ids': [manager_id],
                               'subject':"Asset for %s has been Raised " %(req.name),
                               'body':" Asset %s is raised by %s and is waiting for approval." %(req.name,req.employee_id.name)
                               }  
                 msg_id = self.message_post(cr, uid,[req.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            self.write(cr, uid, [req.id], {'state':'waiting'}, context=context)
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        for req in self.browse(cr, uid, ids, context=context):
            employee_id=req.employee_id.user_id or req.employee_id.user_id.partner_id.id
            if employee_id:
                 post_values = {
                                'partner_ids': [employee_id],
                               'subject':"Asset Request %s has been Cancelled" %(req.name),
                               'body':" Asset Request %s is Cancelled by %s " %(req.name,req.department_id.manager_id.name)
                               }  
                 msg_id = self.message_post(cr, uid,[req.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            self.write(cr, uid, [req.id], {'state':'cancel'}, context=context)
        return True
    
    def action_approve(self, cr, uid, ids, context=None):
        res = False
        context = context or {}
        for req in self.browse(cr, uid, ids, context=context):
            mtr_pool = self.pool.get('material.indentation')
            war_pool = self.pool.get('stock.warehouse')
            pro_pool = self.pool.get('product.product')
            main_war = war_pool.search(cr, uid, [('main_warehouse','=',True),('company_id','=',req.company_id.id)])
            if not main_war:
                raise osv.except_osv(_('ERROR !!'),_('There is no Main Warehouse defined for this company. Please contact your Administrator'))
            
            asset_loc_id = war_pool.read(cr, uid, main_war[0], ['loc_asset_id'], context=context)['loc_asset_id'][0]
            if req.type == 'in':
                mtr_lines = {
                             'product_id':req.product_id.id,
                             'quantity':req.quantity,
                             'uom_id':req.uom_id.id,
                             'dest_location_id':asset_loc_id,
                             'warehouse_id':main_war[0],
                             'prod_type':req.prod_type,
                             'name':pro_pool.name_get(cr, uid, [req.product_id.id], context=context)[0][1],
                             }
                mtr_data = {
#                             'name':'Material Required as Asset',
                            'employee_id':req.employee_id.id,
                            'department_id':req.department_id.id,
                            'asset_requisition_id':req.id,
                            'company_id':req.company_id.id,
                            'material_lines':[(0,0,mtr_lines)],
                            'warehouse_id':main_war[0],
                            'expected_date':req.expected_date,
                            }
                context.update({'from_asset':True})
                mtr_id = mtr_pool.create(cr, uid, mtr_data, context=context)
                mtr_pool.action_approve(cr, uid, [mtr_id], context=context)
            else:
                req_id = self.search(cr, uid, [('return_id','=',req.id)])
                for ret_req in self.browse(cr, uid, req_id, context=context):
                    for pick in ret_req.picking_lines:
                        context['active_id'] = pick.id
                        context['asset_requisition_id'] = req.id
                        wiz_ret_id = self.pool.get('stock.return.picking').create(cr, uid, {}, context=context)
                        res = self.pool.get('stock.return.picking').create_returns(cr, uid, [wiz_ret_id], context=context)
                        
#            hr_warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [('main_warehouse', '=', True)],context=context)
            hr_manager_id = self.pool.get('stock.warehouse').browse(cr, uid, main_war[0],context=context).user_id.partner_id.id
            if hr_manager_id:
                 post_values = {
                                'partner_ids': [hr_manager_id],
                               'subject':"Asset Request %s is Approved" %(req.name),
                               'body':" Asset Request %s is Approved by %s. Kindly Process." %(req.name,req.department_id.manager_id.name)
                               }  
                 msg_id = self.message_post(cr, uid,[req.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            self.write(cr, uid, [req.id], {'state':'waiting_reception','validated_by':uid}, context=context)
        return res or True
    
    def unlink(self, cr, uid, ids, context=None):
        for req in self.browse(cr, uid, ids, context=context):
            if req.state != 'draft':
                raise osv.except_osv(_('Warning !!'),_('Only draft requests allowed to delete'))
        return super(AssetRequisition, self).unlink(cr, uid, ids, context=context)
    
    def pick_exception(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'pick_exception'}, context=context)
    
    def action_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'done'}, context=context)
    
    def onchange_product(self, cr, uid, ids, product_id, context=None):
        res = {}
        if not product_id:
            return res
        pro_pool = self.pool.get('product.product')
        pro_data = pro_pool.read(cr, uid, product_id, ['uom_id', 'standard_price', 'product_type'], context=context)
        res['value'] = {'uom_id':pro_data['uom_id'][0], 'prod_type':pro_data['product_type']}
        return res
    
    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        res = {}
        if not employee_id:
            return res
        emp_pool = self.pool.get('hr.employee')
        emp_data = emp_pool.read(cr, uid, employee_id, ['department_id'], context=context)
        res['value'] = {'department_id':emp_data['department_id'][0]}
        return res
    
    def return_assets(self, cr, uid, ids, context=None):
        for req in self.browse(cr, uid, ids, context=context):
            if not context:
                context = {}
            context.update({'default_product_id':req.product_id.id,'default_quantity':req.quantity,'default_asset_requisition_id':req.id})
        return {
                'name':_('Return Asset Confirmation'),
                'type':'ir.actions.act_window',
                'res_model':'return.asset',
                'view_mode':'form',
                'view_type':'form',
                'context':context,
                'target':'new',
                }
    
AssetRequisition()

class AccountAsset(osv.osv):
    
    _name = 'account.asset.asset'
    _inherit = ['account.asset.asset','mail.thread','ir.needaction_mixin']
    
    _columns = {
                'employee_id':fields.many2one('hr.employee','Assigned To'),
                'state': fields.selection([('draft','Draft'),('open','Running'),('close','Close')], 'Status', required=True, copy=False,
                                  help="When an asset is created, the status is 'Draft'.\n" \
                                       "If the asset is confirmed, the status goes in 'Running' and the depreciation lines can be posted in the accounting.\n" \
                                       "You can manually close an asset when the depreciation is over. If the last line of depreciation is posted, the asset automatically goes in that status.",track_visibility="on_change"),
                }
    
AccountAsset()