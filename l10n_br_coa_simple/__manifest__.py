# Copyright (C) 2009  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Brazilian - Simple Accounting",
    "summary": "Brazilian Simple Chart of Account",
    "category": "Localization",
    "license": "AGPL-3",
    "author": "Akretion, " "Odoo Community Association (OCA)",
    "website": "http://github.com/OCA/l10n-brazil",
    "version": "12.0.1.0.1",
    "depends": ["account", "l10n_br_coa"],
    "data": [
        "data/account_chart_template_data.xml",
        "data/account_group_data.xml",
        "data/account.account.template.csv",
        "data/account_tax_template_data.xml",
    ],
    "post_init_hook": "post_init_hook",
}
