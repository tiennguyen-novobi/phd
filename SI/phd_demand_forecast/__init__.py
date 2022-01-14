# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from . import models


def uninstall_hook(cr, registry):
    cr.execute("""
        DROP TABLE IF EXISTS actual_sales_demand CASCADE;
        DROP TABLE IF EXISTS actual_daily_sales_demand CASCADE;
    """)
