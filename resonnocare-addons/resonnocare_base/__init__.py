# from odoo import api, SUPERUSER_ID

# from . import models


# def post_init_hook(cr, registry):
#     """Ensure technician group name is updated even if original record is noupdate."""
#     env = api.Environment(cr, SUPERUSER_ID, {})
#     group = env.ref("resonnocare_base.group_resonnocare_internal", raise_if_not_found=False)
#     if group and group.name != "Technician":
#         group.write({"name": "Technician"})
from odoo import api, SUPERUSER_ID
from . import models


# GALAT - Old Style (Odoo 16) ❌
# def post_init_hook(cr, registry):
#     env = api.Environment(cr, SUPERUSER_ID, {})

# SAHI - Odoo 18 Style ✅
def post_init_hook(env):
    """Ensure technician group name is updated even if original record is noupdate."""
    group = env.ref("resonnocare_base.group_resonnocare_internal", raise_if_not_found=False)
    if group and group.name != "Technician":
        group.write({"name": "Technician"})