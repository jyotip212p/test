from openerp.osv import osv, fields
import time


class res_partner(osv.osv):
    
    _inherit = 'res.partner'
    
    _columns = {
                'property_account_payable': fields.many2one('account.account',
                    string="Account Payable",
                    domain="[('type', '=', 'payable')]",
                    help="This account will be used instead of the default one as the payable account for the current partner",
                    required=False),
                'property_account_receivable': fields.many2one('account.account',
                    string="Account Receivable",
                    domain="[('type', '=', 'receivable')]",
                    help="This account will be used instead of the default one as the receivable account for the current partner",
                    required=False),
                }
    
res_partner()