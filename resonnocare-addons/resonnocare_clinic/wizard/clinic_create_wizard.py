from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResonnocareClinicCreateWizard(models.TransientModel):
    _name = "resonnocare.clinic.create.wizard"
    _description = "Resonnocare Clinic Creation Wizard"

    # -------------------------------------------------
    # COMPANY SELECTION
    # -------------------------------------------------
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
  

    # -------------------------------------------------
    # STEP 1 — Clinic Type
    # -------------------------------------------------
    clinic_type = fields.Selection(
        [
            ("h", "H"),
            ("sis", "SIS"),
            ("coco", "COCO"),
        ],
        string="Clinic Type",
        required=True,
    )

    clinic_subtype = fields.Selection(
        [
            ("b2b", "B2B"),
            ("b2c", "B2C"),
        ],
        string="Clinic Sub Type",
    )

    # New field Clinic category
    clinic_category = fields.Selection(
        [
            ("1_1", "1:1"),
            ("1_2", "1:2"),
            ("2_1", "2:1"),
            ("visiting", "Visiting"),
        ],
        string="Clinic Category",
    )

    clinic_logo = fields.Image(
        string="Clinic / Hospital Logo",
        max_width=512,
        max_height=512,
    )


    diagnostic_item_ids = fields.Many2many(
        "resonnocare.diagnostic.item",
        "rc_wiz_diag_rel",  # ✅ SHORT table name
        "wizard_id",
        "diagnostic_id",
        string="Diagnostic Tests",
        required=True,
    )

    diagnostic_mrp_text = fields.Text(
        string="Diagnostic MRPs",
        help="Format: CODE=MRP, one per line. Example:\nCBC=300\nXRAY=800",
    )

    diagnostic_pricing_line_ids = fields.One2many(
        "resonnocare.clinic.create.wizard.line",
        "wizard_id",
        string="Diagnostic Pricing",
    )

    partner_name = fields.Char(string="Partner Name")

    # -------------------------------------------------
    # STEP 2 — Location (MANDATORY)
    # -------------------------------------------------
    shop_clinic_number = fields.Char(string="Shop/Clinic Number")
    address = fields.Char(string="Address", required=True)
    location = fields.Char(string="Location", required=True)
    landmark = fields.Char(string="Landmark")
    
    clinic_vat = fields.Char(
        string="GSTIN/VAT",
        help="GST Identification Number",
        default=lambda self: self.env.company.vat or "",
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

    city = fields.Char(string="City", required=True)
    state_id = fields.Many2one("res.country.state", string="State", required=True)
    zip = fields.Char(string="Pin Code", required=True)
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        required=True,
        default=lambda self: self.env.ref("base.in").id,
    )
    clinic_longitude = fields.Float(string="Longitude", digits=(10, 7))
    clinic_latitude = fields.Float(string="Latitude", digits=(10, 7))

    # -------------------------------------------------
    # STEP 3 — Preview (COMPUTED)
    # -------------------------------------------------
    preview_clinic_name = fields.Char(
        string="Clinic Name Preview",
        compute="_compute_preview",
        readonly=True,
    )

    preview_clinic_code = fields.Char(
        string="Clinic Code Preview",
        compute="_compute_preview",
        readonly=True,
    )

    @api.model
    def _clean_pricing_line_commands(self, vals):
        """Drop empty o2m create commands sent by inline editable list rows."""
        commands = vals.get("diagnostic_pricing_line_ids")
        if not isinstance(commands, (list, tuple)):
            return vals

        cleaned_commands = []
        for command in commands:
            if not isinstance(command, (list, tuple)) or not command:
                cleaned_commands.append(command)
                continue

            cmd_type = command[0]
            # Command 0: CREATE
            if cmd_type == 0:
                line_vals = command[2] if len(command) > 2 else {}
                if not line_vals or not line_vals.get("diagnostic_item_id"):
                    continue
                cleaned_commands.append((0, 0, line_vals))
                continue

            # Command 1: UPDATE
            if cmd_type == 1:
                line_vals = command[2] if len(command) > 2 else {}
                # If diagnostic_item_id is explicitly set to False/None, drop the update
                # Or if it's an empty update (no line_vals), we can keep it if Odoo permits, 
                # but usually we want to ensure diagnostic_item_id remains set if it's there.
                if "diagnostic_item_id" in line_vals and not line_vals.get("diagnostic_item_id"):
                    continue
                cleaned_commands.append((1, command[1], line_vals))
                continue

            # Command 4: LINK, 2: DELETE, 3: UNLINK, 5: CLEAR, 6: SET
            cleaned_commands.append(command)

        vals["diagnostic_pricing_line_ids"] = cleaned_commands
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        cleaned_vals_list = [self._clean_pricing_line_commands(vals) for vals in vals_list]
        return super().create(cleaned_vals_list)

    def write(self, vals):
        vals = self._clean_pricing_line_commands(vals)
        return super().write(vals)



    # -------------------------------------------------
    # COMPUTED LOGIC
    # -------------------------------------------------
    @api.depends("clinic_type", "partner_name", "location", "city")
    def _compute_preview(self):
        for wizard in self:
            if not wizard.city or not wizard.clinic_type or not wizard.location:
                wizard.preview_clinic_name = False
                wizard.preview_clinic_code = False
                continue

            base = "EAR360"

            if wizard.clinic_type == "coco":
                # COCO: EAR360 Location - City
                name = f"{base} {wizard.location} - {wizard.city}"
            elif wizard.clinic_type in ("h", "sis"):
                if not wizard.partner_name:
                    name = False
                else:
                    name = f"{base} {wizard.partner_name} - {wizard.location} - {wizard.city}"
            else:
                name = False

            wizard.preview_clinic_name = name

            # Sequence preview (not consumed)
            seq = wizard.env["ir.sequence"].search(
                [("code", "=", "resonnocare.clinic.code")], limit=1
            )
            wizard.preview_clinic_code = (
                f"{seq.prefix}{str(seq.number_next_actual).zfill(seq.padding)}"
                if seq
                else False
            )

    @api.onchange("clinic_type")
    def _onchange_clinic_type_clear_subtype(self):
        for wizard in self:
            if wizard.clinic_type == "coco":
                wizard.clinic_subtype = False

    @api.onchange("diagnostic_item_ids")
    def _onchange_diagnostic_items_sync_pricing(self):
        for wizard in self:
            if not wizard.diagnostic_item_ids:
                wizard.diagnostic_pricing_line_ids = [(5, 0, 0)]
                continue

            existing_mrp = {
                line.diagnostic_item_id.id: line.mrp
                for line in wizard.diagnostic_pricing_line_ids
                if line.diagnostic_item_id
            }

            commands = [(5, 0, 0)]
            for diag in wizard.diagnostic_item_ids:
                commands.append(
                    (
                        0,
                        0,
                        {
                            "diagnostic_item_id": diag.id,
                            "mrp": existing_mrp.get(diag.id, 0.0),
                        },
                    )
                )

            wizard.diagnostic_pricing_line_ids = commands

    # -------------------------------------------------
    # CREATE CLINIC
    # -------------------------------------------------
    def action_create_clinic(self):
        self.ensure_one()

        if self.clinic_type in ("h", "sis") and not self.partner_name:
            raise ValidationError(
                "Partner name is mandatory for H and SIS clinics."
            )



        # Generate final clinic code
        clinic_code = self.env["ir.sequence"].next_by_code("resonnocare.clinic.code")

        clinic_name = self.preview_clinic_name
        if not clinic_name or not clinic_code:
            raise ValidationError("Unable to generate clinic name or code.")

        # Build full address for street field
        address_parts = []
        if self.shop_clinic_number:
            address_parts.append(self.shop_clinic_number)
        if self.address:
            address_parts.append(self.address)

        street = ", ".join(address_parts) if address_parts else self.address

        # Build street2 with location and landmark
        street2_parts = []
        if self.location:
            street2_parts.append(self.location)
        if self.landmark:
            street2_parts.append(f"Near {self.landmark}")

        street2 = ", ".join(street2_parts) if street2_parts else False

        warehouse = self.env["stock.warehouse"].create(
            {
                "name": clinic_name,
                "code": clinic_code[-3:],
                "company_id": self.company_id.id,
            }
        )

        clinic = self.env["resonnocare.clinic"].create(
            {
                "name": clinic_name,
                "clinic_code": clinic_code,
                "clinic_type": self.clinic_type,
                "clinic_subtype": self.clinic_subtype if self.clinic_type in ("h", "sis") else False,
                "clinic_category": self.clinic_category,
                "partner_name": self.partner_name,
                "clinic_status": "draft",
                "company_id": self.company_id.id,
                "street": street,
                "street2": street2,
                "city": self.city,
                "state_id": self.state_id.id,
                "zip": self.zip,
                "country_id": self.country_id.id,
                "clinic_location": self.location,
                "clinic_landmark": self.landmark,
                "clinic_longitude": self.clinic_longitude,
                "clinic_latitude": self.clinic_latitude,
                "clinic_logo": self.clinic_logo,
                "warehouse_id": warehouse.id,
                "vat": self.clinic_vat or self.company_id.vat or "",
                "state_hq_name": self.state_hq_name or "",
                "state_hq_address": self.state_hq_address or "",
                "state_gst": self.state_gst or "",
            }
        )

        clinic._ensure_inventory_locations(include_rtv=False)

        """
        This wizard performs system-level operations (user & employee creation)
        on behalf of Resonnocare governance. Privileged actions are intentionally
        executed using sudo() and must never be exposed via UI.
        """

        pricing = {}

        if self.diagnostic_pricing_line_ids:
            # Build a map only from valid rows and ignore orphan/incomplete rows.
            line_by_diag_id = {
                line.diagnostic_item_id.id: line
                for line in self.diagnostic_pricing_line_ids
                if line.diagnostic_item_id
            }
            for diag in self.diagnostic_item_ids:
                line = line_by_diag_id.get(diag.id)
                if not line or not line.mrp:
                    raise ValidationError(f"MRP missing for diagnostic: {diag.name}")
                pricing[diag.code] = line.mrp
        elif self.diagnostic_mrp_text:
            for line in self.diagnostic_mrp_text.splitlines():
                if "=" not in line:
                    raise ValidationError("Invalid MRP format. Use CODE=MRP per line.")
                code, mrp = line.split("=", 1)
                pricing[code.strip()] = float(mrp.strip())

        for diag in self.diagnostic_item_ids:
            if diag.code not in pricing:
                raise ValidationError(f"MRP missing for diagnostic: {diag.name}")

            self.env["resonnocare.clinic.diagnostic"].create(
                {
                    "clinic_id": clinic.id,
                    "diagnostic_item_id": diag.id,
                    "mrp": pricing[diag.code],
                }
            )



        # Return action that opens the clinic in the clinic-specific form view
        return {
            "type": "ir.actions.act_window",
            "name": "Clinic",
            "res_model": "resonnocare.clinic",
            "res_id": clinic.id,
            "view_mode": "form",
            "view_id": self.env.ref(
                "resonnocare_clinic.view_resonnocare_clinic_form"
            ).id,
            "target": "current",
            "context": {"form_view_initial_mode": "readonly"},
        }
