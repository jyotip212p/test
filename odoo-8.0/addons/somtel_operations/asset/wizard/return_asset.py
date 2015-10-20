from openerp.osv import osv, fields
import time
from openerp.tools.translate import _


class ReturnAsset(osv.osv_memory):
    
    _name = 'return.asset'
    
    _description = 'Return Assets'
    
    _columns = {
                'product_id':fields.many2one('product.product','Product'),
                'quantity':fields.float('Quantity'),
                'asset_requisition_id':fields.many2one('asset.requisition','Asset Ref'),
                'reason':fields.char('Reason',size=264),
                }
    
    def confirm(self, cr, uid, ids, context=None):
        for ret in self.browse(cr, uid, ids, context=context):
            ret_asset_data = self.pool.get('asset.requisition').copy_data(cr, uid, ret.asset_requisition_id.id, context=context)
            print ret_asset_data
            ret_asset_data['type'] = 'out'
            ret_asset_data['date'] = time.strftime("%Y-%m-%d")
            ret_asset_data['reason'] = str(ret.reason)
            ret_id = self.pool.get('asset.requisition').create(cr, uid, ret_asset_data, context=context)
            self.pool.get('asset.requisition').action_submit(cr, uid, [ret_id], context=context)
            self.pool.get('asset.requisition').write(cr, uid, [ret.asset_requisition_id.id], {'return_id':ret_id})
        return True
    
ReturnAsset()