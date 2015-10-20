from openerp.osv import osv, fields
import time
from openerp.tools.translate import _


class SaleOrder(osv.osv):
    
    _inherit = 'sale.order'
    
    _columns = {
                'shop_id':fields.many2one('sale.shop','Shop'),
                'sector_id':fields.related('shop_id','sector_id',type='many2one',relation='sale.sector',string='Sector'),   
                }
    
    def _get_shop(self, cr, uid, context=None):
        shop_id = self.pool.get('sale.shop').search(cr, uid, [('manager_id','=',uid)])
#         if not shop_id:
#             raise osv.except_osv(_("ERROR !!"),_("Sorry no outlets are assigned to you. Please contact Administrator."))
        return shop_id and shop_id[0] or False
    
    def _get_warehouse(self, cr, uid, context=None):
        shop_id = self._get_shop(cr, uid, context=context)
        if shop_id:
            warehouse_id = self.pool.get('sale.shop').read(cr, uid, shop_id, ['warehouse_id'], context=context)['warehouse_id']
            return warehouse_id and warehouse_id[0] or False
        return False
            
    
    _defaults = {
                 'shop_id':_get_shop,
                 'warehouse_id':_get_warehouse,
                 }
    
    def onchange_shop(self, cr, uid, ids, shop_id, context=None):
        res = {}
        if not shop_id:
            return res
        warning_msgs = False
        warehouse_id = self.pool.get('sale.shop').read(cr, uid, shop_id, ['warehouse_id'], context=context)['warehouse_id']
        if warehouse_id is False:
            warning_msgs = _("There is no corresponding warehouse found for this shop")
        if warning_msgs:
            warning = {
                       'title':_('Configuration Error !!'),
                       'message':warning_msgs
                       }
            res.update({'warning':warning})
        res['value'] = {'warehouse_id':warehouse_id and warehouse_id[0]}
        return res
    
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        """Prepare the dict of values to create the new invoice for a
           sales order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: sale.order record to invoice
           :param list(int) line: list of invoice line IDs that must be
                                  attached to the invoice
           :return: dict of value to create() the invoice
        """
        if context is None:
            context = {}
        journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'sale'), ('company_id', '=', order.company_id.id)],
            limit=1)
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
                _('Please define sales journal for this company: "%s" (id:%d).') % (order.company_id.name, order.company_id.id))
        invoice_vals = {
            'name': order.client_order_ref or '',
            'origin': order.name,
            'type': 'out_invoice',
            'reference': order.client_order_ref or order.name,
            'account_id': order.partner_id.property_account_receivable.id,
            'partner_id': order.partner_invoice_id.id,
            'journal_id': journal_ids[0],
            'invoice_line': [(6, 0, lines)],
            'currency_id': order.pricelist_id.currency_id.id,
            'comment': order.note,
            'payment_term': order.payment_term and order.payment_term.id or False,
            'fiscal_position': order.fiscal_position.id or order.partner_id.property_account_position.id,
            'date_invoice': context.get('date_invoice', False),
            'company_id': order.company_id.id,
            'user_id': order.user_id and order.user_id.id or False,
            'section_id' : order.section_id.id,
            'sector_id':order.sector_id.id
        }

        # Care for deprecated _inv_get() hook - FIXME: to be removed after 6.1
        invoice_vals.update(self._inv_get(cr, uid, order, context=context))
        return invoice_vals
    
SaleOrder()