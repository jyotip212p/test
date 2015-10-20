from openerp.osv import osv, fields
import time
from openerp import models, api
from openerp import fields as new_fields
from openerp.tools.translate import _

class StockWarehouse(osv.osv):
    
    _inherit = 'stock.warehouse'
    
    _columns = {
                'loc_asset_id':fields.many2one('stock.location','Asset Location'),
                'user_id':fields.many2one('res.users','Owner'),                
                'main_warehouse':fields.boolean('Main Warehouse'),
                }
    
    def _check_main_warehouse(self, cr, uid, ids, context=None):
        for war in self.browse(cr, uid, ids, context=context):
            company_id = war.company_id.id
            war_ids = self.search(cr, uid, [('main_warehouse','=',True),('company_id','=',company_id)])
            if len(war_ids) > 1:
                return False
        return True
    
    _constraints = [(_check_main_warehouse,"A company will have only one Main warehouse", ['main_warehouse'])]

    def _get_main_warehouse(self, cr, uid, context=None):
        res = {}
        main_warehouse_id = self.pool.get('stock.warehouse').search(cr,uid, [('main_warehouse','=',True)])
        if not main_warehouse_id:
            return False
        return main_warehouse_id and main_warehouse_id[0]
        
    def create(self, cr, uid, vals, context=None):
        id = super(StockWarehouse, self).create(cr, uid, vals, context=context)
        war_data = self.read(cr, uid, id, ['company_id','view_location_id'], context=context)
        loc_vals = {
                    'name':'Asset',
                    'usage': 'internal',
                    'location_id': war_data['view_location_id'][0],
                    'active': True,
                    'company_id':war_data['company_id'][0],
                    }
        asset_loc_id = self.pool.get('stock.location').create(cr, uid, loc_vals, context=context)
        self.write(cr, uid, [id], {'loc_asset_id':asset_loc_id}, context=context)
        return id
    
StockWarehouse()


class StockPicking(osv.osv):
    
    _inherit = 'stock.picking'
    
    _order = "date desc, id desc, priority desc"
    
    _columns = {
                'indentation_id':fields.many2one('material.indentation','Indentation'),
                'asset_requisition_id':fields.many2one('asset.requisition','Asset Requisition'),
                'approved':fields.boolean('Approved'),
                }
    
    def approve_receipt(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [record.id], {'approved':True}, context=context)
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        res = super(StockPicking, self).action_cancel(cr, uid, ids, context=context)
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.indentation_id:
                self.pool.get('material.indentation').pick_exception(cr, uid, [pick.indentation_id.id], context=context)
        return res
    
    def do_transfer(self, cr, uid, ids, context=None):
        res = super(StockPicking, self).do_transfer(cr, uid, ids, context=context)
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.indentation_id:
                self.pool.get('material.indentation').action_done(cr, uid, [pick.indentation_id.id], context=context)
            if pick.asset_requisition_id:
                self.pool.get('asset.requisition').action_done(cr, uid, [pick.asset_requisition_id.id], context=context)
        return res
    
StockPicking()


class StockReturnPicking(osv.osv_memory):
    
    _inherit = 'stock.return.picking'
    
    def _create_returns(self, cr, uid, ids, context=None):
        res = super(StockReturnPicking, self)._create_returns(cr, uid, ids, context=context)
        if context.get('asset_requisition_id',False):
            self.pool.get('stock.picking').write(cr, uid, [res[0]], {'asset_requisition_id':context.get('asset_requisition_id',False)}, context=context)
        return res
    
StockReturnPicking()


class StockMove(osv.osv):
    
    _inherit = 'stock.move'
    
    _columns = {
                'prod_type':fields.selection([('inventory','Inventory')
                                                 ,('non-inventory','Non Inventory')
                                                 ,('asset','Asset')
                                                 ,('service','service')], string="Product Type"),
                'asset_serial_no':fields.char('Asset Serial No',size=24),
                'picking_type_code': fields.related('picking_type_id', 'code', type='char', string='Picking Type Code',store=True, help="Technical field used to display the correct label on print button in the picking view"),
                }
    
    _defaults = {
                 'prod_type':'inventory',
                 }
    
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):
        """ On change of product id, if finds UoM, UoS, quantity and UoS quantity.
        @param prod_id: Changed Product id
        @param loc_id: Source location id
        @param loc_dest_id: Destination location id
        @param partner_id: Address id of partner
        @return: Dictionary of values
        """
        if not prod_id:
            return {}
        user = self.pool.get('res.users').browse(cr, uid, uid)
        lang = user and user.lang or False
        if partner_id:
            addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        ctx = {'lang': lang}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
        uos_id = product.uos_id and product.uos_id.id or False
        result = {
            'name': product.partner_ref,
            'product_uom': product.uom_id.id,
            'product_uos': uos_id,
            'prod_type':product.product_type,
            'product_uom_qty': 1.00,
            'product_uos_qty': self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id)['value']['product_uos_qty'],
        }
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}
    
    
StockMove()


class make_procurement(osv.osv_memory):
    _inherit = 'make.procurement'
    _description = 'Make Procurements'
    
    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        if context.has_key('product_id'):
            context['active_id'] = context.get('product_id')
        record_id = context.get('active_id')
        if context.get('active_model') == 'product.template':
            product_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id', '=', context.get('active_id'))], context=context)
            if len(product_ids) == 1:
                record_id = product_ids[0]
            else:
                raise orm.except_orm(_('Warning'), _('Please use the Product Variant vue to request a procurement.'))

        res = super(make_procurement, self).default_get(cr, uid, fields, context=context)
        if context.has_key('qty'):
            res['qty'] = context.get('qty')
        if record_id and 'product_id' in fields:
            proxy = self.pool.get('product.product')
            product_ids = proxy.search(cr, uid, [('id', '=', record_id)], context=context, limit=1)
            if product_ids:
                product_id = product_ids[0]

                product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
                res['product_id'] = product.id
                res['uom_id'] = product.uom_id.id

        if 'warehouse_id' in fields:
            warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)
            res['warehouse_id'] = warehouse_id[0] if warehouse_id else False

        return res

make_procurement()

class StockMoveScrap(osv.osv_memory):
    
    _inherit = 'stock.move.scrap'
    
    _columns = {
                'prod_type':fields.selection([('inventory','Inventory')
                                                 ,('non-inventory','Non Inventory')
                                                 ,('asset','Asset')
                                                 ,('service','service')], string="Product Type"),
                }
    
    def default_get(self, cr, uid, fields, context=None):
        """ Get default values
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for default value
        @param context: A standard dictionary
        @return: default values of fields
        """
        if context is None:
            context = {}
        res = super(StockMoveScrap, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)

        location_obj = self.pool.get('stock.location')
        scrap_location_id = location_obj.search(cr, uid, [('scrap_location','=',True)])
        res.update({'prod_type':move.prod_type})

        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'location_id' in fields:
            if scrap_location_id:
                res.update({'location_id': scrap_location_id[0]})
            else:
                res.update({'location_id': False})
        return res
    
StockMoveScrap()

class stock_transfer_details(models.TransientModel):
    _inherit = "stock.transfer_details"
    
    asset_transfer = new_fields.Boolean('Asset Transfer Included')
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(stock_transfer_details, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        items = []
        packs = []
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
        lot_id = False
        for op in picking.pack_operation_ids:
            for qty in range(0, int(op.product_qty)):
                if picking.picking_type_code == 'incoming':            
                    vals = {'product_id':op.product_id.id}
                    lot_id = self.pool.get('stock.production.lot').create(cr, uid, vals, context=context)
                item = {
                    'packop_id': False,
                    'product_id': op.product_id.id,
                    'product_uom_id': op.product_uom_id.id,
                    'quantity': 1.0,
                    'package_id': op.package_id.id,
                    'lot_id': lot_id or op.lot_id.id,
                    'sourceloc_id': op.location_id.id,
                    'destinationloc_id': op.location_dest_id.id,
                    'result_package_id': op.result_package_id.id,
                    'date': op.date, 
                    'owner_id': op.owner_id.id,
                }
                if op.product_id:
                    items.append(item)
                elif op.package_id:
                    packs.append(item)
        res.update(item_ids=items)
        res.update(packop_ids=packs)
        return res
    
    @api.one
    def do_detailed_transfer(self):
        processed_ids = []
        lot_ids = []
        # Create new and update existing pack operations
        for lstits in [self.item_ids, self.packop_ids]:
            for prod in lstits:
                pack_datas = {
                    'product_id': prod.product_id.id,
                    'product_uom_id': prod.product_uom_id.id,
                    'product_qty': prod.quantity,
                    'package_id': prod.package_id.id,
                    'lot_id': prod.lot_id.id,
                    'location_id': prod.sourceloc_id.id,
                    'location_dest_id': prod.destinationloc_id.id,
                    'result_package_id': prod.result_package_id.id,
                    'date': prod.date if prod.date else datetime.now(),
                    'owner_id': prod.owner_id.id,
                }
                
                #Validate Serial Numbers
                if not prod.lot_id:
                    osv.except_osv(_('ERROR'),_("Please select the serial Number"))
                if self.picking_id.picking_type_id.code == 'incoming':
                    prod.lot_id.confirm_lot()
                if prod.packop_id:
                    prod.packop_id.write(pack_datas)
                    processed_ids.append(prod.packop_id.id)
                else:
                    pack_datas['picking_id'] = self.picking_id.id
                    packop_id = self.env['stock.pack.operation'].create(pack_datas)
                    processed_ids.append(packop_id.id)
        
        # Delete the others
        packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', self.picking_id.id), '!', ('id', 'in', processed_ids)])
        for packop in packops:
            packop.unlink()

        # Execute the transfer of the picking
        self.picking_id.do_transfer()

        return True
    
    
stock_transfer_details()


class StockProductionLot(osv.osv):
    
    _inherit = 'stock.production.lot'
    
    _columns = {
                'state':fields.selection([('draft','New'),('valid','Valid')],string='Status')
                }
    
    _defaults = {
                 'name':'Tentative-Sl.no',
                 'state':'draft',
                 }
    
    def confirm_lot(self, cr, uid, ids, context=None):
        for ser in self.browse(cr, uid, ids, context=context):
            name = self.pool.get('ir.sequence').get(cr, uid, 'stock.lot.serial')
            p_code = ser.product_id.default_code or ''
            c_code = ser.product_id.categ_id.code or ''
            self.write(cr, uid, [ser.id], {'state':'valid','name':c_code+'/'+p_code+'/'+name}, context=context)
        return True
    
StockProductionLot()

class stock_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'
    _description = 'Picking wizard items'
    
    prod_type = new_fields.Selection([('inventory','Inventory')
                                                 ,('non-inventory','Non Inventory')
                                                 ,('asset','Asset')
                                                 ,('service','service')], string="Product Type")

    
stock_transfer_details_items()

class stock_location(osv.osv):
    
    _inherit = 'stock.location'
    
    _rec_name = 'name'
    
stock_location()