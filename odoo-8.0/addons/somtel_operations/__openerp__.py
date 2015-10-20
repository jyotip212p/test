

{
'name':'Module for Somtel Operations',
'category':'Customized Module',
'author':'credativ software(India) pvt ltd',
'description':'''
Modules contains the features for Somtel operations
1. Sales
2. Purchase
3. Warehouse
4. Financial Accounting & Analytic Accounting
5. Asset Management
6. Budget Management
etc..
''',
'depends':['base','sale','stock','purchase','account_accountant','account_chart','account_voucher','analytic','account_cancel','account_asset','account_budget','somtel','account_analytic_analysis'],
'data':[
        'security/structure_security.xml',
        'security/ir.model.access.csv',
        'account/coa.xml',
        'structure/structure_view.xml',
        'stock/stock_view.xml',
        'indentation/material_indentation_sequence.xml',
        'indentation/indentation_view.xml',
        'account/account_view.xml',
        'purchase/purchase_view.xml',
        'asset/asset_requisition_sequence.xml',
        'asset/asset_view.xml',
        'asset/wizard/return_asset_view.xml',
        'sale/sale_view.xml',
        'hr/hr_view.xml',
        'budget/budget_view.xml',
        'sales_forecast/outlet_sales_forecast_view.xml',
        'sales_forecast/sales_forecast_sequence.xml',
        'sales_forecast/wizard/sales_forecast_reject_reason_view.xml',
        'sales_forecast/wizard/sales_forecast_send_for_validate_view.xml',
        'sales_forecast/sales_forecast_view.xml',
        'email/sales_forecast_mail_view.xml',
        'budget/wizard/import_budget_lines_view.xml',
        'product/product_view.xml',
        'res/res_partner_view.xml',
        'procurement/procurement_view.xml',
        ],
'installable':True,
'auto_install':False
}
