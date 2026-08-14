import re
from odoo import models, fields, api
from json import loads
from odoo.exceptions import UserError
from datetime import date, timedelta
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    contract_id = fields.Char(string="Contract ID", readonly=True, copy=False)
    custom_invoice_category = fields.Selection(
        [
            ("DI", "Diagnostic Invoice"),
            ("DC", "Diagnostic Cancellation"),
            ("HI", "Hearing Device Invoice"),
            ("HC", "Hearing Device Cancellation"),
            ("RI", "Repair Invoice"),
            ("RC", "Repair Cancellation"),
        ],
        string="Invoice Category Code",
        readonly=True,
        copy=False,
    )

    _CUSTOM_INV_REGEX = re.compile(
        # New format (without DI/HI/RI category segment):
        # TI/C/TL/26/00012
        # Backward compatibility for old format is kept for existing records.
        r"^(TI|BS|TC|CN)/(C|H)(?:/(DI|DC|HI|HC|RI|RC))?/[A-Z]{2}/\d{2}/\d{5}$"
    )
    _STATE_CODE_MAP = {
        "jammu and kashmir": "JK",
        "himachal pradesh": "HP",
        "punjab": "PB",
        "chandigarh": "CH",
        "uttarakhand": "UK",
        "haryana": "GR",
        "delhi": "DL",
        "rajasthan": "RJ",
        "uttar pradesh": "UP",
        "bihar": "BR",
        "sikkim": "SK",
        "arunachal pradesh": "AR",
        "nagaland": "NL",
        "manipur": "MN",
        "mizoram": "MZ",
        "tripura": "TR",
        "meghalaya": "ML",
        "assam": "AS",
        "west bengal": "WB",
        "jharkhand": "JH",
        "odisha": "OD",
        "orissa": "OD",
        "chhattisgarh": "CG",
        "madhya pradesh": "MP",
        "gujarat": "GJ",
        "daman and diu": "DD",
        "daman & diu": "DD",
        "dadra and nagar haveli": "DN",
        "dadra & nagar haveli": "DN",
        "maharashtra": "MH",
        "andhra pradesh": "AP",
        "karnataka": "KA",
        "goa": "GA",
        "lakshadweep": "LD",
        "kerala": "KR",
        "tamil nadu": "TN",
        "puducherry": "PY",
        "pondicherry": "PY",
        "andaman and nicobar islands": "AN",
        "andaman & nicobar islands": "AN",
        "telangana": "TL",
    }

    def _invoice_item_lines(self):
        self.ensure_one()
        # Keep real invoice item lines only (works for both manual and SO-generated lines).
        return self.invoice_line_ids.filtered(
            lambda l: l.product_id
            and (l.display_type in (False, "product"))
            and not l.tax_line_id
        )

    def _is_service_product(self, product):
        if not product:
            return False
        ptype = getattr(product, "type", None)
        if ptype:
            return ptype == "service"
        detailed = getattr(product, "type", None)
        if detailed:
            return detailed == "service"
        return False

    def _is_device_product(self, product):
        if not product:
            return False
        ptype = getattr(product, "type", None)
        if ptype:
            return ptype in ("product", "consu")
        detailed = getattr(product, "type", None)
        if detailed:
            return detailed in ("product", "consu")
        return False

    def _sum_payments_amount(self, payments):
        self.ensure_one()
        total = 0.0
        for payment in payments:
            amount = payment.amount or 0.0
            if payment.currency_id and payment.currency_id != self.currency_id:
                date = (
                    payment.date or self.invoice_date or fields.Date.context_today(self)
                )
                amount = payment.currency_id._convert(
                    amount, self.currency_id, self.company_id, date
                )
            total += amount
        return total

    def _get_invoice_fy_suffix(self):
        self.ensure_one()
        inv_date = self.invoice_date or fields.Date.context_today(self)
        year = inv_date.year
        fy_end_year = year + 1 if inv_date.month >= 4 else year
        return str(fy_end_year)[-2:]

    def _get_custom_billing_code(self):
        self.ensure_one()
        clinic = self.clinic_id
        if (
            not clinic
            and self.partner_id
            and getattr(self.partner_id, "clinic_id", False)
        ):
            clinic = self.partner_id.clinic_id
        if clinic and hasattr(clinic, "_get_effective_billing_type"):
            return "H" if clinic._get_effective_billing_type() == "b2b" else "C"
        clinic_type = (clinic.clinic_type or "").lower() if clinic else ""
        return "H" if clinic_type == "b2b" else "C"

    def _get_custom_state_code(self):
        self.ensure_one()
        clinic = self.clinic_id
        if (
            not clinic
            and self.partner_id
            and getattr(self.partner_id, "clinic_id", False)
        ):
            clinic = self.partner_id.clinic_id
        state = clinic.state_id if clinic else False
        if not state:
            return "NA"
        mapped = self._STATE_CODE_MAP.get((state.name or "").strip().lower())
        if mapped:
            return mapped
        code = (state.code or "").strip().upper()
        return code[:2] if code else "NA"

    def _is_taxable_move(self):
        self.ensure_one()
        lines = self._invoice_item_lines()
        # Tax Invoice should apply only when there is effective tax impact.
        # If lines only carry 0%/Exempt/0-NGST taxes, treat as Bill of Supply.
        if abs(self.amount_tax or 0.0) > 0.000001:
            return True

        taxes = lines.mapped("tax_ids")
        effective_taxes = taxes.filtered(
            lambda t: (
                (t.amount_type in ("percent", "division", "fixed") and (t.amount or 0.0) > 0.0)
            )
        )
        return bool(effective_taxes)

    def _looks_like_repair_invoice(self):
        self.ensure_one()
        for line in self._invoice_item_lines():
            product = line.product_id
            text_parts = [
                (line.name or ""),
                (product.display_name or "") if product else "",
                (product.default_code or "") if product else "",
                (
                    (product.categ_id.display_name or "")
                    if product and product.categ_id
                    else ""
                ),
            ]
            haystack = " ".join(text_parts).lower()
            if "repair" in haystack:
                return True
        return False

    def _get_related_appointment(self):
        self.ensure_one()
        sale_orders = self.invoice_line_ids.sale_line_ids.mapped("order_id")
        if not sale_orders and self.invoice_origin:
            sale_orders = self.env["sale.order"].search(
                [("name", "=", self.invoice_origin)], limit=1
            )
        if sale_orders:
            appointment = self.env["resonnocare.appointment"].search(
                [("sale_order_id", "in", sale_orders.ids)], limit=1
            )
            if appointment:
                return appointment
        if self.invoice_origin:
            return self.env["resonnocare.appointment"].search(
                [("appointment_id", "=", self.invoice_origin)], limit=1
            )
        return self.env["resonnocare.appointment"]

    def _get_related_sale_orders(self):
        self.ensure_one()
        sale_orders = self.invoice_line_ids.sale_line_ids.mapped("order_id")
        if not sale_orders and self.invoice_origin:
            origins = [o.strip() for o in (self.invoice_origin or "").split(",") if o.strip()]
            if origins:
                sale_orders = self.env["sale.order"].search([("name", "in", origins)])
        return sale_orders

    def _is_device_invoice_flow(self):
        """Return True when invoice belongs to hearing-device sales flow."""
        self.ensure_one()
        appointment = self._get_related_appointment()
        if appointment:
            return appointment.sale_type == "device" or bool(appointment.device_sale_line_ids)

        sale_orders = self._get_related_sale_orders()
        if sale_orders:
            return any(
                line.product_id
                and self._is_device_product(line.product_id)
                and not self._is_service_product(line.product_id)
                for line in sale_orders.mapped("order_line")
                if not line.display_type
            )
        return False

    def _get_base_invoice_category_code(self):
        self.ensure_one()
        if self.reversed_entry_id and self.reversed_entry_id.custom_invoice_category:
            original = self.reversed_entry_id.custom_invoice_category
            return {
                "DI": "DI",
                "DC": "DI",
                "HI": "HI",
                "HC": "HI",
                "RI": "RI",
                "RC": "RI",
            }.get(original, "HI")

        if self._looks_like_repair_invoice():
            return "RI"

        appointment = self._get_related_appointment()
        if appointment:
            if appointment.sale_type == "service" or appointment.diagnostic_item_ids:
                return "DI"
            if appointment.sale_type == "device" or appointment.device_sale_line_ids:
                return "HI"

        item_lines = self._invoice_item_lines()
        if item_lines and all(
            self._is_service_product(l.product_id) for l in item_lines
        ):
            return "DI"
        if item_lines and any(
            self._is_device_product(l.product_id) for l in item_lines
        ):
            return "HI"
        return "HI"

    def _get_invoice_category_code(self):
        self.ensure_one()
        base_code = self._get_base_invoice_category_code()
        if self.move_type == "out_refund":
            return {"DI": "DC", "HI": "HC", "RI": "RC"}.get(base_code, "HC")
        return base_code

    def _get_document_prefix_code(self):
        self.ensure_one()
        taxable = self._is_taxable_move()
        if self.move_type == "out_refund":
            return "TC" if taxable else "CN"
        return "TI" if taxable else "BS"

    def _next_custom_invoice_name(self):
        self.ensure_one()
        doc_code = self._get_document_prefix_code()
        billing_code = self._get_custom_billing_code()
        inv_category = self._get_invoice_category_code()
        state_code = self._get_custom_state_code()
        fy_suffix = self._get_invoice_fy_suffix()

        seq_code = f"resonnocare.inv.{doc_code}.{billing_code}.{state_code}.{fy_suffix}"
        seq_prefix = f"{doc_code}/{billing_code}/{state_code}/{fy_suffix}/"

        sequence = (
            self.env["ir.sequence"].sudo().search([("code", "=", seq_code)], limit=1)
        )
        if not sequence:
            sequence = (
                self.env["ir.sequence"]
                .sudo()
                .create(
                    {
                        "name": f"Resonnocare {seq_prefix}",
                        "code": seq_code,
                        "prefix": seq_prefix,
                        "padding": 5,
                        "implementation": "no_gap",
                        "company_id": False,
                    }
                )
            )
        return sequence.next_by_id(), inv_category

    def _next_unique_custom_invoice_name(self):
        """Generate a collision-safe custom invoice number."""
        self.ensure_one()
        inv_category = self._get_invoice_category_code()
        for _idx in range(5000):
            custom_name, inv_category = self._next_custom_invoice_name()
            duplicate = self.sudo().with_context(active_test=False).search_count(
                [
                    ("id", "!=", self.id),
                    ("journal_id", "=", self.journal_id.id),
                    ("state", "=", "posted"),
                    ("name", "=", custom_name),
                ]
            )
            if not duplicate:
                return custom_name, inv_category
        raise UserError(
            "Could not generate a unique custom invoice number automatically. "
            "Please contact administrator."
        )

    def _use_custom_invoice_numbering_on_post(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "out_refund"):
            return False
        # Keep custom numbering for customer refunds.
        if self.move_type == "out_refund":
            return True

        # Device flow must keep native Odoo numbering on normal invoices.
        if self._is_device_invoice_flow():
            return False

        # Fallback safety for device product lines when appointment link is missing.
        item_lines = self._invoice_item_lines()
        if item_lines and any(self._is_device_product(l.product_id) for l in item_lines):
            return False

        # Service flow keeps custom numbering.
        return True

    def _is_downpayment_invoice(self):
        self.ensure_one()
        return bool(self.invoice_line_ids.filtered(lambda l: l.is_downpayment))

    def _ensure_contract_id(self):
        self.ensure_one()
        if self.contract_id or not self._is_downpayment_invoice():
            return
        appointment = self._get_contract_appointment()
        self.contract_id = (
            appointment.appointment_id
            if appointment and getattr(appointment, "appointment_id", False)
            else ""
        )

    payment_mode = fields.Selection(
        [
            ("cash", "Cash"),
            ("bank", "Bank"),
            ("upi", "UPI / QR"),
            ("cheque", "Cheque"),
            ("paytm", "Paytm"),
        ],
        string="Payment Mode",
    )

    upi_transaction_id = fields.Char("UPI Transaction ID")
    cheque_number = fields.Char("Cheque Number")
    cheque_date = fields.Date("Cheque Date")
    cheque_bank_name = fields.Char("Cheque Bank")
    paytm_txn_id = fields.Char("Paytm Transaction ID")

    warranty_lot_ids = fields.Many2many(
        "stock.lot",
        string="Warranty Lots",
        compute="_compute_warranty_lot_ids",
        store=False,
    )

    @api.depends(
        "invoice_line_ids.sale_line_ids",
        "invoice_line_ids.sale_line_ids.move_ids",
        "invoice_line_ids.sale_line_ids.move_ids.move_line_ids.lot_id",
    )
    def _compute_warranty_lot_ids(self):
        for move in self:
            lots = move.invoice_line_ids.mapped(
                "sale_line_ids.move_ids.move_line_ids.lot_id"
            )
            move.warranty_lot_ids = lots

    def _get_contract_device_lines(self):
        self.ensure_one()

        def is_device_product(product):
            ptype = getattr(product, "type", None)
            detailed = getattr(product, "type", None)
            if ptype:
                return ptype in ("product", "consu")
            if detailed:
                return detailed in ("product", "consu")
            return False

        return self.invoice_line_ids.filtered(
            lambda line: not line.display_type
            and line.product_id
            and not line.is_downpayment
            and is_device_product(line.product_id)
        )

    def _get_contract_sale_order_lines(self):
        self.ensure_one()
        sale_orders = self.invoice_line_ids.sale_line_ids.mapped("order_id")
        if not sale_orders and self.invoice_origin:
            sale_orders = self.env["sale.order"].search(
                [("name", "=", self.invoice_origin)], limit=1
            )
        lines = sale_orders.mapped("order_line")
        return lines.filtered(
            lambda line: line.product_id
            and not line.is_downpayment
            and (
                (getattr(line.product_id, "type", None) in ("product", "consu"))
                or (
                    getattr(line.product_id, "type", None)
                    in ("product", "consu")
                )
            )
        )

    def _get_contract_lines(self):
        self.ensure_one()
        device_lines = self._get_contract_device_lines()
        lines = []

        if device_lines:
            for line in device_lines:
                product = line.product_id
                manufacturer = ""
                if hasattr(product, "manufacturer_id") and product.manufacturer_id:
                    manufacturer = product.manufacturer_id.name or ""
                elif product.product_tmpl_id and getattr(
                    product.product_tmpl_id, "manufacturer_id", False
                ):
                    manufacturer = product.product_tmpl_id.manufacturer_id.name or ""
                tax_info = self._compute_line_tax_breakup(line)
                gross = (line.price_unit or 0.0) * (line.quantity or 0.0)
                discount_amount = gross - (line.price_subtotal or 0.0)
                lines.append(
                    {
                        "manufacturer": manufacturer,
                        "model": product.display_name,
                        "description": line.name
                        or (product.display_name if product else ""),
                        "serial_numbers": line.serial_numbers or "",
                        "device_code": product.default_code
                        or (
                            product.product_tmpl_id.default_code
                            if product.product_tmpl_id
                            else ""
                        ),
                        "hsn_code": self._get_product_hsn_code(product),
                        "item_code": product.default_code if product else "",
                        "brand": manufacturer,
                        "qty": line.quantity,
                        "rate": line.price_unit,
                        "amount": line.price_subtotal,
                        "mrp": line.price_unit or 0.0,
                        "total": gross,
                        "discount": discount_amount,
                        "taxable_value": line.price_subtotal or 0.0,
                        "cgst_rate": tax_info["cgst_rate"],
                        "cgst_amount": tax_info["cgst_amount"],
                        "sgst_rate": tax_info["sgst_rate"],
                        "sgst_amount": tax_info["sgst_amount"],
                        "igst_rate": tax_info["igst_rate"],
                        "igst_amount": tax_info["igst_amount"],
                        "device_type": self._get_device_type_label(product),
                    }
                )
            return lines

        for sol in self._get_contract_sale_order_lines():
            product = sol.product_id
            lots = sol.move_ids.mapped("move_line_ids.lot_id")
            serials = ", ".join(dict.fromkeys([n for n in lots.mapped("name") if n]))
            manufacturer = ""
            if hasattr(product, "manufacturer_id") and product.manufacturer_id:
                manufacturer = product.manufacturer_id.name or ""
            elif product.product_tmpl_id and getattr(
                product.product_tmpl_id, "manufacturer_id", False
            ):
                manufacturer = product.product_tmpl_id.manufacturer_id.name or ""
            qty = sol.product_uom_qty or 0.0
            unit_price = sol.price_unit or 0.0
            gross = qty * unit_price
            discount_pct = sol.discount or 0.0
            discount_amount = gross * (discount_pct / 100.0)
            taxable_value = gross - discount_amount
            tax_info = self._compute_tax_breakup_from_taxes(
                sol.tax_id,
                unit_price,
                qty,
                discount_pct,
                product,
            )
            lines.append(
                {
                    "manufacturer": manufacturer,
                    "model": product.display_name,
                    "description": sol.name
                    or (product.display_name if product else ""),
                    "serial_numbers": serials or "",
                    "device_code": product.default_code
                    or (
                        product.product_tmpl_id.default_code
                        if product.product_tmpl_id
                        else ""
                    ),
                    "hsn_code": self._get_product_hsn_code(product),
                    "item_code": product.default_code if product else "",
                    "brand": manufacturer,
                    "qty": qty,
                    "rate": unit_price,
                    "amount": taxable_value,
                    "mrp": unit_price,
                    "total": gross,
                    "discount": discount_amount,
                    "taxable_value": taxable_value,
                    "cgst_rate": tax_info["cgst_rate"],
                    "cgst_amount": tax_info["cgst_amount"],
                    "sgst_rate": tax_info["sgst_rate"],
                    "sgst_amount": tax_info["sgst_amount"],
                    "igst_rate": tax_info["igst_rate"],
                    "igst_amount": tax_info["igst_amount"],
                    "device_type": self._get_device_type_label(product),
                }
            )
        if lines:
            return lines

        # Fallback: if device filters yield no rows, still show billable lines so
        # contract detail section is not empty for mixed/custom product setups.
        fallback_lines = self.invoice_line_ids.filtered(
            lambda l: not l.display_type and l.product_id and not l.is_downpayment
        )
        for line in fallback_lines:
            product = line.product_id
            manufacturer = ""
            if hasattr(product, "manufacturer_id") and product.manufacturer_id:
                manufacturer = product.manufacturer_id.name or ""
            elif product.product_tmpl_id and getattr(
                product.product_tmpl_id, "manufacturer_id", False
            ):
                manufacturer = product.product_tmpl_id.manufacturer_id.name or ""
            tax_info = self._compute_line_tax_breakup(line)
            gross = (line.price_unit or 0.0) * (line.quantity or 0.0)
            discount_amount = gross - (line.price_subtotal or 0.0)
            lines.append(
                {
                    "manufacturer": manufacturer,
                    "model": product.display_name,
                    "description": line.name
                    or (product.display_name if product else ""),
                    "serial_numbers": line.serial_numbers or "",
                    "device_code": product.default_code
                    or (
                        product.product_tmpl_id.default_code
                        if product.product_tmpl_id
                        else ""
                    ),
                    "hsn_code": self._get_product_hsn_code(product),
                    "item_code": product.default_code if product else "",
                    "brand": manufacturer,
                    "qty": line.quantity,
                    "rate": line.price_unit,
                    "amount": line.price_subtotal,
                    "mrp": line.price_unit or 0.0,
                    "total": gross,
                    "discount": discount_amount,
                    "taxable_value": line.price_subtotal or 0.0,
                    "cgst_rate": tax_info["cgst_rate"],
                    "cgst_amount": tax_info["cgst_amount"],
                    "sgst_rate": tax_info["sgst_rate"],
                    "sgst_amount": tax_info["sgst_amount"],
                    "igst_rate": tax_info["igst_rate"],
                    "igst_amount": tax_info["igst_amount"],
                    "device_type": self._get_device_type_label(product),
                }
            )
        return lines

    def _get_partner_age(self):
        self.ensure_one()
        birthdate = self.partner_id.birthdate_date
        if not birthdate:
            return False
        today = date.today()
        years = today.year - birthdate.year
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            years -= 1
        return years if years >= 0 else False

    def _get_device_type_label(self, product):
        if product and product.categ_id:
            return product.categ_id.display_name or product.categ_id.name or ""
        return ""

    def _get_discount_amount(self):
        self.ensure_one()
        total = 0.0
        for line in self.invoice_line_ids.filtered(
            lambda l: l.display_type == "product"
        ):
            if line.discount:
                total += (line.price_unit * line.quantity) * (line.discount / 100.0)
        return total

    def _get_product_hsn_code(self, product):
        if not product:
            return ""
        for field_name in ("l10n_in_hsn_code", "hs_code", "hs_code_id"):
            if hasattr(product, field_name):
                value = getattr(product, field_name)
                if not value and product.product_tmpl_id:
                    value = getattr(product.product_tmpl_id, field_name, False)
                if value:
                    return value.name if hasattr(value, "name") else value
        return ""

    def _get_contract_fitting_date(self):
        self.ensure_one()
        if not self.invoice_date:
            return False
        return self.invoice_date + timedelta(days=10)

    def _get_tax_labels(self):
        self.ensure_one()
        taxes = self.invoice_line_ids.mapped("tax_ids")
        names = [
            t.invoice_label or t.name for t in taxes if (t.invoice_label or t.name)
        ]
        return ", ".join(dict.fromkeys(names))

    def _is_b2c_coco_invoice(self):
        self.ensure_one()
        clinic = self.clinic_id
        if (
            not clinic
            and self.partner_id
            and getattr(self.partner_id, "clinic_id", False)
        ):
            clinic = self.partner_id.clinic_id
        if not clinic:
            return False
        if hasattr(clinic, "_get_effective_billing_type"):
            return clinic._get_effective_billing_type() == "b2c"
        return clinic.clinic_type in ("b2c", "coco")

    def _is_b2b_invoice(self):
        self.ensure_one()
        clinic = self.clinic_id
        if (
            not clinic
            and self.partner_id
            and getattr(self.partner_id, "clinic_id", False)
        ):
            clinic = self.partner_id.clinic_id
        if not clinic:
            return False
        if hasattr(clinic, "_get_effective_billing_type"):
            return clinic._get_effective_billing_type() == "b2b"
        return clinic.clinic_type == "b2b"

    def _use_custom_invoice_layout(self):
        self.ensure_one()
        return self._is_b2c_coco_invoice() or self._is_b2b_invoice()

    def _use_b2b_debug_layout_for_testing(self):
        self.ensure_one()
        # Temporary debug switch: render B2B invoice format for COCO clinic.
        # Set to False after finalizing the format.
        debug_force_b2b_on_coco = True
        if not debug_force_b2b_on_coco:
            return False
        clinic = self.clinic_id
        if (
            not clinic
            and self.partner_id
            and getattr(self.partner_id, "clinic_id", False)
        ):
            clinic = self.partner_id.clinic_id
        return bool(clinic and clinic.clinic_type == "coco")

    def _compute_tax_breakup_from_taxes(
        self, taxes, price_unit, quantity, discount=0.0, product=False
    ):
        self.ensure_one()
        result = {
            "cgst_rate": 0.0,
            "cgst_amount": 0.0,
            "sgst_rate": 0.0,
            "sgst_amount": 0.0,
            "igst_rate": 0.0,
            "igst_amount": 0.0,
            "gst_rate_total": 0.0,
        }
        base_price = (price_unit or 0.0) * (1 - (discount or 0.0) / 100.0)
        tax_data = taxes.compute_all(
            base_price,
            currency=self.currency_id,
            quantity=quantity or 0.0,
            product=product,
            partner=self.partner_id,
        )
        tax_id_to_record = {tax.id: tax for tax in taxes}
        for tax_val in tax_data.get("taxes", []):
            tax_rec = tax_id_to_record.get(tax_val.get("id"))
            tax_name = (tax_val.get("name") or "").upper()
            tax_rate = tax_rec.amount if tax_rec else 0.0
            tax_amt = tax_val.get("amount", 0.0) or 0.0
            if "CGST" in tax_name:
                result["cgst_rate"] += tax_rate
                result["cgst_amount"] += tax_amt
            elif "SGST" in tax_name or "UTGST" in tax_name:
                result["sgst_rate"] += tax_rate
                result["sgst_amount"] += tax_amt
            elif "IGST" in tax_name:
                result["igst_rate"] += tax_rate
                result["igst_amount"] += tax_amt
        result["gst_rate_total"] = (
            result["cgst_rate"] + result["sgst_rate"] + result["igst_rate"]
        )
        return result

    def _compute_line_tax_breakup(self, line):
        self.ensure_one()
        return self._compute_tax_breakup_from_taxes(
            line.tax_ids,
            line.price_unit,
            line.quantity,
            line.discount,
            line.product_id,
        )

    def _get_b2c_report_lines(self):
        self.ensure_one()
        rows = []
        for idx, line in enumerate(self._invoice_item_lines(), start=1):
            product = line.product_id
            brand = ""
            if (
                product
                and hasattr(product, "manufacturer_id")
                and product.manufacturer_id
            ):
                brand = product.manufacturer_id.name or ""
            elif (
                product
                and product.product_tmpl_id
                and getattr(product.product_tmpl_id, "manufacturer_id", False)
            ):
                brand = product.product_tmpl_id.manufacturer_id.name or ""
            tax_info = self._compute_line_tax_breakup(line)
            gross = (line.price_unit or 0.0) * (line.quantity or 0.0)
            discount_amount = gross - (line.price_subtotal or 0.0)
            rows.append(
                {
                    "sl_no": idx,
                    "description": line.name
                    or (product.display_name if product else ""),
                    "hsn": self._get_product_hsn_code(product),
                    "item_code": product.default_code if product else "",
                    "brand": brand,
                    "qty": line.quantity or 0.0,
                    "mrp": line.price_unit or 0.0,
                    "total": gross,
                    "discount": discount_amount,
                    "taxable_value": line.price_subtotal or 0.0,
                    "cgst_rate": tax_info["cgst_rate"],
                    "cgst_amount": tax_info["cgst_amount"],
                    "sgst_rate": tax_info["sgst_rate"],
                    "sgst_amount": tax_info["sgst_amount"],
                    "igst_rate": tax_info["igst_rate"],
                    "igst_amount": tax_info["igst_amount"],
                    "gst_rate_total": tax_info["gst_rate_total"],
                }
            )
        return rows

    def _get_b2b_report_lines(self):
        self.ensure_one()
        rows = []
        for idx, line in enumerate(self._invoice_item_lines(), start=1):
            product = line.product_id
            brand = ""
            if (
                product
                and hasattr(product, "manufacturer_id")
                and product.manufacturer_id
            ):
                brand = product.manufacturer_id.name or ""
            elif (
                product
                and product.product_tmpl_id
                and getattr(product.product_tmpl_id, "manufacturer_id", False)
            ):
                brand = product.product_tmpl_id.manufacturer_id.name or ""
            tax_info = self._compute_line_tax_breakup(line)
            gross = (line.price_unit or 0.0) * (line.quantity or 0.0)
            sale_line = line.sale_line_ids[:1]
            has_sharing = sale_line and "clinic_sharing_pct" in sale_line._fields
            hospital_sharing_pct = (
                sale_line.clinic_sharing_pct if has_sharing else 0.0
            ) or 0.0
            hospital_sharing_amount = (
                sale_line.clinic_sharing_amount if has_sharing else 0.0
            ) or 0.0
            rows.append(
                {
                    "sl_no": idx,
                    "description": line.name
                    or (product.display_name if product else ""),
                    "hsn": self._get_product_hsn_code(product),
                    "item_code": product.default_code if product else "",
                    "brand": brand,
                    "qty": line.quantity or 0.0,
                    "patient_selling_price": line.price_unit or 0.0,
                    "hospital_sharing_pct": hospital_sharing_pct,
                    "hospital_sharing_amount": hospital_sharing_amount,
                    "invoice_value": line.price_subtotal or 0.0,
                    "cgst_rate": tax_info["cgst_rate"],
                    "cgst_amount": tax_info["cgst_amount"],
                    "sgst_rate": tax_info["sgst_rate"],
                    "sgst_amount": tax_info["sgst_amount"],
                    "igst_rate": tax_info["igst_rate"],
                    "igst_amount": tax_info["igst_amount"],
                    "gst_rate_total": tax_info["gst_rate_total"],
                    "gross": gross,
                    "taxable_value": line.price_subtotal or 0.0,
                }
            )
        return rows

    def _get_b2c_hsn_summary(self):
        self.ensure_one()
        summary = {}
        for row in self._get_b2c_report_lines():
            key = (row["hsn"] or "", row["gst_rate_total"] or 0.0)
            if key not in summary:
                summary[key] = {
                    "hsn": key[0],
                    "qty": 0.0,
                    "rate": key[1],
                    "taxable_value": 0.0,
                }
            summary[key]["qty"] += row["qty"]
            summary[key]["taxable_value"] += row["taxable_value"]
        return list(summary.values())

    def _get_b2b_hsn_summary(self):
        self.ensure_one()
        summary = {}
        for row in self._get_b2b_report_lines():
            key = (row["hsn"] or "", row["gst_rate_total"] or 0.0)
            if key not in summary:
                summary[key] = {
                    "hsn": key[0],
                    "qty": 0.0,
                    "rate": key[1],
                    "taxable_value": 0.0,
                }
            summary[key]["qty"] += row["qty"]
            summary[key]["taxable_value"] += row["taxable_value"]
        return list(summary.values())

    def _get_b2c_payment_lines(self):
        self.ensure_one()
        result = []
        payment_list = self.reconciled_payment_ids.sorted(
            lambda p: (p.date or fields.Date.context_today(self), p.id)
        )
        for idx, payment in enumerate(payment_list, start=1):
            mode = payment.journal_id.name or ""
            ref = (
                getattr(payment, "paytm_txn_id", False)
                or getattr(payment, "upi_transaction_id", False)
                or getattr(payment, "payment_ref", False)
                or getattr(payment, "ref", False)
                or payment.name
                or ""
            )
            pay_amt = payment.amount or 0.0
            if payment.currency_id and payment.currency_id != self.currency_id:
                pay_amt = payment.currency_id._convert(
                    payment.amount or 0.0,
                    self.currency_id,
                    self.company_id,
                    payment.date
                    or self.invoice_date
                    or fields.Date.context_today(self),
                )
            result.append(
                {
                    "sl_no": idx,
                    "receipt_no": payment.name or "",
                    "paid_on": payment.date,
                    "payment_mode": mode,
                    "reference": ref,
                    "cheque_date": (
                        payment.cheque_date
                        if hasattr(payment, "cheque_date")
                        else False
                    ),
                    "amount": pay_amt,
                }
            )
        return result

    def _format_amount_compact(self, amount):
        self.ensure_one()
        value = amount or 0.0
        text = f"{value:,.2f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def _get_contract_sale_order(self):
        self.ensure_one()
        sale_orders = self.invoice_line_ids.sale_line_ids.mapped("order_id")
        if not sale_orders and self.invoice_origin:
            sale_orders = self.env["sale.order"].search(
                [("name", "=", self.invoice_origin)], limit=1
            )
        return sale_orders[:1]

    def _get_contract_appointment(self):
        self.ensure_one()
        sale = self._get_contract_sale_order()
        if sale:
            appointment = self.env["resonnocare.appointment"].search(
                [("sale_order_id", "=", sale.id)], limit=1
            )
            if appointment:
                return appointment
        if self.invoice_origin:
            return self.env["resonnocare.appointment"].search(
                [("appointment_id", "=", self.invoice_origin)], limit=1
            )
        return self.env["resonnocare.appointment"]

    def _get_contract_total_payable(self):
        self.ensure_one()
        sale = self._get_contract_sale_order()
        return sale.amount_total if sale else self.amount_total

    def _get_contract_related_customer_invoices(self, sale):
        self.ensure_one()
        sale_sudo = sale.sudo()
        invoices = sale_sudo.invoice_ids.filtered(
            lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
        )
        invoices |= sale_sudo.order_line.mapped("invoice_lines.move_id").filtered(
            lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
        )
        invoice_model = self.env["account.move"].sudo()
        invoices |= invoice_model.search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "!=", "cancel"),
                ("invoice_line_ids.sale_line_ids.order_id", "=", sale_sudo.id),
            ]
        )
        invoices |= invoice_model.search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "!=", "cancel"),
                ("invoice_origin", "ilike", sale_sudo.name),
            ]
        )
        return invoices

    def _get_contract_total_paid(self):
        self.ensure_one()
        sale = self._get_contract_sale_order()
        if not sale:
            return self._get_contract_advance_paid()
        invoices = self._get_contract_related_customer_invoices(sale).filtered(
            lambda inv: inv.state == "posted"
        )
        total_paid = sum(inv._get_contract_advance_paid() for inv in invoices)
        return total_paid if total_paid > 0 else 0.0

    def _get_contract_advance_paid(self):
        self.ensure_one()
        paid = 0.0
        if self.state == "posted":
            try:
                self._compute_payments_widget_reconciled_info()
            except Exception:
                pass
            widget = self.invoice_payments_widget
            if widget:
                try:
                    if isinstance(widget, (bytes, bytearray)):
                        widget = widget.decode()
                    if isinstance(widget, str):
                        widget = loads(widget)
                    if isinstance(widget, dict):
                        for line in widget.get("content", []):
                            paid += line.get("amount", 0.0) or 0.0
                except Exception:
                    paid = paid or 0.0
        if not paid:
            partials = self._get_all_reconciled_invoice_partials()
            for partial in partials:
                paid += partial.get("amount", 0.0) or 0.0
        if not paid:
            payments = self.reconciled_payment_ids | self.matched_payment_ids
            if payments:
                paid = self._sum_payments_amount(payments)
        if not paid:
            paid = (self.amount_total or 0.0) - (self.amount_residual or 0.0)
        return paid if paid > 0 else 0.0

    def _get_contract_balance_due(self):
        self.ensure_one()
        total = self._get_contract_total_payable()
        advance = self._get_contract_total_paid()
        balance = total - advance
        return balance if balance > 0 else 0.0

    def action_print_contract(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            raise UserError("Contract is available only for customer invoices.")
        if not self._is_downpayment_invoice():
            raise UserError("Contract is available only for down payment invoices.")
        self._ensure_contract_id()
        contract_lines = self._get_contract_lines()
        if not contract_lines:
            raise UserError("No device sale lines found for this invoice.")
        return self.env.ref(
            "resonnocare_appointment.action_report_device_contract"
        ).report_action(self)

    def action_view_contract(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            raise UserError("Contract is available only for customer invoices.")
        if not self._is_downpayment_invoice():
            raise UserError("Contract is available only for down payment invoices.")
        self._ensure_contract_id()
        contract_lines = self._get_contract_lines()
        if not contract_lines:
            raise UserError("No device sale lines found for this invoice.")
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/report/pdf/resonnocare_appointment.report_device_contract_document/{self.id}"
                "?download=false"
            ),
            "target": "self",
        }

    def action_print_payment_receipt(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            raise UserError("Payment receipt is available only for customer invoices.")
        payments = (
            (self.reconciled_payment_ids | self.matched_payment_ids)
            .filtered(
                lambda p: p.partner_type == "customer"
                and p.payment_type == "inbound"
                and p.state in ("in_process", "paid", "posted")
            )
            .sorted(
                lambda p: (p.date or fields.Date.context_today(self), p.id),
                reverse=True,
            )
        )
        if not payments:
            try:
                self._compute_payments_widget_reconciled_info()
            except Exception:
                pass
            widget = self.invoice_payments_widget
            if isinstance(widget, (bytes, bytearray)):
                widget = widget.decode()
            if isinstance(widget, str):
                try:
                    widget = loads(widget)
                except Exception:
                    widget = {}
            widget = widget or {}
            payment_ids = [
                row.get("account_payment_id")
                for row in widget.get("content", [])
                if row.get("account_payment_id")
            ]
            if payment_ids:
                payments = (
                    self.env["account.payment"]
                    .browse(payment_ids)
                    .filtered(
                        lambda p: p.partner_type == "customer"
                        and p.payment_type == "inbound"
                        and p.state in ("in_process", "paid", "posted")
                    )
                    .sorted(
                        lambda p: (p.date or fields.Date.context_today(self), p.id),
                        reverse=True,
                    )
                )
        if not payments:
            payments = self.env["account.payment"].search(
                [
                    ("partner_id", "=", self.partner_id.id),
                    ("partner_type", "=", "customer"),
                    ("payment_type", "=", "inbound"),
                    ("state", "in", ("in_process", "paid", "posted")),
                    ("memo", "=", self.name),
                ],
                order="date desc, id desc",
                limit=1,
            )
        if not payments:
            raise UserError("No validated customer payment found for this invoice.")
        report = self.env.ref("account.action_report_payment_receipt")
        return report.report_action(payments[:1])

    def action_print_final_invoice(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            raise UserError("Final invoice is available only for customer invoices.")
        if self.state != "posted":
            raise UserError("Post the invoice before printing final invoice.")
        currency = self.currency_id or self.company_currency_id
        residual = self.amount_residual or 0.0
        fully_paid = self.payment_state == "paid" or float_is_zero(
            residual,
            precision_rounding=(currency.rounding if currency else 0.01),
        )
        if not fully_paid:
            raise UserError(
                "Final invoice can be printed only after full payment is completed."
            )
        # Reuse standard invoice report action so existing custom invoice layout is preserved.
        return self.action_invoice_print()

    def action_post(self):
        # Normalize draft names before posting:
        # always force "/" so Odoo assigns a fresh unique sequence for current date/FY.
        # This avoids duplicate-name collisions from copied/imported/stale draft names.
        stale_named_drafts = self.filtered(
            lambda m: m.state == "draft"
            and m.move_type in ("out_invoice", "out_refund")
            and m.name
            and m.name != "/"
        )
        if stale_named_drafts:
            ids = tuple(stale_named_drafts.ids)
            self.env.cr.execute(
                """
                UPDATE account_move
                   SET name = '/',
                       sequence_prefix = '',
                       sequence_number = 0
                 WHERE id IN %s
                """,
                [ids],
            )
            stale_named_drafts.invalidate_recordset(
                ["name", "sequence_prefix", "sequence_number"]
            )

        res = super().action_post()
        target_moves = self.filtered(
            lambda m: m.move_type in ("out_invoice", "out_refund")
        )
        for move in target_moves:
            category_code = move._get_invoice_category_code()
            vals = {"custom_invoice_category": category_code}
            if move._use_custom_invoice_numbering_on_post():
                custom_name, _category = move._next_unique_custom_invoice_name()
                vals["name"] = custom_name
                vals["custom_invoice_category"] = _category
            move.with_context(check_move_validity=False).write(vals)
        for move in self.filtered(lambda m: m.move_type == "out_invoice"):
            move._ensure_contract_id()
        # ✅ Recompute supply eligibility after payment posted
        self._recompute_related_supply_eligibility()
        return res

    def _recompute_related_supply_eligibility(self):
        """After invoice is posted, recompute is_supply_eligible on related supply pickings."""
        for move in self:
            sale = move.invoice_line_ids.mapped("sale_line_ids.order_id")[:1]
            if not sale:
                continue
            appointments = self.env["resonnocare.appointment"].search(
                [("sale_order_id", "=", sale.id)]
            )
            for appt in appointments:
                pickings = self.env["stock.picking"].search(
                    [
                        ("origin", "in", [appt.appointment_id, appt.name]),
                        ("is_clinic_supply", "=", True),
                        ("state", "not in", ("done", "cancel")),
                    ]
                )
                if pickings:
                    pickings._compute_is_supply_eligible()

    def _must_check_constrains_date_sequence(self):
        # Skip date/sequence constraint for customer invoices/refunds.
        # This avoids repeated posting blockers on reused/legacy draft names
        # when invoice date/fiscal-year changes.
        if any(m.move_type in ("out_invoice", "out_refund") for m in self):
            return False
        # Keep prior bypass for legacy custom names on any remaining move types.
        for move in self:
            if (
                move.move_type in ("out_invoice", "out_refund")
                and move.name
                and self._CUSTOM_INV_REGEX.match(move.name)
            ):
                return False
        return super()._must_check_constrains_date_sequence()

    def _check_date_sequence(self):
        """Skip standard date/sequence validation for Resonnocare custom invoice names.

        Odoo's date-based sequence check rejects changes when the number already
        encodes a different date range. Our custom numbering embeds FY/state/billing
        and does not follow Odoo's date-range sequence format, so we bypass it.
        """
        bypass = self.filtered(
            lambda m: m.move_type in ("out_invoice", "out_refund")
            and m.name
            and (
                self._CUSTOM_INV_REGEX.match(m.name)
                or m.name.startswith("INV/")
            )
        )
        remaining = self - bypass
        if remaining:
            return super(AccountMove, remaining)._check_date_sequence()
        return True

    def _get_last_sequence_domain(self, relaxed=False):
        """Keep normal invoice sequencing independent from legacy TI/BS custom names."""
        where_string, params = super()._get_last_sequence_domain(relaxed=relaxed)
        self.ensure_one()
        if self.move_type in ("out_invoice", "out_refund"):
            params = dict(params or {})
            params.update(
                {
                    "rn_prefix_ti": "TI/%",
                    "rn_prefix_bs": "BS/%",
                    "rn_prefix_tc": "TC/%",
                    "rn_prefix_cn": "CN/%",
                }
            )
            where_string += (
                " AND sequence_prefix NOT LIKE %(rn_prefix_ti)s"
                " AND sequence_prefix NOT LIKE %(rn_prefix_bs)s"
                " AND sequence_prefix NOT LIKE %(rn_prefix_tc)s"
                " AND sequence_prefix NOT LIKE %(rn_prefix_cn)s"
            )
        return where_string, params
