from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date


class ResonnocareClinic(models.Model):
    _name = "resonnocare.clinic"
    _description = "Resonnocare Clinic"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "clinic_code desc"

    # ---------------------------------------------------------
    # Core Identity
    # ---------------------------------------------------------

    area_manager_id = fields.Many2one(
        'res.users',
        string='Area Manager',
        tracking=True,
        help="Area Manager responsible for this clinic"
    )

    region = fields.Char(
        string='Region',
        help="Geographic region (North, South, East, West, etc.)"
    )

    clinic_version = fields.Char(
        string='Store Version',
        help="Version of the store (SIS Same Store, SIS Store 2023, etc.)"
    )

    name = fields.Char(
        string="Clinic Name",
        required=True,
        tracking=True,
    )

    clinic_code = fields.Char(
        string="Clinic Code",
        readonly=True,
        copy=False,
        index=True,
    )

    clinic_type = fields.Selection(
        [
            ("h", "H"),
            ("sis", "SIS"),
            ("coco", "COCO"),
        ],
        string="Clinic Type",
        tracking=True,
        required=True,
    )

    clinic_subtype = fields.Selection(
        [
            ("b2b", "B2B"),
            ("b2c", "B2C"),
        ],
        string="Clinic Sub Type",
    )

    clinic_category = fields.Selection(
        [
            ("1_1", "1:1"),
            ("1_2", "1:2"),
            ("2_1", "2:1"),
            ("visiting", "Visiting"),
        ],
        string="Clinic Category",
        required=True,
    )

    clinic_logo = fields.Image(
        string="Clinic / Hospital Logo",
        max_width=512,
        max_height=512,
    )

    partner_name = fields.Char(
        string="Partner Name",
    )

    clinic_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("suspended", "Suspended"),
        ],
        string="Clinic Status",
        default="draft",
        tracking=True,
    )

    go_live_date = fields.Date(
        string="Clinic Opening Date",
        tracking=True,
    )

    external_billing = fields.Boolean(
        string="External Billing",
        default=True,
    )

    def init(self):
        # Idempotent migration: map legacy clinic type/subtype values to the new model.
        self._cr.execute(
            """
            UPDATE resonnocare_clinic
               SET clinic_type = 'sis'
             WHERE clinic_type = 'b2b'
            """
        )
        self._cr.execute(
            """
            UPDATE resonnocare_clinic
               SET clinic_type = 'h'
             WHERE clinic_type = 'b2c'
            """
        )
        self._cr.execute(
            """
            UPDATE resonnocare_clinic
               SET clinic_subtype = 'b2b'
             WHERE (clinic_subtype IS NULL OR clinic_subtype = '' OR clinic_subtype IN ('doctor', 'hospital'))
               AND clinic_type = 'sis'
            """
        )
        self._cr.execute(
            """
            UPDATE resonnocare_clinic
               SET clinic_subtype = 'b2c'
             WHERE (clinic_subtype IS NULL OR clinic_subtype = '' OR clinic_subtype IN ('doctor', 'hospital'))
               AND clinic_type IN ('h', 'coco')
            """
        )
        self._cr.execute(
            """
            UPDATE resonnocare_clinic
               SET clinic_subtype = NULL
             WHERE clinic_type = 'coco'
            """
        )

    # ---------------------------------------------------------
    # Address & Location
    # ---------------------------------------------------------

    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    zip = fields.Char()

    state_id = fields.Many2one(
        "res.country.state",
        string="State",
    )

    country_id = fields.Many2one(
        "res.country",
        string="Country",
    )

    clinic_location = fields.Char(string="Location")
    clinic_landmark = fields.Char(string="Landmark")

    clinic_latitude = fields.Float(
        string="Latitude",
        digits=(10, 7),
    )

    clinic_longitude = fields.Float(
        string="Longitude",
        digits=(10, 7),
    )

    

    # ---------------------------------------------------------
    # Ownership (Derived)
    # ---------------------------------------------------------

    ownership_type = fields.Selection(
        [
            ("resonnocare", "Owned by Resonnocare"),
            ("partner", "Partner Owned"),
        ],
        string="Ownership",
        compute="_compute_ownership_type",
        compute_sudo=True,
        store=True,
        readonly=True,
    )

    # ---------------------------------------------------------
    # ERP / SCM Linkage
    # ---------------------------------------------------------

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    vat = fields.Char(
        string="GSTIN/VAT",
        help="GST Identification Number or VAT Number from Company",
    )

    state_hq_name = fields.Char(
        string="State HQ Name",
        help="Head Quarter Name for the State",
    )

    state_hq_address = fields.Text(
        string="State HQ Address",
        help="Address of the State Head Quarter",
    )

    state_gst = fields.Char(
        string="State GST",
        help="GST Number for State Operations",
    )

    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        required=True,
        readonly=True,
    )

    hearing_aid_sale_location_id = fields.Many2one(
        "stock.location",
        string="Saleable Hearing Aid Location",
        readonly=True,
    )

    demo_hearing_aid_location_id = fields.Many2one(
        "stock.location",
        string="Demo Hearing Aid & Charger Location",
        readonly=True,
    )

    saleable_accessories_location_id = fields.Many2one(
        "stock.location",
        string="Saleable Accessories Location",
        readonly=True,
    )

    repair_service_location_id = fields.Many2one(
        "stock.location",
        string="Repair & Service Location",
        readonly=True,
    )

    equipment_location_id = fields.Many2one(
        "stock.location",
        string="Equipment Location",
        readonly=True,
    )

    consumable_location_id = fields.Many2one(
        "stock.location",
        string="Consumable Location",
        readonly=True,
    )

    rtv_location_id = fields.Many2one(
        "stock.location",
        string="Return to Vendor (RTV) Location",
        readonly=True,
    )

    stock_location_id = fields.Many2one(
        related="warehouse_id.lot_stock_id",
        string="Main Stock Location",
        compute_sudo=True,
        store=True,
        readonly=True,
    )

    diagnostic_price_line_ids = fields.One2many(
        "resonnocare.clinic.diagnostic",
        "clinic_id",
        string="Diagnostic Pricing",
    )

    diagnostic_price_history_ids = fields.One2many(
        "resonnocare.clinic.diagnostic.price.history",
        "clinic_id",
        string="Diagnostic Price History",
        readonly=True,
    )

    clinic_sharing_rule_ids = fields.One2many(
        "resonnocare.clinic.sharing.rule",
        "clinic_id",
        string="Clinic Sharing Rules",
    )
    clinic_sharing_flat_ids = fields.One2many(
        "resonnocare.clinic.sharing.rule",
        "clinic_id",
        string="Flat Sharing Rules",
        domain=[("rule_level", "=", "flat")],
    )
    clinic_sharing_mrp_ids = fields.One2many(
        "resonnocare.clinic.sharing.rule",
        "clinic_id",
        string="MRP Sharing Rules",
        domain=[("rule_level", "=", "mrp")],
    )
    clinic_sharing_item_ids = fields.One2many(
        "resonnocare.clinic.sharing.rule",
        "clinic_id",
        string="Item Sharing Rules",
        domain=[("rule_level", "=", "item")],
    )
    clinic_sharing_source_ids = fields.One2many(
        "resonnocare.clinic.sharing.rule",
        "clinic_id",
        string="Source Sharing Rules",
        domain=[("rule_level", "=", "source")],
    )
    enable_flat_sharing = fields.Boolean(default=False)
    enable_mrp_slab_sharing = fields.Boolean(default=False)
    enable_item_based_sharing = fields.Boolean(default=False)
    enable_source_based_sharing = fields.Boolean(default=False)
    sharing_applicable_from = fields.Date()
    sharing_applicable_to = fields.Date()

    # ---------------------------------------------------------
    # Creation Rules (Wizard-only)
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("clinic_type") == "coco":
                vals["clinic_subtype"] = False
            if not vals.get("clinic_code"):
                raise UserError(
                    "Clinics must be created using the 'Create Clinic' wizard."
                )

            if (
                not vals.get("city")
                or not vals.get("state_id")
                or not vals.get("country_id")
            ):
                raise ValidationError(
                    "City, State, and Country are mandatory for all clinics."
                )

            if vals.get("clinic_type") in ("h", "sis"):
                if not vals.get("partner_name"):
                    raise ValidationError(
                        "Partner name is required for H and SIS clinics."
                    )

            # Auto-create warehouse if not provided
            if not vals.get("warehouse_id"):
                clinic_name = vals.get("name", "Clinic")
                clinic_code = vals.get("clinic_code", "")
                company_id = vals.get("company_id", self.env.company.id)
                
                warehouse = self.env["stock.warehouse"].create(
                    {
                        "name": clinic_name,
                        "code": clinic_code[-3:] if clinic_code else "CLC",
                        "company_id": company_id,
                    }
                )
                vals["warehouse_id"] = warehouse.id

            # Auto-populate VAT from Company if not provided
            if not vals.get("vat"):
                company_id = vals.get("company_id", self.env.company.id)
                company = self.env["res.company"].browse(company_id)
                if company.vat:
                    vals["vat"] = company.vat

        return super().create(vals_list)

    # ---------------------------------------------------------
    # Write Protection Rules
    # ---------------------------------------------------------

    def write(self, vals):
        for clinic in self:
            # if "name" in vals and vals["name"] != clinic.name:
            #     raise UserError("Clinic name cannot be modified.")

            if "clinic_code" in vals and vals["clinic_code"] != clinic.clinic_code:
                raise UserError("Clinic code cannot be modified.")

            if clinic.clinic_status in ("active", "suspended"):
                restricted_fields = [
                    "clinic_type",
                    "clinic_subtype",
                    "partner_name",
                    "city",
                    "state_id",
                    "country_id",
                    "zip",
                    "street",
                ]
                for field in restricted_fields:
                    if field in vals and vals[field] != clinic[field]:
                        raise UserError(
                            f"Cannot modify {field.replace('_', ' ').title()} when clinic is {clinic.clinic_status}."
                        )
            next_type = vals.get("clinic_type", clinic.clinic_type)
            if next_type == "coco":
                vals["clinic_subtype"] = False

            if "go_live_date" in vals and vals["go_live_date"]:
                go_live = fields.Date.from_string(vals["go_live_date"])
                if go_live <= date.today() and clinic.clinic_status == "draft":
                    vals["clinic_status"] = "active"

        result = super().write(vals)
        self._check_auto_activation()
        return result

    # ---------------------------------------------------------
    # Inventory Locations (Clinic-Level)
    # ---------------------------------------------------------

    def _get_inventory_location_defs(self, include_rtv=False):
        defs = [
            ("hearing_aid_sale_location_id", "Saleable Hearing Aid"),
            ("demo_hearing_aid_location_id", "Demo Hearing Aid & Charger"),
            ("saleable_accessories_location_id", "Saleable Accessories"),
            ("repair_service_location_id", "Repair & Service"),
            ("equipment_location_id", "Equipment"),
            ("consumable_location_id", "Consumable"),
        ]
        if include_rtv:
            defs.append(("rtv_location_id", "Return to Vendor (RTV)"))
        return defs

    def _ensure_inventory_locations(self, include_rtv=False):
        StockLocation = self.env["stock.location"].sudo()

        for clinic in self:
            if not clinic.warehouse_id or not clinic.warehouse_id.lot_stock_id:
                continue

            parent = clinic.warehouse_id.lot_stock_id
            updates = {}

            for field_name, location_name in clinic._get_inventory_location_defs(
                include_rtv=include_rtv
            ):
                current = clinic[field_name]
                if current and current.location_id == parent:
                    continue

                existing = StockLocation.search(
                    [
                        ("location_id", "=", parent.id),
                        ("name", "=", location_name),
                        ("usage", "=", "internal"),
                    ],
                    limit=1,
                )

                if not existing:
                    existing = StockLocation.create(
                        {
                            "name": location_name,
                            "location_id": parent.id,
                            "usage": "internal",
                            "company_id": clinic.warehouse_id.company_id.id,
                        }
                    )

                updates[field_name] = existing.id

            if updates:
                clinic.sudo().write(updates)

    def action_backfill_inventory_locations(self):
        self._ensure_inventory_locations(include_rtv=False)

    # ---------------------------------------------------------
    # Computed Fields
    # ---------------------------------------------------------

    @api.depends("clinic_type")
    def _compute_ownership_type(self):
        for clinic in self:
            if clinic.clinic_type == "coco":
                clinic.ownership_type = "resonnocare"
            elif clinic.clinic_type in ("h", "sis"):
                clinic.ownership_type = "partner"
            else:
                clinic.ownership_type = False

    # ---------------------------------------------------------
    # Automated Go-Live Activation
    # ---------------------------------------------------------

    def _check_auto_activation(self):
        for clinic in self:
            if (
                clinic.clinic_status == "draft"
                and clinic.go_live_date
                and clinic.go_live_date <= date.today()
            ):
                clinic.clinic_status = "active"

    @api.model
    def _cron_activate_go_live_clinics(self):
        clinics = self.search(
            [
                ("clinic_status", "=", "draft"),
                ("go_live_date", "<=", fields.Date.today()),
            ]
        )
        for clinic in clinics:
            clinic.clinic_status = "active"

    # ---------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------

    @api.constrains("city", "state_id", "country_id")
    def _check_location(self):
        for clinic in self:
            if not clinic.city or not clinic.state_id or not clinic.country_id:
                raise ValidationError(
                    "City, State, and Country are mandatory for all clinics."
                )

    @api.constrains("clinic_type", "clinic_subtype", "partner_name")
    def _check_partner_details(self):
        for clinic in self:
            if clinic.clinic_type == "coco" and clinic.clinic_subtype:
                raise ValidationError("Clinic Sub Type must be empty for COCO clinics.")
            if clinic.clinic_type in ("h", "sis") and not clinic.clinic_subtype:
                raise ValidationError("Clinic Sub Type is mandatory for H and SIS clinics.")
            if clinic.clinic_type in ("h", "sis") and not clinic.partner_name:
                raise ValidationError(
                    "Partner name is mandatory for H and SIS clinics."
                )

    @api.onchange("clinic_type")
    def _onchange_clinic_type_clear_subtype(self):
        for clinic in self:
            if clinic.clinic_type == "coco":
                clinic.clinic_subtype = False

    @api.constrains("go_live_date", "clinic_status")
    def _check_go_live_date(self):
        for clinic in self:
            if clinic.clinic_status == "active" and clinic.go_live_date:
                if clinic.go_live_date > date.today():
                    raise ValidationError(
                        "Active clinic cannot have a future go-live date."
                    )

    # ---------------------------------------------------------
    # Dashboard Metrics (Live)
    # ---------------------------------------------------------

    appointments_today = fields.Integer(compute="_compute_dashboard_metrics")
    walkins_today = fields.Integer(compute="_compute_dashboard_metrics")
    patients_waiting = fields.Integer(compute="_compute_dashboard_metrics")
    pending_consultations = fields.Integer(compute="_compute_dashboard_metrics")
    followups_due_today = fields.Integer(compute="_compute_dashboard_metrics")
    doctors_on_duty = fields.Integer(compute="_compute_doctors_on_duty")

    def _compute_dashboard_metrics(self):
        today = fields.Date.context_today(self)
        Appointment = self.env["resonnocare.appointment"].sudo()
        Lead = self.env["crm.lead"].sudo()
        lead_fields = Lead._fields
        for clinic in self:
            base_domain = [
                ("clinic_id", "=", clinic.id),
                ("appointment_date", "=", today),
                ("status", "not in", ("cancelled", "no_show")),
            ]
            clinic.appointments_today = Appointment.search_count(base_domain)
            clinic.walkins_today = Appointment.search_count(
                base_domain + [("source", "=", "walkin")]
            )
            clinic.patients_waiting = Appointment.search_count(
                base_domain + [("status", "=", "checked_in")]
            )
            clinic.pending_consultations = Appointment.search_count(
                base_domain + [("status", "in", ("scheduled", "checked_in"))]
            )

            # CRM follow-up count (today) scoped to this clinic using available clinic linkage fields.
            followup_domain = [("type", "=", "lead")]
            clinic_or = []
            if "x_preferred_clinic_id" in lead_fields:
                clinic_or.append(("x_preferred_clinic_id", "=", clinic.id))
            if "x_interested_clinic_id" in lead_fields:
                clinic_or.append(("x_interested_clinic_id", "=", clinic.id))
            if clinic_or:
                if len(clinic_or) == 1:
                    followup_domain += clinic_or
                else:
                    followup_domain += ["|"] + clinic_or

            date_or = []
            if "x_next_followup_date" in lead_fields:
                date_or.append(("x_next_followup_date", "=", today))
            if "activity_date_deadline" in lead_fields:
                date_or.append(("activity_date_deadline", "=", today))
            if date_or:
                if len(date_or) == 1:
                    followup_domain += date_or
                else:
                    followup_domain += ["|"] + date_or
                clinic.followups_due_today = Lead.search_count(followup_domain)
            else:
                clinic.followups_due_today = 0

    def _compute_doctors_on_duty(self):
        for clinic in self:
            doctors = self.env["hr.employee"].search_count(
                [
                    ("clinic_id", "=", clinic.id),
                    ("clinic_role", "=", "doctor"),
                    ("active", "=", True),
                ]
            )
            clinic.doctors_on_duty = doctors

    def _get_effective_billing_type(self):
        self.ensure_one()
        # New master: billing behavior comes from clinic sub type.
        if self.clinic_subtype in ("b2b", "b2c"):
            return self.clinic_subtype
        if self.clinic_type == "coco":
            return "b2c"
        # Backward compatibility for older clinic records.
        if self.clinic_type == "b2b":
            return "b2b"
        return "b2c"

    def _get_product_service_category(self, product):
        self.ensure_one()
        if not product:
            return "other_products"
        ptype = getattr(product, "type", False) or getattr(
            product, "type", False
        )
        name = (
            (product.display_name or "")
            + " "
            + ((product.categ_id.name or "") if product.categ_id else "")
        ).lower()
        if ptype == "service":
            if "repair" in name:
                return "repair_services"
            if "diagnostic" in name or "test" in name:
                return "diagnostic_services"
            return "other_services"
        if "accessor" in name:
            return "accessories_sale"
        return "hearing_device"

    def _resolve_clinic_sharing(self, product=False, mrp=0.0, source_category=False):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.sharing_applicable_from and today < self.sharing_applicable_from:
            return {
                "sharing_percent": 0.0,
                "billing_price": 0.0,
                "rule_id": False,
                "rule_level": False,
            }
        if self.sharing_applicable_to and today > self.sharing_applicable_to:
            return {
                "sharing_percent": 0.0,
                "billing_price": 0.0,
                "rule_id": False,
                "rule_level": False,
            }

        billing_type = self._get_effective_billing_type()
        category = self._get_product_service_category(product)
        rules = self.clinic_sharing_rule_ids.filtered(
            lambda r: r.active
            and (not r.applicable_from or r.applicable_from <= today)
            and (not r.applicable_to or r.applicable_to >= today)
            and r.product_category == category
            and (not r.billing_type or r.billing_type == billing_type)
        )

        def _pick(level, pred):
            candidates = rules.filtered(lambda r: r.rule_level == level and pred(r))
            if not candidates:
                return False
            exact_billing = candidates.filtered(lambda r: r.billing_type == billing_type)
            return (exact_billing or candidates).sorted(
                key=lambda r: (r.sequence, r.id)
            )[:1]

        level_order = [
            ("source", self.enable_source_based_sharing),
            ("item", self.enable_item_based_sharing),
            ("mrp", self.enable_mrp_slab_sharing),
            ("flat", self.enable_flat_sharing),
        ]
        for level, enabled in level_order:
            if not enabled:
                continue
            match = False
            if level == "source" and source_category:
                match = _pick(level, lambda r: r.source_category == source_category)
            elif level == "item" and product:
                match = _pick(
                    level, lambda r: r.product_tmpl_id and r.product_tmpl_id == product.product_tmpl_id
                )
            elif level == "mrp":
                match = _pick(
                    level,
                    lambda r: (not r.mrp_range_from or mrp >= r.mrp_range_from)
                    and (not r.mrp_range_to or mrp <= r.mrp_range_to),
                )
            elif level == "flat":
                match = _pick(level, lambda r: True)
            if match:
                rule = match[0]
                return {
                    "sharing_percent": rule.sharing_percent or 0.0,
                    "billing_price": rule.billing_price or 0.0,
                    "rule_id": rule.id,
                    "rule_level": rule.rule_level,
                }
        return {
            "sharing_percent": 0.0,
            "billing_price": 0.0,
            "rule_id": False,
            "rule_level": False,
        }
