from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    _RESONNOCARE_INPUT_CODES = (
        "RES_ATTN_DED_DAYS",
        "RES_ATTN_LWP_DAYS",
        "RES_ATTN_PL_DAYS",
        "RES_REIMB_EXEMPT",
        "RES_TDS_MONTHLY",
    )

    res_payable_days = fields.Float(
        string="Payable Days",
        compute="_compute_resonnocare_payroll_snapshot",
    )
    res_lop_days = fields.Float(
        string="LOP Days",
        compute="_compute_resonnocare_payroll_snapshot",
    )
    res_currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
    )
    res_approved_claim_amount = fields.Monetary(
        string="Approved Claims (Tax Exempt)",
        currency_field="res_currency_id",
        compute="_compute_resonnocare_payroll_snapshot",
    )

    def _resonnocare_get_attendance_deduction_totals(self):
        self.ensure_one()
        if not self.employee_id or not self.date_from or not self.date_to:
            return {"total": 0.0, "lwp": 0.0, "pl": 0.0}

        summaries = self.env["resonnocare.attendance.summary"].sudo().search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
                ("payroll_deduction_days", ">", 0),
            ]
        )
        total_days = sum(summaries.mapped("payroll_deduction_days"))
        lwp_days = sum(
            summaries.filtered(lambda s: s.payroll_deduction_type == "lwp").mapped("payroll_deduction_days")
        )
        pl_days = sum(
            summaries.filtered(lambda s: s.payroll_deduction_type == "pl").mapped("payroll_deduction_days")
        )
        return {"total": total_days, "lwp": lwp_days, "pl": pl_days}

    def _resonnocare_get_basis_days(self):
        self.ensure_one()
        if not self.date_from or not self.date_to:
            return 30.0
        basis = "actual"
        if self.contract_id and "res_payroll_day_basis" in self.contract_id._fields:
            basis = self.contract_id.res_payroll_day_basis or "actual"
        if basis == "fixed_26":
            return 26.0
        if basis == "fixed_30":
            return 30.0
        return float((self.date_to - self.date_from).days + 1)

    def _resonnocare_sync_attendance_inputs(self):
        for slip in self:
            if not slip.contract_id:
                continue

            totals = slip._resonnocare_get_attendance_deduction_totals()
            keep_codes = {
                "RES_ATTN_DED_DAYS": totals["total"],
                "RES_ATTN_LWP_DAYS": totals["lwp"],
                "RES_ATTN_PL_DAYS": totals["pl"],
            }

            existing = slip.input_line_ids.filtered(
                lambda line: line.code in self._RESONNOCARE_INPUT_CODES
            )
            if existing:
                existing.unlink()

            for code, days in keep_codes.items():
                if days <= 0:
                    continue
                self.env["hr.payslip.input"].create(
                    {
                        "name": _("Resonnocare Attendance Deduction (%s)") % code,
                        "payslip_id": slip.id,
                        "code": code,
                        "amount": days,
                        "amount_qty": days,
                        "contract_id": slip.contract_id.id,
                    }
                )

    def _resonnocare_get_claim_totals(self):
        self.ensure_one()
        if "resonnocare.payroll.claim" not in self.env:
            return {"amount": 0.0, "ids": []}
        if not self.employee_id or not self.date_from or not self.date_to:
            return {"amount": 0.0, "ids": []}

        claim_domain = [
            ("employee_id", "=", self.employee_id.id),
            ("claim_date", ">=", self.date_from),
            ("claim_date", "<=", self.date_to),
            ("state", "=", "hr_approved"),
            ("is_tax_exempt", "=", True),
            "|",
            ("payslip_id", "=", False),
            ("payslip_id", "=", self.id),
        ]
        claims = self.env["resonnocare.payroll.claim"].sudo().search(claim_domain)
        return {
            "amount": sum(claims.mapped("amount_approved")),
            "ids": claims.ids,
        }

    def _resonnocare_sync_claim_inputs(self):
        for slip in self:
            if not slip.contract_id:
                continue
            totals = slip._resonnocare_get_claim_totals()

            existing = slip.input_line_ids.filtered(lambda line: line.code == "RES_REIMB_EXEMPT")
            if existing:
                existing.unlink()

            if totals["amount"] > 0:
                self.env["hr.payslip.input"].create(
                    {
                        "name": _("Resonnocare Approved Reimbursements"),
                        "payslip_id": slip.id,
                        "code": "RES_REIMB_EXEMPT",
                        "amount": totals["amount"],
                        "amount_qty": 1.0,
                        "contract_id": slip.contract_id.id,
                    }
                )
            if totals["ids"]:
                self.env["resonnocare.payroll.claim"].sudo().browse(totals["ids"]).write(
                    {"payslip_id": slip.id}
                )

    def _resonnocare_sync_tds_inputs(self):
        for slip in self:
            if not slip.contract_id:
                continue
            existing = slip.input_line_ids.filtered(lambda line: line.code == "RES_TDS_MONTHLY")
            if existing:
                existing.unlink()
            monthly_tds = (
                slip.contract_id.res_monthly_tds
                if "res_monthly_tds" in slip.contract_id._fields
                else 0.0
            )
            if monthly_tds and monthly_tds > 0:
                self.env["hr.payslip.input"].create(
                    {
                        "name": _("Resonnocare Monthly TDS"),
                        "payslip_id": slip.id,
                        "code": "RES_TDS_MONTHLY",
                        "amount": monthly_tds,
                        "amount_qty": 1.0,
                        "contract_id": slip.contract_id.id,
                    }
                )

    def _resonnocare_get_structure_chain(self, structure):
        if not structure:
            return structure
        if hasattr(structure, "get_structure_with_parents"):
            return structure.get_structure_with_parents() | structure
        return structure

    def _resonnocare_get_deduction_category(self, company):
        category_model = self.env["hr.salary.rule.category"].sudo()
        category = category_model.search(
            [("code", "=", "DED"), ("company_id", "in", [company.id, False])],
            order="company_id desc, id asc",
            limit=1,
        )
        if category:
            return category
        return category_model.create(
            {
                "name": "Deductions",
                "code": "DED",
                "company_id": company.id,
            }
        )

    def _resonnocare_ensure_lwp_deduction_rule(self):
        salary_rule_model = self.env["hr.salary.rule"].sudo()
        input_model = self.env["hr.rule.input"].sudo()
        structure_model = self.env["hr.payroll.structure"].sudo()
        for slip in self:
            structure = slip.struct_id or slip.contract_id.struct_id
            if not structure:
                continue
            company = slip.company_id or self.env.company
            category = self._resonnocare_get_deduction_category(company)

            rule = salary_rule_model.search(
                [("code", "=", "RES_LWP_DED"), ("company_id", "=", company.id)],
                limit=1,
            )
            if not rule:
                rule = salary_rule_model.create(
                    {
                        "name": "Resonnocare LWP Deduction",
                        "code": "RES_LWP_DED",
                        "sequence": 960,
                        "company_id": company.id,
                        "category_id": category.id,
                        "condition_select": "none",
                        "amount_select": "code",
                        "amount_python_compute": (
                            "days = inputs.RES_ATTN_LWP_DAYS.amount if inputs.RES_ATTN_LWP_DAYS else 0.0\n"
                            "divisor = 30.0\n"
                            "if contract and hasattr(contract, 'res_payroll_day_basis'):\n"
                            "    if contract.res_payroll_day_basis == 'fixed_26':\n"
                            "        divisor = 26.0\n"
                            "    elif contract.res_payroll_day_basis == 'fixed_30':\n"
                            "        divisor = 30.0\n"
                            "    elif payslip and payslip.date_from and payslip.date_to:\n"
                            "        divisor = float((payslip.date_to - payslip.date_from).days + 1)\n"
                            "daily = (contract.wage / divisor) if contract and contract.wage and divisor else 0.0\n"
                            "result = -1.0 * days * daily"
                        ),
                        "quantity": "1.0",
                        "appears_on_payslip": True,
                    }
                )

            if not rule.input_ids.filtered(lambda x: x.code == "RES_ATTN_LWP_DAYS"):
                input_model.create(
                    {
                        "name": "Resonnocare LWP Days",
                        "code": "RES_ATTN_LWP_DAYS",
                        "input_id": rule.id,
                    }
                )

            reimb_rule = salary_rule_model.search(
                [("code", "=", "RES_REIMB_EXEMPT"), ("company_id", "=", company.id)],
                limit=1,
            )
            if not reimb_rule:
                allowance_category = self.env["hr.salary.rule.category"].sudo().search(
                    [("code", "=", "ALW"), ("company_id", "in", [company.id, False])],
                    order="company_id desc, id asc",
                    limit=1,
                )
                if not allowance_category:
                    allowance_category = category
                reimb_rule = salary_rule_model.create(
                    {
                        "name": "Resonnocare Reimbursement (Tax Exempt)",
                        "code": "RES_REIMB_EXEMPT",
                        "sequence": 220,
                        "company_id": company.id,
                        "category_id": allowance_category.id,
                        "condition_select": "none",
                        "amount_select": "code",
                        "amount_python_compute": (
                            "result = inputs.RES_REIMB_EXEMPT.amount if inputs.RES_REIMB_EXEMPT else 0.0"
                        ),
                        "quantity": "1.0",
                        "appears_on_payslip": True,
                    }
                )

            if not reimb_rule.input_ids.filtered(lambda x: x.code == "RES_REIMB_EXEMPT"):
                input_model.create(
                    {
                        "name": "Resonnocare Approved Reimbursement",
                        "code": "RES_REIMB_EXEMPT",
                        "input_id": reimb_rule.id,
                    }
                )

            tds_rule = salary_rule_model.search(
                [("code", "=", "RES_TDS_MONTHLY"), ("company_id", "=", company.id)],
                limit=1,
            )
            if not tds_rule:
                tds_rule = salary_rule_model.create(
                    {
                        "name": "Resonnocare Monthly TDS",
                        "code": "RES_TDS_MONTHLY",
                        "sequence": 970,
                        "company_id": company.id,
                        "category_id": category.id,
                        "condition_select": "none",
                        "amount_select": "code",
                        "amount_python_compute": (
                            "result = -1.0 * (inputs.RES_TDS_MONTHLY.amount if inputs.RES_TDS_MONTHLY else 0.0)"
                        ),
                        "quantity": "1.0",
                        "appears_on_payslip": True,
                    }
                )

            if not tds_rule.input_ids.filtered(lambda x: x.code == "RES_TDS_MONTHLY"):
                input_model.create(
                    {
                        "name": "Resonnocare TDS Input",
                        "code": "RES_TDS_MONTHLY",
                        "input_id": tds_rule.id,
                    }
                )

            full_structures = self._resonnocare_get_structure_chain(structure)
            for each_structure in full_structures:
                if rule.id not in each_structure.rule_ids.ids:
                    each_structure.write({"rule_ids": [(4, rule.id)]})
                if reimb_rule.id not in each_structure.rule_ids.ids:
                    each_structure.write({"rule_ids": [(4, reimb_rule.id)]})
                if tds_rule.id not in each_structure.rule_ids.ids:
                    each_structure.write({"rule_ids": [(4, tds_rule.id)]})

    def _resonnocare_ensure_statutory_rules(self):
        salary_rule_model = self.env["hr.salary.rule"].sudo()
        for slip in self:
            contract = slip.contract_id
            if not contract:
                continue
            structure = slip.struct_id or contract.struct_id
            if not structure:
                continue
            company = slip.company_id or self.env.company
            category = self._resonnocare_get_deduction_category(company)
            full_structures = self._resonnocare_get_structure_chain(structure)

            def ensure_rule(code, name, python_compute):
                rule = salary_rule_model.search(
                    [("code", "=", code), ("company_id", "=", company.id)],
                    limit=1,
                )
                if not rule:
                    rule = salary_rule_model.create(
                        {
                            "name": name,
                            "code": code,
                            "sequence": 980,
                            "company_id": company.id,
                            "category_id": category.id,
                            "condition_select": "none",
                            "amount_select": "code",
                            "amount_python_compute": python_compute,
                            "quantity": "1.0",
                            "appears_on_payslip": True,
                        }
                    )
                for each_structure in full_structures:
                    if rule.id not in each_structure.rule_ids.ids:
                        each_structure.write({"rule_ids": [(4, rule.id)]})
                return rule

            if hasattr(contract, "res_pf_applicable") and contract.res_pf_applicable:
                ensure_rule(
                    "RES_PF_DED",
                    "Resonnocare PF Deduction",
                    "result = -1.0 * ((contract.wage or 0.0) * ((contract.res_pf_employee_rate or 0.0) / 100.0))",
                )
            if hasattr(contract, "res_esic_applicable") and contract.res_esic_applicable:
                ensure_rule(
                    "RES_ESIC_DED",
                    "Resonnocare ESIC Deduction",
                    "result = -1.0 * ((contract.wage or 0.0) * ((contract.res_esic_employee_rate or 0.0) / 100.0))",
                )
            if hasattr(contract, "res_pt_applicable") and contract.res_pt_applicable:
                ensure_rule(
                    "RES_PT_DED",
                    "Resonnocare Professional Tax Deduction",
                    "result = -1.0 * (contract.res_pt_monthly_amount or 0.0)",
                )

    @api.depends(
        "employee_id",
        "date_from",
        "date_to",
        "company_id",
    )
    def _compute_resonnocare_payroll_snapshot(self):
        for slip in self:
            payable_days = 0.0
            lop_days = 0.0
            claim_amount = 0.0
            if slip.employee_id and slip.date_from and slip.date_to:
                total_days = slip._resonnocare_get_basis_days()
                summaries = self.env["resonnocare.attendance.summary"].sudo().search(
                    [
                        ("employee_id", "=", slip.employee_id.id),
                        ("date", ">=", slip.date_from),
                        ("date", "<=", slip.date_to),
                    ]
                )
                lop_days = sum(
                    summaries.filtered(lambda s: s.payroll_deduction_type == "lwp").mapped(
                        "payroll_deduction_days"
                    )
                )
                payable_days = max(total_days - lop_days, 0.0)
                claim_amount = slip._resonnocare_get_claim_totals().get("amount", 0.0)
            slip.res_lop_days = lop_days
            slip.res_payable_days = payable_days
            slip.res_approved_claim_amount = claim_amount

    def compute_sheet(self):
        for slip in self:
            summaries = self.env["resonnocare.attendance.summary"].sudo().search(
                [
                    ("employee_id", "=", slip.employee_id.id),
                    ("date", ">=", slip.date_from),
                    ("date", "<=", slip.date_to),
                    ("payroll_window_started_on", "!=", False),
                    ("payroll_locked", "=", False),
                ],
                limit=1,
            )
            if summaries:
                raise UserError(
                    _(
                        "Payroll cannot be finalized yet for %(employee)s. "
                        "Manager review window is still open for attendance cycle.",
                        employee=slip.employee_id.name,
                    )
                )

        if (
            "hr.salary.rule" in self.env
            and "hr.salary.rule.category" in self.env
            and "hr.rule.input" in self.env
            and "hr.payroll.structure" in self.env
        ):
            self._resonnocare_ensure_lwp_deduction_rule()
            self._resonnocare_ensure_statutory_rules()
        self._resonnocare_sync_attendance_inputs()
        self._resonnocare_sync_claim_inputs()
        self._resonnocare_sync_tds_inputs()
        return super().compute_sheet()

    def res_get_approved_claim_lines(self):
        self.ensure_one()
        if "resonnocare.payroll.claim" not in self.env:
            return self.env["resonnocare.payroll.claim"]
        return self.env["resonnocare.payroll.claim"].sudo().search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("claim_date", ">=", self.date_from),
                ("claim_date", "<=", self.date_to),
                ("state", "=", "hr_approved"),
                ("is_tax_exempt", "=", True),
            ],
            order="claim_date asc, id asc",
        )

    def res_get_total_approved_claim_amount(self):
        self.ensure_one()
        return sum(self.res_get_approved_claim_lines().mapped("amount_approved"))

    @api.model
    def _cron_generate_salary_day_payslips(self):
        """
        Generate draft payslips on salary day for the latest completed 26->25 cycle.
        """
        policy = self.env["resonnocare.attendance.policy"].search(
            [("active", "=", True)], order="priority asc, id asc", limit=1
        )
        salary_day = policy.salary_day if policy and policy.salary_day else 1
        today = fields.Date.today()
        if today.day != salary_day:
            return True

        # Latest completed cycle end is 25th of previous month (for salary day on 1st).
        prev_month_last = today.replace(day=1) - timedelta(days=1)
        cycle_end = prev_month_last.replace(day=25)
        cycle_start_month_last = cycle_end.replace(day=1) - timedelta(days=1)
        cycle_start = cycle_start_month_last.replace(day=26)

        contract_domain = [
            ("state", "=", "open"),
            ("date_start", "<=", cycle_end),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", cycle_start),
        ]
        contracts = self.env["hr.contract"].sudo().search(contract_domain)
        for contract in contracts:
            existing = self.search_count(
                [
                    ("employee_id", "=", contract.employee_id.id),
                    ("date_from", "=", cycle_start),
                    ("date_to", "=", cycle_end),
                ]
            )
            if existing:
                continue
            self.create(
                {
                    "name": _("Payslip %s (%s to %s)")
                    % (contract.employee_id.name, cycle_start, cycle_end),
                    "employee_id": contract.employee_id.id,
                    "contract_id": contract.id,
                    "struct_id": contract.struct_id.id if "struct_id" in contract._fields else False,
                    "date_from": cycle_start,
                    "date_to": cycle_end,
                }
            )
        return True
