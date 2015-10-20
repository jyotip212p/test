from openerp.osv import osv, fields
import time
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import openerp

class procurement_order(osv.osv):
    
    _inherit = 'procurement.order'
    
    _columns = {
                'employee_id':fields.many2one('hr.employee','Employee', states={'draft': [('readonly', False)]}, readonly=True),
                'department_id':fields.related('employee_id', 'department_id', type='many2one', relation='hr.department', string='Department'),
                'product_id': fields.many2one('product.product', 'Product', required=True, states={'draft': [('readonly', False)]}, readonly=True),
                'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, states={'draft': [('readonly', False)]}, readonly=True),
                'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, states={'draft': [('readonly', False)]}, readonly=True),
                'product_uos_qty': fields.float('UoS Quantity', states={'draft': [('readonly', False)]}, readonly=True),
                'product_uos': fields.many2one('product.uom', 'Product UoS', states={'draft': [('readonly', False)]}, readonly=True),
                'state': fields.selection([
                        ('draft','Draft'),
                        ('waiting','Waiting'),
                        ('cancel', 'Cancelled'),
                        ('confirmed', 'Confirmed'),
                        ('exception', 'Exception'),
                        ('running', 'Running'),
                        ('done', 'Done')
                    ], 'Status', required=True, track_visibility='onchange', copy=False),
                }
    
    def _get_employee(self, cr, uid, context=None):
        emp_pool = self.pool.get('hr.employee')
        emp_id = emp_pool.search(cr, uid, [('user_id','=',uid)])
        return emp_id and emp_id[0] or False
    
    def _get_buy_route(self, cr, uid, context=None):
        
        buy_route = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'purchase.route_warehouse0_buy')
        if buy_route:
            return [buy_route]
        return []
    
    _defaults = {
                 'state':'draft',
                 'employee_id':lambda s, cr, uid, c:s._get_employee(cr, uid, c),
                 'route_ids': _get_buy_route,
                 'warehouse_id':lambda s,cr, uid, c:s.pool.get('stock.warehouse')._get_main_warehouse(cr, uid, context=c)
                 }
    
    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        res = {}
        if not employee_id:
            return res
        emp_pool = self.pool.get('hr.employee')
        emp_data = emp_pool.read(cr, uid, employee_id, ['department_id'], context=context)
        if not emp_data['department_id']:
            warning_msg = _('Employee is linked to department, Contact Administrator.')
            warnings = _('No Related Department \n') + warning_msg + '\n\n'
            if warnings:
                warning = {
                           'title':_('Configuration ERROR !!'),
                           'message':warnings
                           }
                return {'warning':warning, 'value':{'department_id':False, 'product_id':False}}
        res['value'] = {'department_id':emp_data['department_id'][0]}
        print "LLLLLLLLLLLLLLLLLLLLLLLLLLLLLL", res
        return res
    
    def action_submit(self, cr, uid, ids, context=None):
        print "NNNNNNNNNNNNNNNNNNNNNNNNNN"
        for record in self.browse(cr, uid, ids, context=context):
            if not record.department_id:
                raise osv.except_osv(_('ERROR !!'), _('Please select the employee department.'))
            manager_id =self.pool.get('hr.department').browse(cr,uid,record.department_id.id,context=context).manager_id.user_id.partner_id.id
            if manager_id:
                 post_values = {
                                'partner_ids': [manager_id],
                               'subject':"Procurement request for %s " %(record.product_id.name),
                               'body':" Procurement request for %s is raised by %s and is waiting for approval." %(record.product_id.name,record.employee_id.name)
                               }  
                 msg_id = self.message_post(cr, uid,[record.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
            self.write(cr, uid, [record.id], {'state':'waiting'}, context=context)
        print "JJJJJJJJJJJJJJJJJjjjjj"
        return True
    
    def action_confirm(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            part_ids=[]
            pur_usr_ids = self.pool.get('res.groups').search(cr, uid, [('category_id','=','Purchases'),('name','=','User')])
            if pur_usr_ids:
                for grp in pur_usr_ids:
                    grp_obj = self.pool.get('res.groups').browse(cr, uid, grp, context=context)
                    part_ids = [usr.partner_id.id for usr in grp_obj.users]
                    if part_ids:
                         post_values = {
                                        'partner_ids': part_ids,
                                       'subject':"Procurement Request for %s is confirmed." %(record.product_id.name),
                                       'body':"Procurement Request for %s is confirmed. Kindly Process the Request." %(record.product_id.name)
                                       }
                         msg_id = self.message_post(cr, uid,[record.id], type='comment', subtype='mail.mt_comment', context=context, **post_values)
        return self.write(cr, uid, ids, {'state':'confirmed'}, context=context)
    
    
    def make_po(self, cr, uid, ids, context=None):
        """ Resolve the purchase from procurement, which may result in a new PO creation, a new PO line creation or a quantity change on existing PO line.
        Note that some operations (as the PO creation) are made as SUPERUSER because the current user may not have rights to do it (mto product launched by a sale for example)

        @return: dictionary giving for each procurement its related resolving PO line.
        """
        res = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        po_obj = self.pool.get('purchase.order')
        po_line_obj = self.pool.get('purchase.order.line')
        seq_obj = self.pool.get('ir.sequence')
        pass_ids = []
        linked_po_ids = []
        sum_po_line_ids = []
        for procurement in self.browse(cr, uid, ids, context=context):
            partner = self._get_product_supplier(cr, uid, procurement, context=context)
            if not partner:
                raise osv.except_osv(_('ERROR !!'),_('No supplier defined for this product. Please add a supplier in product form. Then Run the procurement.'))
                self.message_post(cr, uid, [procurement.id], _('There is no supplier associated to product %s') % (procurement.product_id.name))
                res[procurement.id] = False
            else:
                schedule_date = self._get_purchase_schedule_date(cr, uid, procurement, company, context=context)
                purchase_date = self._get_purchase_order_date(cr, uid, procurement, company, schedule_date, context=context) 
                line_vals = self._get_po_line_values_from_proc(cr, uid, procurement, partner, company, schedule_date, context=context)
                #look for any other draft PO for the same supplier, to attach the new line on instead of creating a new draft one
                available_draft_po_ids = po_obj.search(cr, uid, [
                    ('partner_id', '=', partner.id), ('state', '=', 'draft'), ('picking_type_id', '=', procurement.rule_id.picking_type_id.id),
                    ('location_id', '=', procurement.location_id.id), ('company_id', '=', procurement.company_id.id), ('dest_address_id', '=', procurement.partner_dest_id.id)], context=context)
                if available_draft_po_ids:
                    po_id = available_draft_po_ids[0]
                    po_rec = po_obj.browse(cr, uid, po_id, context=context)
                    #if the product has to be ordered earlier those in the existing PO, we replace the purchase date on the order to avoid ordering it too late
                    if datetime.strptime(po_rec.date_order, DEFAULT_SERVER_DATETIME_FORMAT) > purchase_date:
                        po_obj.write(cr, uid, [po_id], {'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
                    #look for any other PO line in the selected PO with same product and UoM to sum quantities instead of creating a new po line
                    available_po_line_ids = po_line_obj.search(cr, uid, [('order_id', '=', po_id), ('product_id', '=', line_vals['product_id']), ('product_uom', '=', line_vals['product_uom'])], context=context)
                    if available_po_line_ids:
                        po_line = po_line_obj.browse(cr, uid, available_po_line_ids[0], context=context)
                        po_line_obj.write(cr, SUPERUSER_ID, po_line.id, {'product_qty': po_line.product_qty + line_vals['product_qty']}, context=context)
                        po_line_id = po_line.id
                        sum_po_line_ids.append(procurement.id)
                    else:
                        line_vals.update(order_id=po_id)
                        po_line_id = po_line_obj.create(cr, SUPERUSER_ID, line_vals, context=context)
                        linked_po_ids.append(procurement.id)
                else:
                    name = seq_obj.get(cr, uid, 'purchase.order') or _('PO: %s') % procurement.name
                    po_vals = {
                        'name': name,
                        'origin': procurement.origin,
                        'partner_id': partner.id,
                        'location_id': procurement.location_id.id,
                        'picking_type_id': procurement.rule_id.picking_type_id.id,
                        'pricelist_id': partner.property_product_pricelist_purchase.id,
                        'currency_id': partner.property_product_pricelist_purchase and partner.property_product_pricelist_purchase.currency_id.id or procurement.company_id.currency_id.id,
                        'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'company_id': procurement.company_id.id,
                        'fiscal_position': partner.property_account_position and partner.property_account_position.id or False,
                        'payment_term_id': partner.property_supplier_payment_term.id or False,
                        'dest_address_id': procurement.partner_dest_id.id,
                    }
                    po_id = self.create_procurement_purchase_order(cr, SUPERUSER_ID, procurement, po_vals, line_vals, context=context)
                    po_line_id = po_obj.browse(cr, uid, po_id, context=context).order_line[0].id
                    pass_ids.append(procurement.id)
                res[procurement.id] = po_line_id
                self.write(cr, uid, [procurement.id], {'purchase_line_id': po_line_id}, context=context)
        if pass_ids:
            self.message_post(cr, uid, pass_ids, body=_("Draft Purchase Order created"), context=context)
        if linked_po_ids:
            self.message_post(cr, uid, linked_po_ids, body=_("Purchase line created and linked to an existing Purchase Order"), context=context)
        if sum_po_line_ids:
            self.message_post(cr, uid, sum_po_line_ids, body=_("Quantity added in existing Purchase Order Line"), context=context)
        return res
    
    
procurement_order()