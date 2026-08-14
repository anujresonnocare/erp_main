from datetime import date

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    res_payroll_day_basis = fields.Selection(
        [
            ("actual", "Actual Days In Cycle"),
            ("fixed_26", "Fixed 26 Days"),
            ("fixed_30", "Fixed 30 Days"),
        ],
        string="Payroll Day Basis",
        default="actual",
        required=True,
        help="Defines base days used for payable day / LOP salary calculations.",
    )
    res_tax_regime = fields.Selection(
        [("new", "New Regime"), ("old", "Old Regime")],
        string="Tax Regime",
        default="new",
    )
    res_tds_enabled = fields.Boolean(string="Enable TDS", default=True)
    res_rebate_87a_enabled = fields.Boolean(string="Apply Rebate 87A", default=True)
    res_cess_percent = fields.Float(string="Cess %", default=4.0)
    res_surcharge_percent = fields.Float(string="Surcharge %", default=0.0)
    res_standard_deduction = fields.Float(string="Standard Deduction", default=50000.0)
    res_declared_80c = fields.Float(string="Declared 80C")
    res_declared_80d = fields.Float(string="Declared 80D")
    res_other_deductions = fields.Float(string="Other Deductions")
    res_pf_applicable = fields.Boolean(string="PF Applicable", default=False)
    res_pf_employee_rate = fields.Float(string="PF Employee %", default=12.0)
    res_esic_applicable = fields.Boolean(string="ESIC Applicable", default=False)
    res_esic_employee_rate = fields.Float(string="ESIC Employee %", default=0.75)
    res_pt_applicable = fields.Boolean(string="Professional Tax Applicable", default=False)
    res_pt_monthly_amount = fields.Float(string="Professional Tax Monthly Amount", default=200.0)
    res_annual_projected_income = fields.Float(
        string="Annual Projected Income",
        compute="_compute_res_tax_projection",
        store=True,
    )
    res_annual_taxable_income = fields.Float(
        string="Annual Taxable Income",
        compute="_compute_res_tax_projection",
        store=True,
    )
    res_annual_tax_liability = fields.Float(
        string="Annual Tax Liability",
        compute="_compute_res_tax_projection",
        store=True,
    )
    res_remaining_fy_months = fields.Integer(
        string="Remaining FY Months",
        compute="_compute_res_tax_projection",
        store=True,
    )
    res_monthly_tds = fields.Float(
        string="Monthly TDS",
        compute="_compute_res_tax_projection",
        store=True,
    )

    @staticmethod
    def _res_fy_bounds(anchor):
        # FY in India: 1 Apr - 31 Mar
        if anchor.month >= 4:
            fy_start = date(anchor.year, 4, 1)
            fy_end = date(anchor.year + 1, 3, 31)
        else:
            fy_start = date(anchor.year - 1, 4, 1)
            fy_end = date(anchor.year, 3, 31)
        return fy_start, fy_end

    @staticmethod
    def _res_months_inclusive(start_month, end_month):
        if end_month >= start_month:
            return end_month - start_month + 1
        return (12 - start_month + 1) + end_month

    @staticmethod
    def _res_simple_tax(annual_taxable_income, regime="new", rebate_87a=True):
        # Slab-based projection (configurable old/new regime).
        taxable = max(annual_taxable_income, 0.0)
        tax = 0.0
        if regime == "old":
            if taxable > 250000:
                slab = min(taxable, 500000) - 250000
                tax += slab * 0.05
            if taxable > 500000:
                slab = min(taxable, 1000000) - 500000
                tax += slab * 0.20
            if taxable > 1000000:
                tax += (taxable - 1000000) * 0.30
            if rebate_87a and taxable <= 500000:
                tax = 0.0
        else:
            if taxable > 300000:
                slab = min(taxable, 700000) - 300000
                tax += slab * 0.05
            if taxable > 700000:
                slab = min(taxable, 1000000) - 700000
                tax += slab * 0.10
            if taxable > 1000000:
                slab = min(taxable, 1200000) - 1000000
                tax += slab * 0.15
            if taxable > 1200000:
                slab = min(taxable, 1500000) - 1200000
                tax += slab * 0.20
            if taxable > 1500000:
                tax += (taxable - 1500000) * 0.30
            if rebate_87a and taxable <= 700000:
                tax = 0.0
        return tax

    @api.depends(
        "wage",
        "res_tax_regime",
        "res_tds_enabled",
        "res_rebate_87a_enabled",
        "res_cess_percent",
        "res_surcharge_percent",
        "res_standard_deduction",
        "res_declared_80c",
        "res_declared_80d",
        "res_other_deductions",
    )
    def _compute_res_tax_projection(self):
        today = fields.Date.context_today(self)
        _, fy_end = self._res_fy_bounds(today)
        months_left = self._res_months_inclusive(today.month, fy_end.month)

        for contract in self:
            annual_income = (contract.wage or 0.0) * 12.0
            deduction_total = (
                (contract.res_standard_deduction or 0.0)
                + (contract.res_declared_80c or 0.0)
                + (contract.res_declared_80d or 0.0)
                + (contract.res_other_deductions or 0.0)
            )
            taxable = max(annual_income - deduction_total, 0.0)
            annual_tax = (
                self._res_simple_tax(
                    taxable,
                    regime=contract.res_tax_regime or "new",
                    rebate_87a=bool(contract.res_rebate_87a_enabled),
                )
                if contract.res_tds_enabled
                else 0.0
            )
            if annual_tax > 0 and (contract.res_surcharge_percent or 0.0) > 0:
                annual_tax += annual_tax * (contract.res_surcharge_percent / 100.0)
            if annual_tax > 0 and (contract.res_cess_percent or 0.0) > 0:
                annual_tax += annual_tax * (contract.res_cess_percent / 100.0)
            monthly_tds = annual_tax / months_left if months_left else 0.0

            contract.res_annual_projected_income = annual_income
            contract.res_annual_taxable_income = taxable
            contract.res_annual_tax_liability = annual_tax
            contract.res_remaining_fy_months = months_left
            contract.res_monthly_tds = monthly_tds
