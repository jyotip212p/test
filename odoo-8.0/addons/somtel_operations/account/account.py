from openerp.osv import osv, fields
import time
from openerp.tools.translate import _
from datetime import datetime
import openerp
from openerp import api
from openerp import fields as new_fields

class AccountInvoiceLine(osv.osv):
    
    _inherit = 'account.invoice.line'
    
    _columns = {
                'prod_type':fields.selection([('inventory','Inventory')
                                                 ,('non-inventory','Non Inventory')
                                                 ,('asset','Asset')
                                                 ,('service','service')], string="Product Type"),
                'general_budget_id':fields.many2one('account.budget.post','Budgetary Position'),
                'account_id':fields.many2one('account.account', string="Account", required=False, domain=[('type', 'not in', ['view', 'closed'])],
                                            help="The income or expense account related to the selected product."),
                }
    
    _defaults = {
                 'account_id':False
                 }
    
    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):
        context = self._context
        company_id = company_id if company_id is not None else context.get('company_id', False)
        self = self.with_context(company_id=company_id, force_company=company_id)

        if not partner_id:
            raise except_orm(_('No Partner Defined!'), _("You must first select a partner!"))
        if not product:
            if type in ('in_invoice', 'in_refund'):
                return {'value': {}, 'domain': {'product_uom': []}}
            else:
                return {'value': {'price_unit': 0.0}, 'domain': {'product_uom': []}}

        values = {}

        part = self.env['res.partner'].browse(partner_id)
        fpos = self.env['account.fiscal.position'].browse(fposition_id)

        if part.lang:
            self = self.with_context(lang=part.lang)
        product = self.env['product.product'].browse(product)

        values['name'] = product.partner_ref
        values['prod_type'] = product.product_type
        if type in ('out_invoice', 'out_refund'):
            account = product.property_account_income or product.categ_id.property_account_income_categ
        else:
            account = product.property_account_expense or product.categ_id.property_account_expense_categ
        account = fpos.map_account(account)
        if account:
            values['account_id'] = account.id

        if type in ('out_invoice', 'out_refund'):
            taxes = product.taxes_id or account.tax_ids
            if product.description_sale:
                values['name'] += '\n' + product.description_sale
        else:
            taxes = product.supplier_taxes_id or account.tax_ids
            if product.description_purchase:
                values['name'] += '\n' + product.description_purchase

        taxes = fpos.map_tax(taxes)
        values['invoice_line_tax_id'] = taxes.ids

        if type in ('in_invoice', 'in_refund'):
            values['price_unit'] = price_unit or product.standard_price
        else:
            values['price_unit'] = product.list_price

        values['uos_id'] = uom_id or product.uom_id.id
        domain = {'uos_id': [('category_id', '=', product.uom_id.category_id.id)]}

        company = self.env['res.company'].browse(company_id)
        currency = self.env['res.currency'].browse(currency_id)

        if company and currency:
            if company.currency_id != currency:
                if type in ('in_invoice', 'in_refund'):
                    values['price_unit'] = product.standard_price
                values['price_unit'] = values['price_unit'] * currency.rate

            if values['uos_id'] and values['uos_id'] != product.uom_id.id:
                values['price_unit'] = self.env['product.uom']._compute_price(
                    product.uom_id.id, values['price_unit'], values['uos_id'])

        return {'value': values, 'domain': domain}
    
AccountInvoiceLine()

class AccountInvoice(osv.osv):
    
    _inherit = 'account.invoice'
    
    _columns = {
                'account_id':fields.many2one('account.account', string="Account", required=False, readonly=True, states={'draft': [('readonly', False)]},
                                             help="The partner account used for this invoice."),
                'sector_id':fields.many2one('sale.sector','Sector'),
                'sector_expense':fields.boolean('Region Expense'),
                }
    
    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_invoice_tax = self.env['account.invoice.tax']
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise except_orm(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise except_orm(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': new_fields.Date.context_today(self)})
            date_invoice = inv.date_invoice

            company_currency = inv.company_id.currency_id
            # create the analytical lines, one move line per invoice line
            iml = inv._get_analytic_lines()
            # check if taxes are all computed
            compute_taxes = account_invoice_tax.compute(inv)
            inv.check_tax_lines(compute_taxes)

            # I disabled the check_total feature
            if self.env['res.users'].has_group('account.group_supplier_inv_check_total'):
                if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding / 2.0):
                    raise except_orm(_('Bad Total!'), _('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise except_orm(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

            # one move line per tax line
            iml += account_invoice_tax.move_line_get(inv.id)

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = inv.number

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)

            name = inv.name or inv.supplier_invoice_number or '/'
            totlines = []
            if inv.payment_term:
                totlines = inv.with_context(ctx).payment_term.compute(total, date_invoice)[0]
            if totlines:
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref
                })

            date = date_invoice

            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)

            line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            if journal.centralisation:
                raise except_orm(_('User Error!'),
                        _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            line = inv.finalize_invoice_move_lines(line)

            move_vals = {
                'ref': inv.reference or inv.name,
                'sector_id':inv.sector_id.id,
                'line_id': line,
                'journal_id': journal.id,
                'date': inv.date_invoice,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            period = inv.period_id
            if not period:
                period = period.with_context(ctx).find(date_invoice)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id

            ctx['invoice'] = inv
            move = account_move.with_context(ctx).create(move_vals)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'period_id': period.id,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
        self._log_event()
        return True
    
    def action_number(self, cr, uid, ids, context=None):
        for inv in self.browse(cr, uid, ids, context=context):
#             if inv.type == 'in_invoice':
#                 po_ids = self.pool.get('purchase.order').search(cr, uid, [('name','=',inv.name)])
#                 if po_ids:
#                     shipped = self.pool.get('purchase.order').read(cr, uid, po_ids[0], ['shipped'], context=context)['shipped']
#                     if not shipped:
#                         raise osv.except_osv(_('ERROR !!'),_('Products not received yet.'))
            for line in inv.invoice_line:
                if line.prod_type == 'asset' and not line.asset_category_id:
                    raise osv.except_osv(_('ERROR !!'),_('Please select the asset category for "%s" before validating.'%(line.product_id.name)))
        return super(AccountInvoice, self).action_number(cr, uid, ids)
    
AccountInvoice()

class AccountBankStatement(osv.osv):
    
    _inherit = 'account.bank.statement'
    
AccountBankStatement()

class AccountMoveLine(osv.osv):
    
    _inherit = 'account.move.line'
    
    _order = 'debit desc'
    
    _columns = {
                'name': fields.char('Memo', required=True),
                }
    
AccountMoveLine()

class AccountMove(osv.osv):
    
    _inherit = 'account.move'
    
    _columns = {
                'sector_id':fields.many2one('sale.sector','Sector'),
                }
    
    _defaults = {
                 'date':False
                 }
    
    def onchange_date(self, cr, uid, ids, date, context=None):
        res = {}
        print "KKKKKKKKKKKKKKKkk",date
        if not date:
            return {'value':{'period_id':False}}
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date),('date_stop', '>=', date), ('state', '=', 'draft')])
        if not period_ids:
            model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'account', 'action_account_period')
            msg = _('There is no period defined for this date or period is not open: %s.\nPlease go to Configuration/Periods.') % date
            raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
        return {'value':{'period_id':period_ids[0]}}
        
AccountMove()

class AccountAccount(osv.osv):
    
    _inherit = 'account.account'
    
    _columns = {
                'temp_1':fields.many2one('account.account','Level 1'),
                'temp_2':fields.many2one('account.account','Level 2'),
                'temp_3':fields.many2one('account.account','Level 3'),
                'temp_4':fields.many2one('account.account','Level 4'),
                'temp_5':fields.many2one('account.account','Level 5'),
                'temp_6':fields.many2one('account.account','Level 6'),
                'temp_7':fields.many2one('account.account','Level 7'),
                }
    
    def onchange_internal_type(self, cr, uid, ids, internal_type, context=None):
        res = {}
        if internal_type in ('receivable', 'payable'):
            acc_type = self.pool.get('account.account.type').search(cr, uid, [('code','=',internal_type)])
            res.update({'user_type':acc_type and acc_type[0] or False, 'reconcile':True})
        return {'value':res}
    
    def check_code(self, cr, uid, ids, context=None):
        for acc in self.browse(cr, uid, ids, context=context):
            if not acc.code.startswith(acc.parent_id.code):
                raise osv.except_osv(_('ERROR !!'),_('Code of an account should starts with its parent account code.'))
        return True
    
    def get_code(self, cr, uid, parent_id, type, context=None):
        parent = self.browse(cr, uid, parent_id, context=context)
        code = 0
        first = False
        type_first = True
        for child in parent.child_parent_ids:
            if type == child.type and code < int(child.code):
                code = int(child.code)
                type_first = False
            else:
                continue
        if type_first:
            code = parent.code + (type == 'view' and '1' or '00')
        else:
            code = code + 1
        if not parent.child_parent_ids:
            first = True
            code = parent.code + (type == 'view' and '1' or '00')
        return code
    
    def _check_allow_type_change(self, cr, uid, ids, new_type, context=None):
        restricted_groups = ['consolidation','view']
        line_obj = self.pool.get('account.move.line')
        for account in self.browse(cr, uid, ids, context=context):
            old_type = account.type
            account_ids = self.search(cr, uid, [('id', 'child_of', [account.id])])
            if line_obj.search(cr, uid, [('account_id', 'in', account_ids)]):
                if old_type != 'closed' and new_type == 'closed':
                    if account.balance != 0.0:
                        raise osv.except_osv(_('Warning!'),_("You cannot change the type of account to closed, which has balance not equal to zero."))
                #Check for 'Closed' type
                if old_type == 'closed' and new_type !='closed':
                    raise osv.except_osv(_('Warning!'), _("You cannot change the type of account from 'Closed' to any other type as it contains journal items!"))
                # Forbid to change an account type for restricted_groups as it contains journal items (or if one of its children does)
                if (new_type in restricted_groups):
                    raise osv.except_osv(_('Warning!'), _("You cannot change the type of account to '%s' type as it contains journal items!") % (new_type,))

        return True
        
    def create(self, cr, uid, vals, context=None):
        if not vals.has_key('parent_id'):
            parent_id = vals.has_key('temp_6') and vals['temp_6'] or vals.has_key('temp_5') and vals['temp_5'] \
                        or vals.has_key('temp_4') and vals['temp_4'] or vals.has_key('temp_3') and vals['temp_3'] \
                        or vals.has_key('temp_2') and vals['temp_2'] or vals.has_key('temp_1') and vals['temp_1']
            vals['parent_id'] = parent_id
            vals['code'] = self.get_code(cr, uid, parent_id, vals['type'], context=context)
        id = super(AccountAccount, self).create(cr, uid, vals, context=context)
        self.check_code(cr, uid, [id], context=context)
        return id
          
    def write(self, cr, uid, ids, vals, context=None):
        res = super(AccountAccount, self).write(cr, uid, ids, vals, context=context)
        self.check_code(cr, uid, ids, context=context)
        return True
     
AccountAccount()

class AccountAnalyticAccount(osv.osv):
    
    _inherit = 'account.analytic.account'
    
    def _get_full_name(self, cr, uid, ids, name=None, args=None, context=None):
        if context == None:
            context = {}
        res = {}
        for elmt in self.browse(cr, uid, ids, context=context):
            name = self._get_one_full_name(elmt)
            if elmt.code:
                name = elmt.code + ' - ' + name
            res[elmt.id] = name
        return res
    
    _columns = {
                'complete_name': fields.function(_get_full_name, type='char', string='Full Name'),
                'code': fields.char('Code', select=True, track_visibility='onchange', copy=False),
                }
    
    
    
AccountAnalyticAccount()


class AccountPeriod(osv.osv):
    
    _inherit = 'account.period'
    
    _columns = {
                'state': fields.selection([('new','New'),('draft','Open'), ('done','Closed')], 'Status', readonly=True, copy=False,
                                  help='When monthly periods are created. The status is \'Draft\'. At the end of monthly period it is in \'Done\' status.'),
                }
    
    _defaults = {
        'state': 'new',
    }
    
    @api.returns('self')
    def find(self, cr, uid, dt=None, context=None):
        if context is None: context = {}
        if not dt:
            dt = fields.date.context_today(self, cr, uid, context=context)
        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt), ('state', '=', 'draft')]
        if context.get('company_id', False):
            args.append(('company_id', '=', context['company_id']))
        else:
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            args.append(('company_id', '=', company_id))
        result = []
        if context.get('account_period_prefer_normal', True):
            # look for non-special periods first, and fallback to all if no result is found
            result = self.search(cr, uid, args + [('special', '=', False)], context=context)
        if not result:
            result = self.search(cr, uid, args, context=context)
        if not result:
            model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'account', 'action_account_period')
            msg = _('There is no period defined for this date or period is not open: %s.\nPlease go to Configuration/Periods.') % dt
            raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
        return result
    
    def action_open(self, cr, uid, ids, context=None):
        open_ids = self.search(cr, uid, [('state','=','draft')])
        if len(open_ids) >= 2:
            raise osv.except_osv(_('Warning!'),_('Already 2 or more periods are open. Please close a period to open this one.'))            
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        return True
    
AccountPeriod()
