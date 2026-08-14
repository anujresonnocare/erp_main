from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    env["res.company"].sudo()._ensure_ho_warehouse_and_locations()
