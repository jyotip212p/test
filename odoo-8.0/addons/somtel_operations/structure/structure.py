from openerp.osv import osv, fields
import time
from openerp.tools.translate import _


class SaleSector(osv.osv):
    
    _name = 'sale.sector'
    _description = 'Sectors'
    _columns = {
                'name':fields.char('Name',size=64,required=True),
                'code':fields.char('Code',size=10,required=True),
                'company_id':fields.many2one('res.company','Company',required=True),
                'active':fields.boolean('Active'),
                'shop_lines':fields.one2many('sale.shop','sector_id','Shops'),
                'manager_id':fields.many2one('res.users','Sector Commercial Manager',required=True),
                'warehouse_id':fields.many2one('stock.warehouse','Warehouse',required=True),
                }
    
    _defaults = {
                 'active':True,
                 'company_id': lambda s, cr, uid, c :s.pool.get('res.company')._company_default_get(cr, uid, 'sale.sectors', context=c),
                 }
    
    _sql_constraints = [('sector_code_unique','UNIQUE (code,company_id)', 'Code must be Unique for the Sectors')]
    
    def create(self, cr ,uid, vals, context=None):
        id = super(SaleSector, self).create(cr, uid, vals, context=context)
#         vals.update({'sector_id':id})
#         vals.update({'sector_shop':True})
#         self.pool.get('sale.shop').create(cr, uid, vals, context=context)
        return id
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        res = super(SaleSector, self).write(cr, uid, ids, vals, context=context)
#         for sector in self.browse(cr, uid, ids, context=context):
#             sector_shop = self.pool.get('sale.shop').search(cr, uid, [('sector_shop','=',True),('sector_id','=',sector.id)])
#             if not sector_shop:
#                 continue
#             context = context.update({'sector_update':True})
#             self.pool.get('sale.shop').write(cr, uid, sector_shop, vals, context=context)
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'active':False}, context=context)

    def view_all_locations(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing stocks by location of sector warehouse.
        '''
        loc_ids = []
        for sector in self.browse(cr, uid, ids, context=context):
            w = sector.warehouse_id
            if w:
                loc_ids = [w.lot_stock_id.id,w.wh_input_stock_loc_id.id,w.wh_qc_stock_loc_id.id,w.wh_output_stock_loc_id.id,w.wh_pack_stock_loc_id.id]
        domain = [('id', 'in', loc_ids)]
        return {
            'name': ('Locations'),
            'domain': domain,
            'res_model': 'stock.location',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'limit': 20
        }
    
SaleSector()


class SaleShop(osv.osv):
    
    _name = 'sale.shop'
    _description = 'Shops'
    _columns = {
                'name':fields.char('Name',size=64,required=True),
                'code':fields.char('Code',size=10,required=True),
                'sector_id':fields.many2one('sale.sector','Sector',required=True),
                'active':fields.boolean('Active'),
                'company_id':fields.many2one('res.company','Company',required=True),
                'manager_id':fields.many2one('res.users','Outlet Manager',required=True),
                'warehouse_id':fields.many2one('stock.warehouse','Warehouse',required=True),
                'sector_shop':fields.boolean('Shop'),
                }
    
    _defaults = {
                 'active':True,
                 'company_id': lambda s, cr, uid, c :s.pool.get('res.company')._company_default_get(cr, uid, 'sale.shop', context=c),
                 }
    
    _sql_constraints = [('shop_code_unique','UNIQUE (code,sector_id)', 'Code must be Unique for the Outlets')]
    
    def unlink(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'active':False}, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        for shop in self.browse(cr, uid, ids, context=context):
            if (not context.has_key('sector_update')) and shop.sector_shop:
                raise osv.except_osv(_('ERROR !!'),_('Sorry, you cannot edit this directly. Please update related sector data.'))
        return super(SaleShop, self).write(cr, uid, ids, vals, context=context)
    
    def view_all_locations(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing stocks by location of shop warehouse.
        '''
        loc_ids = []
        for shop in self.browse(cr, uid, ids, context=context):
            w = shop.warehouse_id
            if w:
                loc_ids = [w.lot_stock_id.id,w.wh_input_stock_loc_id.id,w.wh_qc_stock_loc_id.id,w.wh_output_stock_loc_id.id,w.wh_pack_stock_loc_id.id]
        domain = [('id', 'in', loc_ids)]
        return {
            'name': ('Locations'),
            'domain': domain,
            'res_model': 'stock.location',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'limit': 20
        }

SaleShop()

class SaleBranch(osv.osv):
    
    _name = 'sale.branch'
    _description = 'Branches'
    _inherit = ['mail.thread']
    
    _columns = {
                'name':fields.char('Name', size=120, required=True),
                'sector_id':fields.many2one('sale.sector', 'Sector'),
                'company_id':fields.many2one('res.company', 'Company'),
                }
    
    _sql_constraints = [('branch_name_unique','UNIQUE (name)', 'Name must be Unique for the Branches')]
    
    _defaults = {
                 'company_id': lambda s, cr, uid, c :s.pool.get('res.company')._company_default_get(cr, uid, 'sale.branch', context=c),
                 }
    
SaleBranch()