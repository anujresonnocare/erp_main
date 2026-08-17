# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class CdtJourneyReport(models.Model):
    _name = "cdt.journey.report"
    _description = "CDT Journey Data Report"
    _order = "area_manager_name, is_total_row desc, clinic_name"
    _rec_name = "display_name"

    # ========================================
    # ALL YOUR EXISTING FIELD DEFINITIONS HERE
    # ========================================
    area_manager_id = fields.Many2one('res.users', string='Area Manager')
    clinic_id = fields.Many2one('resonnocare.clinic', string='Clinic', index=True)
    clinic_name = fields.Char(string='Clinic Name', related='clinic_id.name', store=True)
    clinic_code = fields.Char(string='Clinic Code', related='clinic_id.clinic_code', store=True)
    city = fields.Char(string='City', related='clinic_id.city', store=True)
    state = fields.Char(string='State', related='clinic_id.state_id.name', store=True)
    region = fields.Char(string='Region', related='clinic_id.region', store=True)
    area_manager_name = fields.Char(string='Area Manager', related='clinic_id.area_manager_id.name', store=True)
    clinic_type = fields.Selection([("h", "H"), ("sis", "SIS"), ("coco", "COCO")], string="Clinic Type", tracking=True, related='clinic_id.clinic_type')
    opening_date = fields.Date(string='Opening Date', related='clinic_id.go_live_date', store=True)
    is_total_row = fields.Boolean(string='Is Total Row', default=False)
    is_area_manager_total = fields.Boolean(string='Is Area Manager Total', default=False)
    is_region_total = fields.Boolean(string='Is Region Total', default=False)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    clinic_status = fields.Selection([("draft", "Draft"), ("active", "Active"), ("suspended", "Suspended")], string="Clinic Status", default="draft", tracking=True, related='clinic_id.clinic_status', store=True)
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    report_type = fields.Selection([('ytd', 'Year to Date'), ('mtd', 'Month to Date'), ('wtd', 'Week to Date'), ('yday', 'Yesterday'), ('custom', 'Custom Range')], string='Report Type', default='ytd')

    # ========================================
    # ALL METRIC FIELDS
    # ========================================
    total_appointments = fields.Integer(string='Total Appointments')
    ta_ext_dr_appointments = fields.Integer(string='TA - Ext. Dr.')
    ta_ext_dr_fup_appointments = fields.Integer(string='TA - Ext. Dr. FUP')
    ta_int_dr_appointments = fields.Integer(string='TA - Int. Dr.')
    ta_int_dr_fup_appointments = fields.Integer(string='TA - Int. Dr. FUP')
    ta_digital_marketing_appointments = fields.Integer(string='TA - Digital Marketing')
    ta_digital_marketing_fup_appointments = fields.Integer(string='TA - Digital Marketing FUP')
    ta_camp_doctor_appointments = fields.Integer(string='TA - Camp with Doctor')
    ta_camp_rwa_appointments = fields.Integer(string='TA - Camp with RWA')
    ta_outreach_appointments = fields.Integer(string='TA - OUTREACH')
    ta_renew_appointments = fields.Integer(string='TA - Renew')

    total_diagnostic_appointments = fields.Integer(string='Total Diagnostic Appointments')
    da_ext_dr_appointments = fields.Integer(string='DA - Ext. Dr.')
    da_ext_dr_fup_appointments = fields.Integer(string='DA - Ext. Dr. FUP')
    da_int_dr_appointments = fields.Integer(string='DA - Int. Dr.')
    da_int_dr_fup_appointments = fields.Integer(string='DA - Int. Dr. FUP')
    da_digital_marketing_appointments = fields.Integer(string='DA - Digital Marketing')
    da_digital_marketing_fup_appointments = fields.Integer(string='DA - Digital Marketing FUP')
    da_camp_doctor_appointments = fields.Integer(string='DA - Camp with Doctor')
    da_camp_rwa_appointments = fields.Integer(string='DA - Camp with RWA')
    da_outreach_appointments = fields.Integer(string='DA - OUTREACH')
    da_renew_appointments = fields.Integer(string='DA - Renew')

    hearing_test_booked = fields.Integer(string='Hearing Test Booked')
    htb_ext_dr_appointments = fields.Integer(string='HTB - Ext. Dr.')
    htb_ext_dr_fup_appointments = fields.Integer(string='HTB - Ext. Dr. FUP')
    htb_int_dr_appointments = fields.Integer(string='HTB - Int. Dr.')
    htb_int_dr_fup_appointments = fields.Integer(string='HTB - Int. Dr. FUP')
    htb_digital_marketing_appointments = fields.Integer(string='HTB - Digital Marketing')
    htb_digital_marketing_fup_appointments = fields.Integer(string='HTB - Digital Marketing FUP')
    htb_camp_doctor_appointments = fields.Integer(string='HTB - Camp with Doctor')
    htb_camp_rwa_appointments = fields.Integer(string='HTB - Camp with RWA')
    htb_outreach_appointments = fields.Integer(string='HTB - OUTREACH')
    htb_renew_appointments = fields.Integer(string='HTB - Renew')

    hearing_test_attended = fields.Integer(string='Hearing Test Attended')
    hta_ext_dr_appointments = fields.Integer(string='HTA - Ext. Dr.')
    hta_ext_dr_fup_appointments = fields.Integer(string='HTA - Ext. Dr. FUP')
    hta_int_dr_appointments = fields.Integer(string='HTA - Int. Dr.')
    hta_int_dr_fup_appointments = fields.Integer(string='HTA - Int. Dr. FUP')
    hta_digital_marketing_appointments = fields.Integer(string='HTA - Digital Marketing')
    hta_digital_marketing_fup_appointments = fields.Integer(string='HTA - Digital Marketing FUP')
    hta_camp_doctor_appointments = fields.Integer(string='HTA - Camp with Doctor')
    hta_camp_rwa_appointments = fields.Integer(string='HTA - Camp with RWA')
    hta_outreach_appointments = fields.Integer(string='HTA - OUTREACH')
    hta_renew_appointments = fields.Integer(string='HTA - Renew')

    net_attendance_percent = fields.Float(string='Net Attendance %', digits=(16, 2))
    nap_ext_dr_appointments = fields.Float(string='NAP - Ext. Dr.', digits=(16, 2))
    nap_ext_dr_fup_appointments = fields.Float(string='NAP - Ext. Dr. FUP', digits=(16, 2))
    nap_int_dr_appointments = fields.Float(string='NAP - Int. Dr.', digits=(16, 2))
    nap_int_dr_fup_appointments = fields.Float(string='NAP - Int. Dr. FUP', digits=(16, 2))
    nap_digital_marketing_appointments = fields.Float(string='NAP - Digital Marketing', digits=(16, 2))
    nap_digital_marketing_fup_appointments = fields.Float(string='NAP - Digital Marketing FUP', digits=(16, 2))
    nap_camp_doctor_appointments = fields.Float(string='NAP - Camp with Doctor', digits=(16, 2))
    nap_camp_rwa_appointments = fields.Float(string='NAP - Camp with RWA', digits=(16, 2))
    nap_outreach_appointments = fields.Float(string='NAP - OUTREACH', digits=(16, 2))
    nap_renew_appointments = fields.Float(string='NAP - Renew', digits=(16, 2))

    hearing_test_opportunity = fields.Integer(string='Hearing Test Opportunity')
    hto_ext_dr_appointments = fields.Integer(string='HTO - Ext. Dr.')
    hto_ext_dr_fup_appointments = fields.Integer(string='HTO - Ext. Dr. FUP')
    hto_int_dr_appointments = fields.Integer(string='HTO - Int. Dr.')
    hto_int_dr_fup_appointments = fields.Integer(string='HTO - Int. Dr. FUP')
    hto_digital_marketing_appointments = fields.Integer(string='HTO - Digital Marketing')
    hto_digital_marketing_fup_appointments = fields.Integer(string='HTO - Digital Marketing FUP')
    hto_camp_doctor_appointments = fields.Integer(string='HTO - Camp with Doctor')
    hto_camp_rwa_appointments = fields.Integer(string='HTO - Camp with RWA')
    hto_outreach_appointments = fields.Integer(string='HTO - OUTREACH')
    hto_renew_appointments = fields.Integer(string='HTO - Renew')

    hearing_test_opportunity_percentage = fields.Float(string='Hearing Test Opportunity %', digits=(16, 2))
    htop_ext_dr_appointments = fields.Float(string='HTOP - Ext. Dr.', digits=(16, 2))
    htop_ext_dr_fup_appointments = fields.Float(string='HTOP - Ext. Dr. FUP', digits=(16, 2))
    htop_int_dr_appointments = fields.Float(string='HTOP - Int. Dr.', digits=(16, 2))
    htop_int_dr_fup_appointments = fields.Float(string='HTOP - Int. Dr. FUP', digits=(16, 2))
    htop_digital_marketing_appointments = fields.Float(string='HTOP - Digital Marketing', digits=(16, 2))
    htop_digital_marketing_fup_appointments = fields.Float(string='HTOP - Digital Marketing FUP', digits=(16, 2))
    htop_camp_doctor_appointments = fields.Float(string='HTOP - Camp with Doctor', digits=(16, 2))
    htop_camp_rwa_appointments = fields.Float(string='HTOP - Camp with RWA', digits=(16, 2))
    htop_outreach_appointments = fields.Float(string='HTOP - OUTREACH', digits=(16, 2))
    htop_renew_appointments = fields.Float(string='HTOP - Renew', digits=(16, 2))

    conversions_prescriptions = fields.Integer(string='# Conversions')
    cp_ext_dr_appointments = fields.Integer(string='CP - Ext. Dr.')
    cp_ext_dr_fup_appointments = fields.Integer(string='CP - Ext. Dr. FUP')
    cp_int_dr_appointments = fields.Integer(string='CP - Int. Dr.')
    cp_int_dr_fup_appointments = fields.Integer(string='CP - Int. Dr. FUP')
    cp_digital_marketing_appointments = fields.Integer(string='CP - Digital Marketing')
    cp_digital_marketing_fup_appointments = fields.Integer(string='CP - Digital Marketing FUP')
    cp_camp_doctor_appointments = fields.Integer(string='CP - Camp with Doctor')
    cp_camp_rwa_appointments = fields.Integer(string='CP - Camp with RWA')
    cp_outreach_appointments = fields.Integer(string='CP - OUTREACH')
    cp_renew_appointments = fields.Integer(string='CP - Renew')

    conversion_rate_percent = fields.Float(string='Conversion Rate %', digits=(16, 2))
    crp_ext_dr_appointments = fields.Float(string='CRP - Ext. Dr.', digits=(16, 2))
    crp_ext_dr_fup_appointments = fields.Float(string='CRP - Ext. Dr. FUP', digits=(16, 2))
    crp_int_dr_appointments = fields.Float(string='CRP - Int. Dr.', digits=(16, 2))
    crp_int_dr_fup_appointments = fields.Float(string='CRP - Int. Dr. FUP', digits=(16, 2))
    crp_digital_marketing_appointments = fields.Float(string='CRP - Digital Marketing', digits=(16, 2))
    crp_digital_marketing_fup_appointments = fields.Float(string='CRP - Digital Marketing FUP', digits=(16, 2))
    crp_camp_doctor_appointments = fields.Float(string='CRP - Camp with Doctor', digits=(16, 2))
    crp_camp_rwa_appointments = fields.Float(string='CRP - Camp with RWA', digits=(16, 2))
    crp_outreach_appointments = fields.Float(string='CRP - OUTREACH', digits=(16, 2))
    crp_renew_appointments = fields.Float(string='CRP - Renew', digits=(16, 2))

    binaural = fields.Integer(string='Binaural')
    bin_ext_dr_appointments = fields.Integer(string='BIN - Ext. Dr.')
    bin_ext_dr_fup_appointments = fields.Integer(string='BIN - Ext. Dr. FUP')
    bin_int_dr_appointments = fields.Integer(string='BIN - Int. Dr.')
    bin_int_dr_fup_appointments = fields.Integer(string='BIN - Int. Dr. FUP')
    bin_digital_marketing_appointments = fields.Integer(string='BIN - Digital Marketing')
    bin_digital_marketing_fup_appointments = fields.Integer(string='BIN - Digital Marketing FUP')
    bin_camp_doctor_appointments = fields.Integer(string='BIN - Camp with Doctor')
    bin_camp_rwa_appointments = fields.Integer(string='BIN - Camp with RWA')
    bin_outreach_appointments = fields.Integer(string='BIN - OUTREACH')
    bin_renew_appointments = fields.Integer(string='BIN - Renew')

    binaural_rate_percentage = fields.Float(string='Binaural Rate %', digits=(16, 2))
    brp_ext_dr_appointments = fields.Float(string='BRP - Ext. Dr.', digits=(16, 2))
    brp_ext_dr_fup_appointments = fields.Float(string='BRP - Ext. Dr. FUP', digits=(16, 2))
    brp_int_dr_appointments = fields.Float(string='BRP - Int. Dr.', digits=(16, 2))
    brp_int_dr_fup_appointments = fields.Float(string='BRP - Int. Dr. FUP', digits=(16, 2))
    brp_digital_marketing_appointments = fields.Float(string='BRP - Digital Marketing', digits=(16, 2))
    brp_digital_marketing_fup_appointments = fields.Float(string='BRP - Digital Marketing FUP', digits=(16, 2))
    brp_camp_doctor_appointments = fields.Float(string='BRP - Camp with Doctor', digits=(16, 2))
    brp_camp_rwa_appointments = fields.Float(string='BRP - Camp with RWA', digits=(16, 2))
    brp_outreach_appointments = fields.Float(string='BRP - OUTREACH', digits=(16, 2))
    brp_renew_appointments = fields.Float(string='BRP - Renew', digits=(16, 2))

    hearing_unit = fields.Integer(string='Hearing Aid Units')
    ha_ext_dr_appointments = fields.Integer(string='HA - Ext. Dr.')
    ha_ext_dr_fup_appointments = fields.Integer(string='HA - Ext. Dr. FUP')
    ha_int_dr_appointments = fields.Integer(string='HA - Int. Dr.')
    ha_int_dr_fup_appointments = fields.Integer(string='HA - Int. Dr. FUP')
    ha_digital_marketing_appointments = fields.Integer(string='HA - Digital Marketing')
    ha_digital_marketing_fup_appointments = fields.Integer(string='HA - Digital Marketing FUP')
    ha_camp_doctor_appointments = fields.Integer(string='HA - Camp with Doctor')
    ha_camp_rwa_appointments = fields.Integer(string='HA - Camp with RWA')
    ha_outreach_appointments = fields.Integer(string='HA - OUTREACH')
    ha_renew_appointments = fields.Integer(string='HA - Renew')

    average_selling_price = fields.Float(string='Average Selling Price', digits=(16, 2))
    asp_ext_dr_appointments = fields.Float(string='ASP - Ext. Dr.', digits=(16, 2))
    asp_ext_dr_fup_appointments = fields.Float(string='ASP - Ext. Dr. FUP', digits=(16, 2))
    asp_int_dr_appointments = fields.Float(string='ASP - Int. Dr.', digits=(16, 2))
    asp_int_dr_fup_appointments = fields.Float(string='ASP - Int. Dr. FUP', digits=(16, 2))
    asp_digital_marketing_appointments = fields.Float(string='ASP - Digital Marketing', digits=(16, 2))
    asp_digital_marketing_fup_appointments = fields.Float(string='ASP - Digital Marketing FUP', digits=(16, 2))
    asp_camp_doctor_appointments = fields.Float(string='ASP - Camp with Doctor', digits=(16, 2))
    asp_camp_rwa_appointments = fields.Float(string='ASP - Camp with RWA', digits=(16, 2))
    asp_outreach_appointments = fields.Float(string='ASP - OUTREACH', digits=(16, 2))
    asp_renew_appointments = fields.Float(string='ASP - Renew', digits=(16, 2))

    gross_revenue = fields.Float(string='Gross Revenue', digits=(16, 2))
    gr_ext_dr_appointments = fields.Float(string='GR - Ext. Dr.', digits=(16, 2))
    gr_ext_dr_fup_appointments = fields.Float(string='GR - Ext. Dr. FUP', digits=(16, 2))
    gr_int_dr_appointments = fields.Float(string='GR - Int. Dr.', digits=(16, 2))
    gr_int_dr_fup_appointments = fields.Float(string='GR - Int. Dr. FUP', digits=(16, 2))
    gr_digital_marketing_appointments = fields.Float(string='GR - Digital Marketing', digits=(16, 2))
    gr_digital_marketing_fup_appointments = fields.Float(string='GR - Digital Marketing FUP', digits=(16, 2))
    gr_camp_doctor_appointments = fields.Float(string='GR - Camp with Doctor', digits=(16, 2))
    gr_camp_rwa_appointments = fields.Float(string='GR - Camp with RWA', digits=(16, 2))
    gr_outreach_appointments = fields.Float(string='GR - OUTREACH', digits=(16, 2))
    gr_renew_appointments = fields.Float(string='GR - Renew', digits=(16, 2))

    fitting_revenue = fields.Float(string='Fitting Revenue', digits=(16, 2))
    fitting_ext_dr_appointments = fields.Float(string='FR - Ext. Dr.', digits=(16, 2))
    fitting_ext_dr_fup_appointments = fields.Float(string='FR - Ext. Dr. FUP', digits=(16, 2))
    fitting_int_dr_appointments = fields.Float(string='FR - Int. Dr.', digits=(16, 2))
    fitting_int_dr_fup_appointments = fields.Float(string='FR - Int. Dr. FUP', digits=(16, 2))
    fitting_digital_marketing_appointments = fields.Float(string='FR - Digital Marketing', digits=(16, 2))
    fitting_digital_marketing_fup_appointments = fields.Float(string='FR - Digital Marketing FUP', digits=(16, 2))
    fitting_camp_doctor_appointments = fields.Float(string='FR - Camp with Doctor', digits=(16, 2))
    fitting_camp_rwa_appointments = fields.Float(string='FR - Camp with RWA', digits=(16, 2))
    fitting_outreach_appointments = fields.Float(string='FR - OUTREACH', digits=(16, 2))
    fitting_renew_appointments = fields.Float(string='FR - Renew', digits=(16, 2))

    @api.depends('clinic_name', 'area_manager_name', 'is_area_manager_total', 'is_region_total')
    def _compute_display_name(self):
        for record in self:
            if record.is_region_total:
                record.display_name = f"{record.region} Total"
            elif record.is_area_manager_total:
                record.display_name = f"{record.area_manager_name} Total"
            else:
                record.display_name = record.clinic_name or ''

    # ========================================
    # PERCENTAGE CALCULATIONS WITH SAFETY CHECKS
    # ========================================

    def _calculate_percentage(self, numerator, denominator):
        """Safe percentage calculation that never exceeds 100%"""
        if denominator and denominator > 0:
            # Ensure numerator doesn't exceed denominator
            if numerator > denominator:
                numerator = denominator
            return (numerator / denominator) * 100
        return 0.0

    def _calculate_derived_percentages(self, vals):
        """
        Calculate derived percentage fields using correct formulas with safety checks:
        
        1. Net Attendance % = (Hearing Test Attended / Hearing Test Booked) * 100
        2. Hearing Test Opportunity % (HL %) = (Hearing Test Opportunity / Hearing Test Attended) * 100
        3. Conversion Rate % = (# Conversions / Hearing Test Opportunity) * 100
        4. Binaural Rate % = (Binaural / # Conversions) * 100
        """
        
        # 1. NET ATTENDANCE %
        hearing_test_booked = vals.get('hearing_test_booked', 0)
        hearing_test_attended = vals.get('hearing_test_attended', 0)
        print(f"Calculating Net Attendance %: Attended={hearing_test_attended}, Booked={hearing_test_booked}")
        
        vals['net_attendance_percent'] = self._calculate_percentage(hearing_test_attended, hearing_test_booked)
        if hearing_test_booked > 0:
            print("net_attendance_percent@@@@@@@@@@@@@@@@@@@@@",vals['net_attendance_percent'])
        
        # 2. HEARING TEST OPPORTUNITY % (HL %)
        hearing_test_opportunity = vals.get('hearing_test_opportunity', 0)
        vals['hearing_test_opportunity_percentage'] = self._calculate_percentage(hearing_test_opportunity, hearing_test_attended)
        
        # 3. CONVERSION RATE %
        conversions_prescriptions = vals.get('conversions_prescriptions', 0)
        vals['conversion_rate_percent'] = self._calculate_percentage(conversions_prescriptions, hearing_test_opportunity)
        
        # 4. BINAURAL RATE %
        binaural = vals.get('binaural', 0)
        vals['binaural_rate_percentage'] = self._calculate_percentage(binaural, conversions_prescriptions)
        
        # 5. AVERAGE SELLING PRICE
        hearing_unit = vals.get('hearing_unit', 0)
        gross_revenue = vals.get('gross_revenue', 0)
        if hearing_unit > 0:
            vals['average_selling_price'] = gross_revenue / hearing_unit
        else:
            vals['average_selling_price'] = 0.0

    def _calculate_source_wise_percentages(self, vals, source_key):
        """
        Calculate source-wise percentages with safety checks
        
        Source keys: ext_dr, ext_dr_fup, int_dr, int_dr_fup, digital_marketing, 
                    digital_marketing_fup, camp_doctor, camp_rwa, outreach, renew
        
        Formulas:
        1. NAP - Source = (HTA - Source / HTB - Source) * 100
        2. HTOP - Source = (HTO - Source / HTA - Source) * 100
        3. CRP - Source = (CP - Source / HTO - Source) * 100
        4. BRP - Source = (BIN - Source / CP - Source) * 100
        """
        
        # Get source-wise values
        htb_key = f'htb_{source_key}_appointments'      # Hearing Test Booked
        hta_key = f'hta_{source_key}_appointments'      # Hearing Test Attended
        hto_key = f'hto_{source_key}_appointments'      # Hearing Test Opportunity
        cp_key = f'cp_{source_key}_appointments'        # Conversions
        bin_key = f'bin_{source_key}_appointments'      # Binaural
        
        htb = vals.get(htb_key, 0)
        hta = vals.get(hta_key, 0)
        hto = vals.get(hto_key, 0)
        cp = vals.get(cp_key, 0)
        bin_val = vals.get(bin_key, 0)
        
        # 1. NET ATTENDANCE % for Source
        vals[f'nap_{source_key}_appointments'] = self._calculate_percentage(hta, htb)
        
        # 2. HEARING TEST OPPORTUNITY % for Source
        vals[f'htop_{source_key}_appointments'] = self._calculate_percentage(hto, hta)
        
        # 3. CONVERSION RATE % for Source
        vals[f'crp_{source_key}_appointments'] = self._calculate_percentage(cp, hto)
        
        # 4. BINAURAL RATE % for Source
        vals[f'brp_{source_key}_appointments'] = self._calculate_percentage(bin_val, cp)

    # ========================================
    # GENERATE REPORT METHODS
    # ========================================
    
    def generate_report(self):
        """Generate and store report data - Called from form view button"""
        self.ensure_one()
        
        date_from = self.date_from
        date_to = self.date_to
        report_type = self.report_type or 'ytd'
        
        if not date_from or not date_to:
            today = fields.Date.today()
            if report_type == 'ytd':
                date_from = date(today.year, 1, 1)
                date_to = today
            elif report_type == 'mtd':
                date_from = date(today.year, today.month, 1)
                date_to = today
            elif report_type == 'wtd':
                monday = today - relativedelta(days=today.weekday())
                date_from = monday
                date_to = today
            elif report_type == 'yday':
                yesterday = today - relativedelta(days=1)
                date_from = yesterday
                date_to = yesterday
            else:
                raise ValidationError(_("Invalid report type"))
        
        return self._generate_report_data(date_from, date_to, report_type)

    def _generate_report_data(self, date_from, date_to, report_type):
        """Internal method to generate report data for given date range"""
        
        existing = self.search([
            ('date_from', '=', date_from),
            ('date_to', '=', date_to),
            ('report_type', '=', report_type)
        ])
        existing.unlink()
        
        clinics = self.env['resonnocare.clinic'].search([
            ('clinic_status', 'in', ['active', 'suspended'])
        ])
        
        if not clinics:
            self._create_sample_data(date_from, date_to, report_type)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        
        report_records = []
        
        # Process each clinic
        for clinic in clinics:
            vals = self._compute_clinic_metrics(clinic, date_from, date_to)
            vals.update({
                'clinic_id': clinic.id,
                'date_from': date_from,
                'date_to': date_to,
                'report_type': report_type,
                'area_manager_name': clinic.area_manager_id.name or '',
                'region': clinic.region or '',
                'is_total_row': False,
                'is_area_manager_total': False,
                'is_region_total': False,
            })
            report_records.append(vals)
        
        # Area Manager Totals
        area_managers = clinics.mapped('area_manager_id')
        for am in area_managers:
            if not am:
                continue
            am_clinics = clinics.filtered(lambda c: c.area_manager_id.id == am.id)
            if not am_clinics:
                continue
                
            am_vals = self._compute_aggregated_metrics(am_clinics, date_from, date_to)
            am_vals.update({
                'area_manager_id': am.id,
                'area_manager_name': am.name,
                'region': am_clinics.mapped('region')[0] if am_clinics.mapped('region') else '',
                'date_from': date_from,
                'date_to': date_to,
                'report_type': report_type,
                'is_total_row': True,
                'is_area_manager_total': True,
                'is_region_total': False,
                'clinic_id': False,
            })
            report_records.append(am_vals)
        
        # Region Totals
        regions = clinics.mapped('region')
        for region in regions:
            if not region:
                continue
            region_clinics = clinics.filtered(lambda c: c.region == region)
            if not region_clinics:
                continue
                
            region_vals = self._compute_aggregated_metrics(region_clinics, date_from, date_to)
            region_vals.update({
                'region': region,
                'date_from': date_from,
                'date_to': date_to,
                'report_type': report_type,
                'is_total_row': True,
                'is_area_manager_total': False,
                'is_region_total': True,
                'clinic_id': False,
                'area_manager_id': False,
                'area_manager_name': '',
            })
            report_records.append(region_vals)
        
        if report_records:
            self.create(report_records)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _compute_aggregated_metrics(self, clinics, date_from, date_to):
        """Compute aggregated metrics for a group of clinics"""
        aggregated = {}
        numeric_fields = self._get_numeric_fields()
        
        for clinic in clinics:
            vals = self._compute_clinic_metrics(clinic, date_from, date_to)
            for key, value in vals.items():
                if key in numeric_fields and value is not None:
                    aggregated[key] = aggregated.get(key, 0) + value
        
        # Calculate derived percentages for aggregated data
        self._calculate_derived_percentages(aggregated)
        
        # Calculate source-wise percentages
        source_keys = ['ext_dr', 'ext_dr_fup', 'int_dr', 'int_dr_fup', 
                      'digital_marketing', 'digital_marketing_fup', 
                      'camp_doctor', 'camp_rwa', 'outreach', 'renew']
        for source_key in source_keys:
            self._calculate_source_wise_percentages(aggregated, source_key)
        
        return aggregated

    def _get_numeric_fields(self):
        """Get list of all numeric field names"""
        numeric_fields = []
        for field_name, field in self._fields.items():
            if field.type in ['integer', 'float', 'monetary']:
                numeric_fields.append(field_name)
        return numeric_fields

    # ========================================
    # CLINIC METRICS COMPUTATION
    # ========================================

    def _compute_clinic_metrics(self, clinic, date_from, date_to):
        """Compute all metrics for a single clinic"""
        Appointment = self.env['resonnocare.appointment']
        
        vals = {}
        
        # Base domain - all valid appointments
        base_domain = [
            ('clinic_id', '=', clinic.id),
            ('appointment_date', '>=', date_from),
            ('appointment_date', '<=', date_to),
            ('status', 'not in', ['cancelled', 'no_show'])
        ]
        
        appointments = Appointment.search(base_domain)
        total = len(appointments)
        
        def classify_appointment(appt):
            """Classify an appointment by source and follow-up status"""
            is_followup = bool(appt.parent_appointment_id)
            referral_source = appt.patient_id.referral_source if appt.patient_id else False
            
            if referral_source == 'doctor':
                return 'ext_dr', is_followup
            elif appt.audiologist_id:
                return 'int_dr', is_followup
            elif referral_source == 'marketing':
                return 'digital_marketing', is_followup
            elif appt.source == 'crm' and referral_source == 'doctor':
                return 'camp_doctor', False
            elif appt.source == 'crm' and referral_source != 'doctor':
                return 'camp_rwa', False
            elif appt.source == 'crm':
                return 'outreach', False
            elif self._is_renew_patient(appt, clinic, date_from):
                return 'renew', False
            else:
                return 'other', False
        
        # Initialize field groups
        ta_fields = {
            'ext_dr': 0, 'ext_dr_fup': 0,
            'int_dr': 0, 'int_dr_fup': 0,
            'digital_marketing': 0, 'digital_marketing_fup': 0,
            'camp_doctor': 0, 'camp_rwa': 0,
            'outreach': 0, 'renew': 0,
        }
        
        # ========================================
        # TOTAL APPOINTMENTS (TA)
        # ========================================
        vals['total_appointments'] = total
        
        for appt in appointments:
            source, is_fup = classify_appointment(appt)
            if source != 'other':
                key = f"{source}_fup" if is_fup and source in ['ext_dr', 'int_dr', 'digital_marketing'] else source
                if key in ta_fields:
                    ta_fields[key] += 1
        
        vals['ta_ext_dr_appointments'] = ta_fields['ext_dr']
        vals['ta_ext_dr_fup_appointments'] = ta_fields['ext_dr_fup']
        vals['ta_int_dr_appointments'] = ta_fields['int_dr']
        vals['ta_int_dr_fup_appointments'] = ta_fields['int_dr_fup']
        vals['ta_digital_marketing_appointments'] = ta_fields['digital_marketing']
        vals['ta_digital_marketing_fup_appointments'] = ta_fields['digital_marketing_fup']
        vals['ta_camp_doctor_appointments'] = ta_fields['camp_doctor']
        vals['ta_camp_rwa_appointments'] = ta_fields['camp_rwa']
        vals['ta_outreach_appointments'] = ta_fields['outreach']
        vals['ta_renew_appointments'] = ta_fields['renew']
        
        # ========================================
        # DIAGNOSTIC APPOINTMENTS (DA)
        # ========================================
        diagnostic_appointments = [a for a in appointments if a.diagnostic_item_ids and a.sale_type == 'service']
        vals['total_diagnostic_appointments'] = len(diagnostic_appointments)
        
        da_fields = {k: 0 for k in ta_fields.keys()}
        for appt in diagnostic_appointments:
            source, is_fup = classify_appointment(appt)
            if source != 'other':
                key = f"{source}_fup" if is_fup and source in ['ext_dr', 'int_dr', 'digital_marketing'] else source
                if key in da_fields:
                    da_fields[key] += 1
        
        vals['da_ext_dr_appointments'] = da_fields['ext_dr']
        vals['da_ext_dr_fup_appointments'] = da_fields['ext_dr_fup']
        vals['da_int_dr_appointments'] = da_fields['int_dr']
        vals['da_int_dr_fup_appointments'] = da_fields['int_dr_fup']
        vals['da_digital_marketing_appointments'] = da_fields['digital_marketing']
        vals['da_digital_marketing_fup_appointments'] = da_fields['digital_marketing_fup']
        vals['da_camp_doctor_appointments'] = da_fields['camp_doctor']
        vals['da_camp_rwa_appointments'] = da_fields['camp_rwa']
        vals['da_outreach_appointments'] = da_fields['outreach']
        vals['da_renew_appointments'] = da_fields['renew']
        
        # ========================================
        # HEARING TEST BOOKED (HTB)
        # ========================================
        hearing_tests = [a for a in appointments if a.appointment_type_id and 
                        ('hearing test' in a.appointment_type_id.name.lower() or 
                         'trial' in a.appointment_type_id.name.lower())]
        vals['hearing_test_booked'] = len(hearing_tests)
        
        htb_fields = {k: 0 for k in ta_fields.keys()}
        for appt in hearing_tests:
            source, is_fup = classify_appointment(appt)
            if source != 'other':
                key = f"{source}_fup" if is_fup and source in ['ext_dr', 'int_dr', 'digital_marketing'] else source
                if key in htb_fields:
                    htb_fields[key] += 1
        
        vals['htb_ext_dr_appointments'] = htb_fields['ext_dr']
        vals['htb_ext_dr_fup_appointments'] = htb_fields['ext_dr_fup']
        vals['htb_int_dr_appointments'] = htb_fields['int_dr']
        vals['htb_int_dr_fup_appointments'] = htb_fields['int_dr_fup']
        vals['htb_digital_marketing_appointments'] = htb_fields['digital_marketing']
        vals['htb_digital_marketing_fup_appointments'] = htb_fields['digital_marketing_fup']
        vals['htb_camp_doctor_appointments'] = htb_fields['camp_doctor']
        vals['htb_camp_rwa_appointments'] = htb_fields['camp_rwa']
        vals['htb_outreach_appointments'] = htb_fields['outreach']
        vals['htb_renew_appointments'] = htb_fields['renew']
        
        # ========================================
        # HEARING TEST ATTENDED (HTA)
        # ========================================
        hearing_tests_attended = [a for a in hearing_tests if a.status == 'completed']
        vals['hearing_test_attended'] = len(hearing_tests_attended)
        
        hta_fields = {k: 0 for k in ta_fields.keys()}
        for appt in hearing_tests_attended:
            source, is_fup = classify_appointment(appt)
            if source != 'other':
                key = f"{source}_fup" if is_fup and source in ['ext_dr', 'int_dr', 'digital_marketing'] else source
                if key in hta_fields:
                    hta_fields[key] += 1
        
        vals['hta_ext_dr_appointments'] = hta_fields['ext_dr']
        vals['hta_ext_dr_fup_appointments'] = hta_fields['ext_dr_fup']
        vals['hta_int_dr_appointments'] = hta_fields['int_dr']
        vals['hta_int_dr_fup_appointments'] = hta_fields['int_dr_fup']
        vals['hta_digital_marketing_appointments'] = hta_fields['digital_marketing']
        vals['hta_digital_marketing_fup_appointments'] = hta_fields['digital_marketing_fup']
        vals['hta_camp_doctor_appointments'] = hta_fields['camp_doctor']
        vals['hta_camp_rwa_appointments'] = hta_fields['camp_rwa']
        vals['hta_outreach_appointments'] = hta_fields['outreach']
        vals['hta_renew_appointments'] = hta_fields['renew']
        
        # ========================================
        # HEARING TEST OPPORTUNITY (HTO)
        # ========================================
        # Hearing Loss Detection = Completed appointments with device sales
        hearing_loss = [a for a in appointments if a.status == 'completed' and a.device_sale_line_ids]
        vals['hearing_test_opportunity'] = len(hearing_loss)
        
        hto_fields = {k: 0 for k in ta_fields.keys()}
        for appt in hearing_loss:
            source, is_fup = classify_appointment(appt)
            if source != 'other':
                key = f"{source}_fup" if is_fup and source in ['ext_dr', 'int_dr', 'digital_marketing'] else source
                if key in hto_fields:
                    hto_fields[key] += 1
        
        vals['hto_ext_dr_appointments'] = hto_fields['ext_dr']
        vals['hto_ext_dr_fup_appointments'] = hto_fields['ext_dr_fup']
        vals['hto_int_dr_appointments'] = hto_fields['int_dr']
        vals['hto_int_dr_fup_appointments'] = hto_fields['int_dr_fup']
        vals['hto_digital_marketing_appointments'] = hto_fields['digital_marketing']
        vals['hto_digital_marketing_fup_appointments'] = hto_fields['digital_marketing_fup']
        vals['hto_camp_doctor_appointments'] = hto_fields['camp_doctor']
        vals['hto_camp_rwa_appointments'] = hto_fields['camp_rwa']
        vals['hto_outreach_appointments'] = hto_fields['outreach']
        vals['hto_renew_appointments'] = hto_fields['renew']
        
        # ========================================
        # CONVERSIONS (Prescriptions)
        # ========================================
        conversions = [a for a in appointments if a.status == 'completed' and 
                      a.sale_type == 'device' and a.device_sale_line_ids]
        vals['conversions_prescriptions'] = len(conversions)
        
        cp_fields = {k: 0 for k in ta_fields.keys()}
        for appt in conversions:
            source, is_fup = classify_appointment(appt)
            if source != 'other':
                key = f"{source}_fup" if is_fup and source in ['ext_dr', 'int_dr', 'digital_marketing'] else source
                if key in cp_fields:
                    cp_fields[key] += 1
        
        vals['cp_ext_dr_appointments'] = cp_fields['ext_dr']
        vals['cp_ext_dr_fup_appointments'] = cp_fields['ext_dr_fup']
        vals['cp_int_dr_appointments'] = cp_fields['int_dr']
        vals['cp_int_dr_fup_appointments'] = cp_fields['int_dr_fup']
        vals['cp_digital_marketing_appointments'] = cp_fields['digital_marketing']
        vals['cp_digital_marketing_fup_appointments'] = cp_fields['digital_marketing_fup']
        vals['cp_camp_doctor_appointments'] = cp_fields['camp_doctor']
        vals['cp_camp_rwa_appointments'] = cp_fields['camp_rwa']
        vals['cp_outreach_appointments'] = cp_fields['outreach']
        vals['cp_renew_appointments'] = cp_fields['renew']
        
        # ========================================
        # BINAURAL
        # ========================================
        # Note: You'll need a field on appointment/device to mark binaural
        # For now, setting to 0 as placeholder
        vals['binaural'] = 0
        bin_fields = {k: 0 for k in ta_fields.keys()}
        for key in bin_fields:
            vals[f'bin_{key}_appointments'] = 0
        
        # ========================================
        # HA UNITS & REVENUE
        # ========================================
        ha_units = 0
        gross_revenue = 0.0
        fitting_revenue = 0.0
        
        ha_fields = {k: 0 for k in ta_fields.keys()}
        gr_fields = {k: 0 for k in ta_fields.keys()}
        fr_fields = {k: 0 for k in ta_fields.keys()}
        
        for appt in conversions:
            source, is_fup = classify_appointment(appt)
            source_key = f"{source}_fup" if is_fup and source in ['ext_dr', 'int_dr', 'digital_marketing'] else source
            
            for line in appt.device_sale_line_ids:
                qty = line.product_uom_qty or 0
                price = line.product_id.lst_price or 0
                ha_units += qty
                revenue = price * qty
                gross_revenue += revenue
                fitting_revenue += revenue * 0.8
                
                if source_key in ha_fields:
                    ha_fields[source_key] += qty
                    gr_fields[source_key] += revenue
                    fr_fields[source_key] += revenue * 0.8
        
        vals['hearing_unit'] = ha_units
        vals['gross_revenue'] = gross_revenue
        vals['fitting_revenue'] = fitting_revenue
        
        # Map HA fields
        vals['ha_ext_dr_appointments'] = ha_fields['ext_dr']
        vals['ha_ext_dr_fup_appointments'] = ha_fields['ext_dr_fup']
        vals['ha_int_dr_appointments'] = ha_fields['int_dr']
        vals['ha_int_dr_fup_appointments'] = ha_fields['int_dr_fup']
        vals['ha_digital_marketing_appointments'] = ha_fields['digital_marketing']
        vals['ha_digital_marketing_fup_appointments'] = ha_fields['digital_marketing_fup']
        vals['ha_camp_doctor_appointments'] = ha_fields['camp_doctor']
        vals['ha_camp_rwa_appointments'] = ha_fields['camp_rwa']
        vals['ha_outreach_appointments'] = ha_fields['outreach']
        vals['ha_renew_appointments'] = ha_fields['renew']
        
        # Map GR fields
        vals['gr_ext_dr_appointments'] = gr_fields['ext_dr']
        vals['gr_ext_dr_fup_appointments'] = gr_fields['ext_dr_fup']
        vals['gr_int_dr_appointments'] = gr_fields['int_dr']
        vals['gr_int_dr_fup_appointments'] = gr_fields['int_dr_fup']
        vals['gr_digital_marketing_appointments'] = gr_fields['digital_marketing']
        vals['gr_digital_marketing_fup_appointments'] = gr_fields['digital_marketing_fup']
        vals['gr_camp_doctor_appointments'] = gr_fields['camp_doctor']
        vals['gr_camp_rwa_appointments'] = gr_fields['camp_rwa']
        vals['gr_outreach_appointments'] = gr_fields['outreach']
        vals['gr_renew_appointments'] = gr_fields['renew']
        
        # Map FR fields
        vals['fitting_ext_dr_appointments'] = fr_fields['ext_dr']
        vals['fitting_ext_dr_fup_appointments'] = fr_fields['ext_dr_fup']
        vals['fitting_int_dr_appointments'] = fr_fields['int_dr']
        vals['fitting_int_dr_fup_appointments'] = fr_fields['int_dr_fup']
        vals['fitting_digital_marketing_appointments'] = fr_fields['digital_marketing']
        vals['fitting_digital_marketing_fup_appointments'] = fr_fields['digital_marketing_fup']
        vals['fitting_camp_doctor_appointments'] = fr_fields['camp_doctor']
        vals['fitting_camp_rwa_appointments'] = fr_fields['camp_rwa']
        vals['fitting_outreach_appointments'] = fr_fields['outreach']
        vals['fitting_renew_appointments'] = fr_fields['renew']
        
        # Map ASP fields
        for key in ['ext_dr', 'ext_dr_fup', 'int_dr', 'int_dr_fup', 'digital_marketing', 
                    'digital_marketing_fup', 'camp_doctor', 'camp_rwa', 'outreach', 'renew']:
            ha_qty = ha_fields.get(key, 0)
            revenue = gr_fields.get(key, 0)
            vals[f'asp_{key}_appointments'] = (revenue / ha_qty) if ha_qty > 0 else 0.0
        
        # ========================================
        # CALCULATE PERCENTAGES WITH SAFETY CHECKS
        # ========================================
        
        # Calculate main percentages
        self._calculate_derived_percentages(vals)
        
        # Calculate source-wise percentages
        source_keys = ['ext_dr', 'ext_dr_fup', 'int_dr', 'int_dr_fup', 
                      'digital_marketing', 'digital_marketing_fup', 
                      'camp_doctor', 'camp_rwa', 'outreach', 'renew']
        for source_key in source_keys:
            self._calculate_source_wise_percentages(vals, source_key)
        
        return vals

    def _is_renew_patient(self, appointment, clinic, date_from):
        """Check if a patient has had previous appointments before date_from"""
        previous = self.env['resonnocare.appointment'].search([
            ('clinic_id', '=', clinic.id),
            ('patient_id', '=', appointment.patient_id.id),
            ('appointment_date', '<', date_from),
            ('status', 'not in', ['cancelled', 'no_show'])
        ], limit=1)
        return bool(previous)

    # ========================================
    # SEPARATE REPORT GENERATION METHODS
    # ========================================

    def generate_mtd_report(self):
        """Generate Month-to-Date report"""
        today = fields.Date.today()
        date_from = date(today.year, today.month, 1)
        date_to = today
        return self._generate_report_data(date_from, date_to, 'mtd')

    def generate_wtd_report(self):
        """Generate Week-to-Date report"""
        today = fields.Date.today()
        monday = today - relativedelta(days=today.weekday())
        date_from = monday
        date_to = today
        return self._generate_report_data(date_from, date_to, 'wtd')

    def generate_ytd_report(self):
        """Generate Year-to-Date report"""
        today = fields.Date.today()
        date_from = date(today.year, 1, 1)
        date_to = today
        return self._generate_report_data(date_from, date_to, 'ytd')

    def generate_yesterday_report(self):
        """Generate Yesterday's report"""
        today = fields.Date.today()
        yesterday = today - relativedelta(days=1)
        date_from = yesterday
        date_to = yesterday
        return self._generate_report_data(date_from, date_to, 'yday')

    def generate_all_reports(self):
        """Generate all report types at once"""
        today = fields.Date.today()
        
        ytd_from = date(today.year, 1, 1)
        self._generate_report_data(ytd_from, today, 'ytd')
        
        mtd_from = date(today.year, today.month, 1)
        self._generate_report_data(mtd_from, today, 'mtd')
        
        monday = today - relativedelta(days=today.weekday())
        self._generate_report_data(monday, today, 'wtd')
        
        yesterday = today - relativedelta(days=1)
        self._generate_report_data(yesterday, yesterday, 'yday')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # ========================================
    # SAMPLE DATA
    # ========================================

    def _create_sample_data(self, date_from, date_to, report_type):
        """Create sample data for testing"""
        demo_clinic = self.env['resonnocare.clinic'].search([], limit=1)
        if not demo_clinic:
            demo_clinic = self.env['resonnocare.clinic'].create({
                'name': 'Demo Clinic',
                'clinic_code': 'DEMO001',
                'clinic_type': 'sis',
                'clinic_status': 'active',
                'city': 'Demo City',
                'go_live_date': fields.Date.today(),
                'area_manager_id': self.env.ref('base.user_admin').id,
                'region': 'North',
            })
        
        sample_data = {
            'clinic_id': demo_clinic.id,
            'date_from': date_from,
            'date_to': date_to,
            'report_type': report_type,
            'area_manager_name': 'Demo Manager',
            'region': 'North',
            
            # TA
            'total_appointments': 100,
            'ta_ext_dr_appointments': 20,
            'ta_ext_dr_fup_appointments': 10,
            'ta_int_dr_appointments': 30,
            'ta_int_dr_fup_appointments': 15,
            'ta_digital_marketing_appointments': 10,
            'ta_digital_marketing_fup_appointments': 5,
            'ta_camp_doctor_appointments': 3,
            'ta_camp_rwa_appointments': 2,
            'ta_outreach_appointments': 5,
            'ta_renew_appointments': 0,
            
            # DA
            'total_diagnostic_appointments': 50,
            'da_ext_dr_appointments': 10,
            'da_ext_dr_fup_appointments': 5,
            'da_int_dr_appointments': 15,
            'da_int_dr_fup_appointments': 8,
            'da_digital_marketing_appointments': 5,
            'da_digital_marketing_fup_appointments': 3,
            'da_camp_doctor_appointments': 2,
            'da_camp_rwa_appointments': 1,
            'da_outreach_appointments': 1,
            'da_renew_appointments': 0,
            
            # HTB
            'hearing_test_booked': 40,
            'htb_ext_dr_appointments': 8,
            'htb_ext_dr_fup_appointments': 4,
            'htb_int_dr_appointments': 12,
            'htb_int_dr_fup_appointments': 6,
            'htb_digital_marketing_appointments': 4,
            'htb_digital_marketing_fup_appointments': 2,
            'htb_camp_doctor_appointments': 2,
            'htb_camp_rwa_appointments': 1,
            'htb_outreach_appointments': 1,
            'htb_renew_appointments': 0,
            
            # HTA
            'hearing_test_attended': 30,
            'hta_ext_dr_appointments': 6,
            'hta_ext_dr_fup_appointments': 3,
            'hta_int_dr_appointments': 9,
            'hta_int_dr_fup_appointments': 5,
            'hta_digital_marketing_appointments': 3,
            'hta_digital_marketing_fup_appointments': 2,
            'hta_camp_doctor_appointments': 1,
            'hta_camp_rwa_appointments': 1,
            'hta_outreach_appointments': 0,
            'hta_renew_appointments': 0,
            
            # HTO (Hearing Loss Detection)
            'hearing_test_opportunity': 25,
            'hto_ext_dr_appointments': 5,
            'hto_ext_dr_fup_appointments': 3,
            'hto_int_dr_appointments': 8,
            'hto_int_dr_fup_appointments': 4,
            'hto_digital_marketing_appointments': 2,
            'hto_digital_marketing_fup_appointments': 1,
            'hto_camp_doctor_appointments': 1,
            'hto_camp_rwa_appointments': 1,
            'hto_outreach_appointments': 0,
            'hto_renew_appointments': 0,
            
            # CP (Conversions/Prescriptions)
            'conversions_prescriptions': 15,
            'cp_ext_dr_appointments': 3,
            'cp_ext_dr_fup_appointments': 2,
            'cp_int_dr_appointments': 5,
            'cp_int_dr_fup_appointments': 3,
            'cp_digital_marketing_appointments': 1,
            'cp_digital_marketing_fup_appointments': 1,
            'cp_camp_doctor_appointments': 0,
            'cp_camp_rwa_appointments': 0,
            'cp_outreach_appointments': 0,
            'cp_renew_appointments': 0,
            
            # BIN
            'binaural': 10,
            'bin_ext_dr_appointments': 2,
            'bin_ext_dr_fup_appointments': 1,
            'bin_int_dr_appointments': 3,
            'bin_int_dr_fup_appointments': 2,
            'bin_digital_marketing_appointments': 1,
            'bin_digital_marketing_fup_appointments': 1,
            'bin_camp_doctor_appointments': 0,
            'bin_camp_rwa_appointments': 0,
            'bin_outreach_appointments': 0,
            'bin_renew_appointments': 0,
            
            # HA
            'hearing_unit': 25,
            'ha_ext_dr_appointments': 5,
            'ha_ext_dr_fup_appointments': 3,
            'ha_int_dr_appointments': 8,
            'ha_int_dr_fup_appointments': 5,
            'ha_digital_marketing_appointments': 2,
            'ha_digital_marketing_fup_appointments': 2,
            'ha_camp_doctor_appointments': 0,
            'ha_camp_rwa_appointments': 0,
            'ha_outreach_appointments': 0,
            'ha_renew_appointments': 0,
            
            # GR
            'gross_revenue': 875000.0,
            'gr_ext_dr_appointments': 175000.0,
            'gr_ext_dr_fup_appointments': 105000.0,
            'gr_int_dr_appointments': 280000.0,
            'gr_int_dr_fup_appointments': 175000.0,
            'gr_digital_marketing_appointments': 70000.0,
            'gr_digital_marketing_fup_appointments': 70000.0,
            'gr_camp_doctor_appointments': 0.0,
            'gr_camp_rwa_appointments': 0.0,
            'gr_outreach_appointments': 0.0,
            'gr_renew_appointments': 0.0,
            
            # FR
            'fitting_revenue': 700000.0,
            'fitting_ext_dr_appointments': 140000.0,
            'fitting_ext_dr_fup_appointments': 84000.0,
            'fitting_int_dr_appointments': 224000.0,
            'fitting_int_dr_fup_appointments': 140000.0,
            'fitting_digital_marketing_appointments': 56000.0,
            'fitting_digital_marketing_fup_appointments': 56000.0,
            'fitting_camp_doctor_appointments': 0.0,
            'fitting_camp_rwa_appointments': 0.0,
            'fitting_outreach_appointments': 0.0,
            'fitting_renew_appointments': 0.0,
        }
        
        # Calculate percentages for sample data with safety checks
        self._calculate_derived_percentages(sample_data)
        
        source_keys = ['ext_dr', 'ext_dr_fup', 'int_dr', 'int_dr_fup', 
                      'digital_marketing', 'digital_marketing_fup', 
                      'camp_doctor', 'camp_rwa', 'outreach', 'renew']
        for source_key in source_keys:
            self._calculate_source_wise_percentages(sample_data, source_key)
        
        self.create(sample_data)
        
        # Create AM total row
        am_total_data = sample_data.copy()
        am_total_data.update({
            'clinic_id': False,
            'is_total_row': True,
            'is_area_manager_total': True,
            'display_name': 'Demo Manager Total',
        })
        self.create(am_total_data)
        
        # Create Region total row
        region_total_data = sample_data.copy()
        region_total_data.update({
            'clinic_id': False,
            'is_total_row': True,
            'is_area_manager_total': False,
            'is_region_total': True,
            'display_name': 'North Total',
            'area_manager_name': '',
        })
        self.create(region_total_data)

    def action_refresh(self):
        """Refresh the report data"""
        self.ensure_one()
        return self.generate_report()