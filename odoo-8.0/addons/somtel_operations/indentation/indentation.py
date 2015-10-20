from openerp.osv import osv, fields
import time
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

class MaterialIndentation(osv.osv):
    
    _name = 'material.indentation'
    _description = 'Material Indentation'
    _order = 'name desc,date desc'
    _inherit = ['mail.thread','ir.needaction_mixin']
    _columns = {
                'name':fields.char('Reference',size=64,readonly=True,states={'draft': [('readonly', False)]}),
                'employee_id':fields.many2one('hr.employee','Employee',readonly=True,states={'draft': [('readonly', False)]}),
                'department_id':fields.many2one('hr.department','Department',readonly=True,states={'draft': [('readonly', False)]}),
                'date':fields.date('Date',readonly=True,states={'draft': [('readonly', False)]}),
                'origin':fields.char('Origin'),
                'asset_requisition_id':fields.many2one('asset.requisition','Asset Requisition',readonly=True,states={'draft': [('readonly', False)]}),
                'expected_date':fields.date('Expected Date',readonly=True,states={'draft': [('readonly', False)]}),
                'state':fields.selection([('draft','Draft'),
                                          ('waiting','Waiting'),
                                          ('confirmed','Confirmed'),
                                          ('transmitted','Requested'),
                                          ('pick_exception','Picking Exception'),
                                          ('done','Done'),
                                          ('cancel','Rejected')],string="Status",readonly=True,track_visibility='onchange'),
                'confirmed_by':fields.many2one('res.users','Confirmed By',readonly=True,states={'draft': [('readonly', False)]}),
                'material_lines':fields.one2many('material.indentation.line','indentation_id','Materials',readonly=True,states={'draft': [('readonly', False)]}),
                'notes':fields.text('Comments'),
                'warehouse_id':fields.related('shop_id','warehouse_id',type="many2one",relation='stock.warehouse',string='Destination Warehouse',readonly=True,states={'draft': [('readonly', False)]}),
                'main_warehouse_id':fields.many2one('stock.warehouse','Main Warehouse',readonly=True,states={'draft': [('readonly', False)]}),
                'src_warehouse_id':fields.many2one('stock.warehouse','Source Warehouse'),
                'company_id':fields.many2one('res.company','Company',readonly=True,states={'draft': [('readonly', False)]}),
                'picking_ids':fields.one2many('stock.picking','indentation_id','Pickings',readonly=True,states={'draft': [('readonly', False)]}),
                'sector_id':fields.many2one('sale.sector','Sector',readonly=True,states={'draft': [('readonly', False)]}),
                'shop_id':fields.many2one('sale.shop','Shop',readonly=True,states={'draft': [('readonly', False)]}),
                'sector_shop':fields.boolean('At Sector'),
                }
    
    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'material.indentation')
        return super(MaterialIndentation, self).create(cr, uid, vals, context=context)
    
    def _get_employee(self, cr, uid, context=None):
        emp_pool = self.pool.get('hr.employee')
        emp_id = emp_pool.search(cr, uid, [('user_id','=',uid)])
        if not emp_id:
            raise osv.except_osv(_("ERROR !!"),_("No employee is linked to login user. Please check with Administrator."))
        return emp_id and emp_id[0] or False
    
    def _get_department(self, cr, uid, context=None):
        emp_id = self._get_employee(cr, uid, context=context)
        dept_id = False
        if emp_id:
            dept_id = self.pool.get('hr.employee').read(cr, uid, emp_id, ['department_id'], context=context)
        return dept_id and dept_id['department_id'] and dept_id['department_id'][0] or False
    
    def _get_shop(self, cr, uid, context=None):
        shop_id = False
        print "JJJJJJJJJJJJJ", context
        if context and context.has_key('from_asset'):
            return False
        shop_id = self.pool.get('sale.shop').search(cr, uid, [('manager_id','=',uid)])
        if not shop_id:
            raise osv.except_osv(_("ERROR !!"),_("No Shop is linked to login user. Please check with Administrator."))
        return shop_id and shop_id[0] or False
    
    _defaults = {
                 'date':time.strftime("%Y-%m-%d"),
                 'state':'draft',
                 'shop_id':lambda s, cr, uid, c:s._get_shop(cr, uid, c),
                 'employee_id':lambda s, cr, uid, c:s._get_employee(cr, uid, c),
                 'department_id':lambda s, cr, uid, c:s._get_department(cr, uid, c),
                 'company_id':lambda s,cr, uid, c:s.pool.get('res.company')._company_default_get(cr, uid, 'material.indentation',context=c),
                 'main_warehouse_id':lambda s,cr, uid, c:s.pool.get('stock.warehouse')._get_main_warehouse(cr, uid, context=c)
                 }
    
    def onchange_shop(self, cr, uid, ids, shop_id, context=None):
        res = {}
        if not shop_id:
            return {'value':{'sector_id':False,'warehouse_id':False}}
        shop_pool = self.pool.get('sale.shop')
        shop_data = shop_pool.read(cr, uid, shop_id, ['sector_id','warehouse_id','sector_shop'], context=context)
        res['value'] = {'sector_shop':shop_data['sector_shop'],'sector_id':shop_data['sector_id'][0], 'warehouse_id':shop_data['warehouse_id'][0]}
        return res
    
    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        res = {}
        if not employee_id:
            return {'value':{'department_id':False}}
        emp_pool = self.pool.get('hr.employee')
        emp_data = emp_pool.read(cr, uid, employee_id, ['department_id'], context=context)
        if emp_data['department_id']:
            res['value'] = {'department_id':emp_data['department_id'][0]}
        return res
    
    def action_submit(self, cr, uid, ids, context=None):
        for mtr_ind in self.browse(cr, uid, ids, context=context): 
            if not mtr_ind.material_lines:
                raise osv.except_osv(_('ERROR !!'),_('Please enter the Products!!'))            
            if mtr_ind.sector_shop == True:
                return self.action_process_further(cr, uid, [mtr_ind.id], context=context)
            if mtr_ind.shop_id and mtr_ind.shop_id.id:
                sector_mgr_id=mtr_ind.sector_id.manager_id and mtr_ind.sector_id.manager_id.partner_id.id
                post_values = {
                                'partner_ids': [sector_mgr_id],
                                'subject':"Request From outlet %s For Material "%(mtr_ind.shop_id.name),
                                'body':"Request from outlet %s to sector %s for Material. For more details please check %s"%(mtr_ind.shop_id.name,mtr_ind.sector_id.name,mtr_ind.name)
                                }
                msg_id = self.message_post(cr, uid, [mtr_ind.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            else:
                emp_mgr_id=mtr_ind.department_id.manager_id and mtr_ind.department_id.manager_id.user_id.partner_id.id
                post_values = {
                                'partner_ids': [emp_mgr_id],
                                'subject':"Request  For Material From Employee %s"%(mtr_ind.employee_id.name),
                                'body':"Request from Employee %s  for Material. For more details please check %s"%(mtr_ind.employee_id.name,mtr_ind.name)
                                }
                msg_id = self.message_post(cr, uid, [mtr_ind.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            self.write(cr, uid, [mtr_ind.id], {'state':'waiting'}, context=context)
        return True
    
    def action_approve(self, cr, uid, ids, context=None):
        for mtr_ind in self.browse(cr, uid, ids, context=context):
            pick_pool = self.pool.get('stock.picking')
            moves = []
            pick_type_id = self.pool.get('stock.picking.type').search(cr, uid, [('code','=','internal'),('warehouse_id','=',mtr_ind.main_warehouse_id.id)])
            if not pick_type_id:
                raise osv.except_osv(_('ERROR !!'),_('Please create picking type for selected warehouse for Internal Transfers. Contact your Administrator/Warehouse Manager'))
            src_loc_id = self.pool.get('stock.picking.type').read(cr, uid, pick_type_id and pick_type_id[0], ['default_location_src_id'], context=context)['default_location_src_id'][0]
            context.update({'default_picking_type_id':pick_type_id[0]})
            asset_name = mtr_ind.asset_requisition_id and mtr_ind.asset_requisition_id.name or ''
            for line in mtr_ind.material_lines:
                move = {
                         'product_id':line.product_id.id,
                         'product_uom_qty':line.quantity,
                         'product_uos_qty':line.quantity,
                         'product_uom':line.uom_id.id,
                         'product_uos':line.uom_id.id,
                         'location_dest_id':line.dest_location_id.id,
                         'location_id':src_loc_id,
                         'name':line.name,
                         'prod_type':line.prod_type,
                         }
                moves.append((0,0,move))
            pick = {
                    'partner_id':mtr_ind.employee_id.address_home_id.id,
                    'origin':str(mtr_ind.name) + ':' + str(asset_name),
                    'indentation_id':mtr_ind.id,
                    'move_lines':moves,
                    'picking_type_id':pick_type_id[0],
                    'asset_requisition_id':mtr_ind.asset_requisition_id and mtr_ind.asset_requisition_id.id or False,
                    }
            pick_id = pick_pool.create(cr, uid, pick, context=context)
            pick_pool.action_confirm(cr, uid, [pick_id], context=context)
            self.write(cr, uid, [mtr_ind.id], {'src_warehouse_id':mtr_ind.main_warehouse_id.id,'state':'confirmed','confirmed_by':uid}, context=context)
            wh_mgr_id=mtr_ind.main_warehouse_id.user_id and mtr_ind.main_warehouse_id.user_id.partner_id.id or False
            emp_id = mtr_ind.employee_id.user_id and mtr_ind.employee_id.user_id.partner_id.id
            post_values = {
                            'partner_ids': [wh_mgr_id,emp_id],
                            'subject':"Employee %s Request For Material is Confirmed"%(mtr_ind.employee_id.name),
                            'body':"Employee %s Request For Material is Confirmed. For more details please check %s"%(mtr_ind.employee_id.name,mtr_ind.name)
                            }
            msg_id = self.message_post(cr, uid, [mtr_ind.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
        
        return True

    def action_confirm_transfer(self, cr, uid, ids, context=None):
        for mtr_ind in self.browse(cr, uid, ids, context=context):
            pick_pool = self.pool.get('stock.picking')
            moves = []
            pick_type_id = self.pool.get('stock.picking.type').search(cr, SUPERUSER_ID, [('code','=','internal'),('warehouse_id','=',mtr_ind.sector_id.warehouse_id.id)])
            if not pick_type_id:
                raise osv.except_osv(_('ERROR !!'),_('Please create picking type for selected warehouse for Internal Transfers. Contact your Administrator/Warehouse Manager'))
            src_loc_id = mtr_ind.sector_id.warehouse_id and mtr_ind.sector_id.warehouse_id.lot_stock_id.id or False
            context.update({'default_picking_type_id':pick_type_id[0]})
            for line in mtr_ind.material_lines:
                move = {
                         'product_id':line.product_id.id,
                         'product_uom_qty':line.quantity,
                         'product_uos_qty':line.quantity,
                         'product_uom':line.uom_id.id,
                         'product_uos':line.uom_id.id,
                         'prod_type':line.prod_type,
                         'location_dest_id':line.dest_location_id.id,
                         'location_id':src_loc_id,
                         'name':line.name,
                         }
                moves.append((0,0,move))
            pick = {
                    'partner_id':False,
                    'origin':str(mtr_ind.name),
                    'indentation_id':mtr_ind.id,
                    'move_lines':moves,
                    'picking_type_id':pick_type_id[0],
                    }
            pick_id = pick_pool.create(cr, SUPERUSER_ID, pick, context=context)
            pick_pool.action_confirm(cr, SUPERUSER_ID, [pick_id], context=context)
            self.write(cr, uid, [mtr_ind.id], {'src_warehouse_id':mtr_ind.sector_id.warehouse_id.id,'state':'confirmed','confirmed_by':uid}, context=context)
            outlet_mgr_id=mtr_ind.shop_id.manager_id and mtr_ind.shop_id.manager_id.partner_id.id
            post_values = {
                            'partner_ids': [outlet_mgr_id],
                            'subject':"Request From outlet %s For Material is Confirmed"%(mtr_ind.shop_id.name),
                            'body':"Request from outlet %s to sector %s for Material is Confirmed. For more details please check %s"%(mtr_ind.shop_id.name,mtr_ind.sector_id.name,mtr_ind.name)
                            }
            msg_id = self.message_post(cr, uid, [mtr_ind.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
        return True

    def action_confirm_transfer_second(self, cr, uid, ids, context=None):
        for mtr_ind in self.browse(cr, uid, ids, context=context):
            print "HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH"
            pick_pool = self.pool.get('stock.picking')
            moves = []
            pick_type_id = self.pool.get('stock.picking.type').search(cr, uid, [('code','=','internal'),('warehouse_id','=',mtr_ind.main_warehouse_id.id)])
            if not pick_type_id:
                raise osv.except_osv(_('ERROR !!'),_('Please create picking type for selected warehouse for Internal Transfers. Contact your Administrator/Warehouse Manager'))
            src_loc_id = mtr_ind.main_warehouse_id and mtr_ind.main_warehouse_id.lot_stock_id.id or False
            context.update({'default_picking_type_id':pick_type_id[0]})
            for line in mtr_ind.material_lines:
                move = {
                         'product_id':line.product_id.id,
                         'product_uom_qty':line.quantity,
                         'product_uos_qty':line.quantity,
                         'product_uom':line.uom_id.id,
                         'product_uos':line.uom_id.id,
                         'prod_type':line.prod_type,
                         'location_dest_id':line.dest_location_id.id,
                         'location_id':src_loc_id,
                         'name':line.name,
                         }
                moves.append((0,0,move))
            pick = {
                    'partner_id':False,
                    'origin':str(mtr_ind.name),
                    'indentation_id':mtr_ind.id,
                    'move_lines':moves,
                    'picking_type_id':pick_type_id[0],
                    }
            pick_id = pick_pool.create(cr, uid, pick, context=context)
            print "KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKkk"
            pick_pool.action_confirm(cr, uid, [pick_id], context=context)
            self.write(cr, uid, [mtr_ind.id], {'src_warehouse_id':mtr_ind.main_warehouse_id.id,'state':'confirmed'}, context=context)
        return True

    def action_process_further(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'transmitted'}, context=context)
        for mtr_ind in self.browse(cr, uid, ids, context=context):
            wh_mgr_id=mtr_ind.warehouse_id.user_id and mtr_ind.warehouse_id.user_id.partner_id.id or False
            outlet_mgr_id=mtr_ind.shop_id.manager_id and mtr_ind.shop_id.manager_id.partner_id.id
            post_values = {
                            'partner_ids': [wh_mgr_id,outlet_mgr_id],
                            'subject':" Request From  Sector %s  to Warehouse %s For Material "%(mtr_ind.sector_id.name,mtr_ind.warehouse_id.name),
                            'body':" Request From Sector %s  to Warehouse %s For Material . For more details please check %s"%(mtr_ind.sector_id.name,mtr_ind.warehouse_id.name,mtr_ind.name)
                            }
            msg_id = self.message_post(cr, uid, [mtr_ind.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            self.write(cr, uid, ids, {'src_warehouse_id':mtr_ind.main_warehouse_id.id}, context=context)
        return True    
    
    def view_transfer(self, cr, uid, ids, context=None):
        for mtr_ind in self.browse(cr, uid, ids, context=context):
            pick_id = self.pool.get('stock.picking').search(cr, uid, [('indentation_id','=',mtr_ind.id)])
            if not pick_id:
                return False
            result = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'action_picking_tree_all')
        return {
                'name':_('Internal Transfers'),
                'type':'ir.actions.act_window',
                'res_model':'stock.picking',
                'view_mode':'tree,form',
                'domain':[('id','in',[pick.id for pick in mtr_ind.picking_ids])],
                'target':'new',
                'nodestroy':True,
                }
        
    def pick_exception(self, cr, uid, ids, context=None):
        for mtr_ind in self.browse(cr, uid, ids, context=context):
            if mtr_ind.asset_requisition_id:
                self.pool.get('asset.requisition').pick_exception(cr, uid, [mtr_ind.asset_requisition_id.id], context=context)
        return self.write(cr, uid, ids, {'state':'pick_exception'}, context=context)
    
    def action_done(self, cr, uid, ids, context=None):
        for mtr_ind in self.browse(cr, uid, ids, context=context):
            if mtr_ind.asset_requisition_id:
                self.pool.get('asset.requisition').action_done(cr, uid, [mtr_ind.asset_requisition_id.id], context=context)
        return self.write(cr, uid, ids, {'state':'done'}, context=context)
    
    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        for mtr_ind in self.browse(cr, uid, ids, context=context):
            if mtr_ind.shop_id and mtr_ind.shop_id.id:
                shop_mgr_id=mtr_ind.shop_id.manager_id and mtr_ind.shop_id.manager_id.partner_id.id
                post_values = {
                                'partner_ids': [shop_mgr_id],
                                'subject':"Request From outlet %s For Material Is Cancelled"%(mtr_ind.shop_id.name),
                                'body':"Request from outlet %s to sector %s for Material is Cancelled. For more details please check %s"%(mtr_ind.shop_id.name,mtr_ind.sector_id.name,mtr_ind.name)
                                }
                msg_id = self.message_post(cr, uid, [mtr_ind.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            else:
                emp_id = mtr_ind.employee_id.user_id and mtr_ind.employee_id.user_id.partner_id.id
                post_values = {
                                'partner_ids': [emp_id],
                                'subject':"Request  For Material From Employee %s Is Cancelled"%(mtr_ind.employee_id.name),
                                'body':"Request from Employee %s  for Material Is Cancelled. For more details please check %s"%(mtr_ind.employee_id.name,mtr_ind.name)
                                }
                msg_id = self.message_post(cr, uid, [mtr_ind.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
        return True    
    
MaterialIndentation()


class IndentationLines(osv.osv):
    
    _name = 'material.indentation.line'
    _description = 'Material Indentation Line'
    _columns = {
                'name':fields.char('Description',size=120),
                'product_id':fields.many2one('product.product','Product'),
                'quantity':fields.float('Quantity'),
                'uom_id':fields.many2one('product.uom','UOM'),
                'dest_location_id':fields.many2one('stock.location','Destination Location'),
                'indentation_id':fields.many2one('material.indentation','Indentation'),
                'warehouse_id':fields.many2one('stock.warehouse','Warehouse'),
                'prod_type':fields.selection([('inventory','Inventory')
                                                 ,('non-inventory','Non Inventory')
                                                 ,('asset','Asset')
                                                 ,('service','service')], string="Product Type"),
                }
    
    _defaults = {
                 'quantity':1.0,
                 }
    
    def onchange_product(self, cr, uid, ids, product_id, warehouse_id, context=None):
        res = {}
        loc_ids = []
        if not product_id:
            return res
        if warehouse_id:
            loc_ids = [[w.lot_stock_id.id,w.wh_input_stock_loc_id.id,w.wh_qc_stock_loc_id.id,w.wh_output_stock_loc_id.id,w.wh_pack_stock_loc_id.id] for w in self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)]
        loc_ids = loc_ids and loc_ids[0]
        pro_pool = self.pool.get('product.product')
        pro_data = pro_pool.read(cr, uid, product_id, ['uom_id','standard_price','product_type'], context=context)
        res['value'] = {'uom_id':pro_data['uom_id'][0],
                        'name':pro_pool.name_get(cr, uid, [product_id], context=context)[0][1], 'prod_type':pro_data['product_type']}
        res['domain'] = {'dest_location_id': [('id','in',loc_ids)]}
        return res
    
    
IndentationLines()