from openerp.osv import osv, fields
import time

class ProductProduct(osv.osv):
    
    _inherit = 'product.product'
    
    _defaults = {
                 'type':'product',
                 }
    
    def onchange_product_type(self, cr, uid, ids, product_type, context=None):
        res = {}
        type = 'service'
        track_all = False
        if product_type in ('inventory','non-inventory','asset'):
            type = 'product'
        if product_type in ('inventory','asset'):
            track_all = True
        res.update({'value':{'type':type,'track_all':track_all}})
        return res
    
    def onchange_account(self, cr, uid, ids, account, context=None):
        res = {}
        value = {'property_account_income':account, 'property_account_expense':account}
        print "KKKKKKKKKKKKKKKKKKKKKKKKKKK",value
        return {'value':value}
    
    
    def _get_domain_locations(self, cr, uid, ids, context=None):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, force_company, compute_child
        '''
        context = context or {}

        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')

        location_ids = []
        wids = []
        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                domain = [('complete_name','ilike',context['location'])]
                if context.get('force_company', False):
                    domain += [('company_id', '=', context['force_company'])]
                location_ids = location_obj.search(cr, uid, domain, context=context)
            else:
                location_ids = context['location']
        else:
            if context.get('warehouse', False):
                wids = [context['warehouse']]
            else:
                if context.get('uid',False):
                    sector_ids = self.pool.get('sale.sector').search(cr, uid, [('manager_id','=',context['uid'])], context=context)
                    if sector_ids:
                        for sector in self.pool.get('sale.sector').browse(cr, uid, sector_ids):
                            wids.append(sector.warehouse_id.id)
                    if not wids:
                        shop_ids = self.pool.get('sale.shop').search(cr, uid, [('manager_id','=',context['uid'])], context=context)
                        if shop_ids:
                            for shop in self.pool.get('sale.shop').browse(cr, uid, shop_ids):
                                wids.append(shop.warehouse_id.id)
                    if not wids:
                        wids = warehouse_obj.search(cr, uid, [], context=context)
                        

            for w in warehouse_obj.browse(cr, uid, wids, context=context):
                location_ids.append(w.view_location_id.id)

        operator = context.get('compute_child', True) and 'child_of' or 'in'
        domain = context.get('force_company', False) and ['&', ('company_id', '=', context['force_company'])] or []
        return (
            domain + [('location_id', operator, location_ids)],
            domain + ['&', ('location_dest_id', operator, location_ids), '!', ('location_id', operator, location_ids)],
            domain + ['&', ('location_id', operator, location_ids), '!', ('location_dest_id', operator, location_ids)]
        )
    
ProductProduct()

class ProductTemplate(osv.osv):
    
    _name = 'product.template'
    _inherit = 'product.template'
    
    _defaults = {
                 'type':'product',
                 }
    
    _columns = {
                'property_lines':fields.one2many('product.property','product_tmpl_id','Properties'),
                'product_type':fields.selection([('inventory','Inventory')
                                                 ,('non-inventory','Non Inventory')
                                                 ,('asset','Asset')
                                                 ,('service','service')], string="Product Type"),
                'account_id':fields.many2one('account.account','Account'),
                }
    
    def onchange_product_type(self, cr, uid, ids, product_type, context=None):
        res = {}
        type = 'service'
        track_all = False
        if product_type in ('inventory','non-inventory','asset'):
            type = 'product'
        if product_type in ('inventory','asset'):
            track_all = True
        res.update({'value':{'type':type,'track_all':track_all}})
        return res
    
    def onchange_account(self, cr, uid, ids, account, context=None):
        res = {}
        value = {'property_account_income':account, 'property_account_expense':account}
        print "KKKKKKKKKKKKKKKKKKKKKKKKKKK",value
        return {'value':value}
    
ProductTemplate()

class Property(osv.osv):
    
    _name = 'property.property'
    _description = 'Properties'
    _inherit = ['mail.thread','ir.needaction_mixin']
    
    _columns = {
                'name':fields.char('Name',size=64),
                }
    
Property()

class ProductProperty(osv.osv):
    
    _name = 'product.property'
    _description = 'Product Properties'
    
    _columns = {
                'product_tmpl_id':fields.many2one('product.template','Product'),
                'property_id':fields.many2one('property.property','Property'),
                'required':fields.boolean('Required ?'),
                'unique':fields.boolean('Unique ?'),
                }
    
ProductProperty()

class ProductCategory(osv.osv):
    
    _inherit = 'product.category'
    
    _columns = {
                'code':fields.char('Code',size=10),
                'company_id':fields.many2one('res.company','Company'),
                }
    
    _defaults = {
                 'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'product.category', context=c),
                 }
    
ProductCategory()