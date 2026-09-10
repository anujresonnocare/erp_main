# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
import io
import base64
import xlsxwriter
import logging

_logger = logging.getLogger(__name__)


class CdtJourneyReportWizard(models.TransientModel):
    _name = 'cdt.journey.report.wizard'
    _description = 'CDT Journey Report Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    report_type = fields.Selection([
        ('ytd', 'Year to Date'),
        ('mtd', 'Month to Date'),
        ('wtd', 'Week to Date'),
        ('yday', 'Yesterday'),
        ('custom', 'Custom Range')
    ], string='Report Type', default='ytd', required=True)
    area_manager_id = fields.Many2one('res.users', string='Area Manager')
    region = fields.Char(string='Region')
    clinic_ids = fields.Many2many('resonnocare.clinic', string='Clinics')
    file_name = fields.Char(string='File Name', default='CDT_Journey_Report')

    @api.onchange('report_type')
    def _onchange_report_type(self):
        today = fields.Date.today()
        if self.report_type == 'ytd':
            if today.month >= 4:
                self.date_from = date(today.year, 4, 1)
            else:
                self.date_from = date(today.year - 1, 4, 1)
            self.date_to = today
        elif self.report_type == 'mtd':
            self.date_from = date(today.year, today.month, 1)
            self.date_to = today
        elif self.report_type == 'wtd':
            monday = today - timedelta(days=today.weekday())
            self.date_from = monday
            self.date_to = today
        elif self.report_type == 'yday':
            yesterday = today - timedelta(days=1)
            self.date_from = yesterday
            self.date_to = yesterday
        else:
            self.date_from = False
            self.date_to = False

    def print_report(self):
        self.ensure_one()
        if not self.date_from or not self.date_to:
            raise ValidationError(_('Please select valid date range.'))
        if self.date_from > self.date_to:
            raise ValidationError(_('Date From cannot be greater than Date To.'))
        return self._generate_excel_report()

    # ========================================
    # DYNAMIC SOURCE HIERARCHY
    # ========================================
    def _get_source_hierarchy(self):
        """
        Build dynamic source hierarchy from custom.source records.
        Returns: [
            {
                'parent_code': 'DR',
                'parent_name': 'Doctor',
                'children': [
                    {'code': 'IN', 'name': 'Internal Doctor', 'key': 'in'},
                    {'code': 'EXT', 'name': 'External Doctor', 'key': 'ext'},
                    ...
                ]
            },
            ...
        ]
        """
        CustomSource = self.env['custom.source'].sudo()
        parents = CustomSource.search([('parent_id', '=', False), ('active', '=', True)], order='code')

        hierarchy = []
        for parent in parents:
            children = CustomSource.search([
                ('parent_id', '=', parent.id),
                ('active', '=', True)
            ], order='code')

            children_data = []
            for child in children:
                # Generate key from code (safe for dict keys)
                key = child.code.lower().replace(' ', '_').replace('.', '').replace('-', '_')
                children_data.append({
                    'id': child.id,
                    'code': child.code,
                    'name': child.name,
                    'key': key,
                    'is_doctor': child.is_doctor,
                    'is_market': child.is_market,
                    'is_outreach': child.is_outreach,
                })

            hierarchy.append({
                'parent_id': parent.id,
                'parent_code': parent.code,
                'parent_name': parent.name,
                'parent_is_doctor': parent.is_doctor,
                'parent_is_market': parent.is_market,
                'parent_is_outreach': parent.is_outreach,
                'children': children_data,
            })

        return hierarchy

    def _build_source_map(self, hierarchy):
        """
        Flatten hierarchy into a lookup dict:
        source_id -> child_key
        Also builds list of all child keys.
        """
        source_map = {}
        all_keys = []
        for parent in hierarchy:
            for child in parent['children']:
                source_map[child['id']] = child['key']
                all_keys.append(child['key'])
        return source_map, all_keys

    def _get_source_key_for_appointment(self, appointment, source_map):
        """Return the dynamic key for the appointment's ref_source"""
        if not appointment.ref_source:
            return None
        return source_map.get(appointment.ref_source.id)

    # ========================================
    # APPOINTMENT LOGIC
    # ========================================
    def _is_followup(self, appointment):
        if not appointment.patient_id or not appointment.appointment_date:
            return False
        previous = self.env['resonnocare.appointment'].search([
            ('patient_id', '=', appointment.patient_id.id),
            ('appointment_date', '<', appointment.appointment_date),
            ('appointment_date', '>=', appointment.appointment_date - timedelta(days=90)),
            ('id', '!=', appointment.id),
            ('status', 'not in', ['cancelled', 'no_show']),
        ], limit=1)
        return bool(previous)

    def _is_ha_product(self, product):
        if not product:
            return False
        item_type = False
        if hasattr(product, 'item_type'):
            item_type = product.item_type
        elif hasattr(product.product_tmpl_id, 'item_type'):
            item_type = product.product_tmpl_id.item_type
        return item_type == 'ha'

    def _get_clinics(self):
        domain = []
        if self.clinic_ids:
            domain.append(('id', 'in', self.clinic_ids.ids))
        if self.area_manager_id:
            domain.append(('area_manager_id', '=', self.area_manager_id.id))
        if self.region:
            domain.append(('region', '=', self.region))
        return self.env['resonnocare.clinic'].search(domain, order='region, area_manager_id, name')

    def _get_appointments(self, clinic):
        return self.env['resonnocare.appointment'].search([
            ('clinic_id', '=', clinic.id),
            ('appointment_date', '>=', self.date_from),
            ('appointment_date', '<=', self.date_to),
            ('status', 'not in', ['cancelled', 'no_show']),
        ])

    # ========================================
    # METRICS
    # ========================================
    METRIC_PREFIXES = ['ta', 'da', 'htb', 'hta', 'hto', 'cp', 'bin', 'ha', 'gr', 'fr']

    def _empty_metrics(self, all_keys):
        """Build empty metrics dict with dynamic keys"""
        m = {}
        # Overview (OVERALL) totals
        m['total_appointments'] = 0
        m['total_diagnostic_appointments'] = 0
        m['hearing_test_booked'] = 0
        m['hearing_test_attended'] = 0
        m['hearing_test_opportunity'] = 0
        m['conversions_prescriptions'] = 0
        m['binaural'] = 0
        m['hearing_unit'] = 0
        m['gross_revenue'] = 0.0
        m['fitting_revenue'] = 0.0
        m['net_attendance_percent'] = 0.0
        m['hearing_test_opportunity_percentage'] = 0.0
        m['conversion_rate_percent'] = 0.0
        m['binaural_rate_percentage'] = 0.0
        m['average_selling_price'] = 0.0

        # Per-source keys (dynamic)
        for prefix in self.METRIC_PREFIXES:
            for key in all_keys:
                m[f'{prefix}_{key}'] = 0 if prefix in ('ta', 'da', 'htb', 'hta', 'hto', 'cp', 'bin', 'ha') else 0.0

        # Per-source percentages
        for key in all_keys:
            m[f'nap_{key}'] = 0.0
            m[f'htop_{key}'] = 0.0
            m[f'crp_{key}'] = 0.0
            m[f'brp_{key}'] = 0.0
            m[f'asp_{key}'] = 0.0

        return m

    def _compute_clinic_metrics(self, clinic, source_map, all_keys):
        m = self._empty_metrics(all_keys)
        appointments = self._get_appointments(clinic)

        for appt in appointments:
            source_key = self._get_source_key_for_appointment(appt, source_map)
            is_fup = self._is_followup(appt)
            fup_suffix = '_fup' if is_fup else ''

            # Determine dynamic key with FUP variant
            dyn_key = None
            if source_key:
                # Try FUP variant first, then fallback
                fup_key = f'{source_key}{fup_suffix}'
                if fup_key in all_keys:
                    dyn_key = fup_key
                elif source_key in all_keys:
                    dyn_key = source_key

            sale_order = appt.sale_order_id or (
                appt.parent_appointment_id.sale_order_id
                if appt.parent_appointment_id else False
            )
            appt_sale_type = appt.appointment_type_id.sale_type if appt.appointment_type_id else False

            # TOTAL APPOINTMENTS
            m['total_appointments'] += 1
            if dyn_key:
                k = f'ta_{dyn_key}'
                if k in m:
                    m[k] += 1

            # DIAGNOSTIC
            if appt_sale_type == 'service':
                m['total_diagnostic_appointments'] += 1
                if dyn_key:
                    k = f'da_{dyn_key}'
                    if k in m:
                        m[k] += 1

                m['hearing_test_booked'] += 1
                if dyn_key:
                    k = f'htb_{dyn_key}'
                    if k in m:
                        m[k] += 1

            # ATTENDED
            if appt.status in ('checked_in', 'in_consultation', 'completed'):
                m['hearing_test_attended'] += 1
                if dyn_key:
                    k = f'hta_{dyn_key}'
                    if k in m:
                        m[k] += 1

                if appt_sale_type == 'service':
                    m['hearing_test_opportunity'] += 1
                    if dyn_key:
                        k = f'hto_{dyn_key}'
                        if k in m:
                            m[k] += 1

            # CONVERSIONS
            if appt_sale_type == 'device' and sale_order:
                m['conversions_prescriptions'] += 1
                if dyn_key:
                    k = f'cp_{dyn_key}'
                    if k in m:
                        m[k] += 1

                ha_lines = sale_order.order_line.filtered(
                    lambda l: l.product_id and self._is_ha_product(l.product_id)
                )
                if ha_lines:
                    ha_qty = sum(ha_lines.mapped('product_uom_qty'))
                    if ha_qty >= 2:
                        m['binaural'] += 1
                        if dyn_key:
                            k = f'bin_{dyn_key}'
                            if k in m:
                                m[k] += 1

                    m['hearing_unit'] += int(ha_qty)
                    if dyn_key:
                        k = f'ha_{dyn_key}'
                        if k in m:
                            m[k] += int(ha_qty)

                    revenue = sum(ha_lines.mapped('price_subtotal'))
                    m['gross_revenue'] += revenue
                    if dyn_key:
                        k = f'gr_{dyn_key}'
                        if k in m:
                            m[k] += revenue

        return m

    def _compute_percentages(self, m, all_keys):
        htb = m.get('hearing_test_booked', 0)
        hta = m.get('hearing_test_attended', 0)
        hto = m.get('hearing_test_opportunity', 0)
        cp = m.get('conversions_prescriptions', 0)
        bin_c = m.get('binaural', 0)
        ha = m.get('hearing_unit', 0)
        gr = m.get('gross_revenue', 0.0)

        m['net_attendance_percent'] = (hta / htb * 100) if htb else 0.0
        m['hearing_test_opportunity_percentage'] = (hto / hta * 100) if hta else 0.0
        m['conversion_rate_percent'] = (cp / hto * 100) if hto else 0.0
        m['binaural_rate_percentage'] = (bin_c / cp * 100) if cp else 0.0
        m['average_selling_price'] = (gr / ha) if ha else 0.0
        m['fitting_revenue'] = gr

        for key in all_keys:
            htb_k = m.get(f'htb_{key}', 0)
            hta_k = m.get(f'hta_{key}', 0)
            hto_k = m.get(f'hto_{key}', 0)
            cp_k = m.get(f'cp_{key}', 0)
            bin_k = m.get(f'bin_{key}', 0)
            ha_k = m.get(f'ha_{key}', 0)
            gr_k = m.get(f'gr_{key}', 0.0)

            m[f'nap_{key}'] = (hta_k / htb_k * 100) if htb_k else 0.0
            m[f'htop_{key}'] = (hto_k / hta_k * 100) if hta_k else 0.0
            m[f'crp_{key}'] = (cp_k / hto_k * 100) if hto_k else 0.0
            m[f'brp_{key}'] = (bin_k / cp_k * 100) if cp_k else 0.0
            m[f'asp_{key}'] = (gr_k / ha_k) if ha_k else 0.0

        return m

    def _merge_metrics(self, target, source):
        for k, v in source.items():
            if k in target and isinstance(v, (int, float)):
                target[k] += v
        return target

    def _recompute_percentages(self, m, all_keys):
        """Recompute percentages after merging"""
        return self._compute_percentages(m, all_keys)

    # ========================================
    # EXCEL GENERATION
    # ========================================
    def _generate_excel_report(self):
        clinics = self._get_clinics()
        if not clinics:
            raise ValidationError(_('No clinics found.'))

        # Build dynamic hierarchy
        hierarchy = self._get_source_hierarchy()
        source_map, all_keys = self._build_source_map(hierarchy)
        if not all_keys:
            raise ValidationError(_('No custom source children found. Please configure Source Hierarchy.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # ========================================
        # FORMATS
        # ========================================
        parent_header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
            'fg_color': '#1F4E78', 'font_color': 'white', 'border': 1, 'font_size': 10
        })
        child_header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
            'fg_color': '#D9E1F2', 'border': 1, 'font_size': 9
        })
        overall_header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
            'fg_color': '#FFD966', 'border': 1, 'font_size': 9
        })
        base_header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
            'fg_color': '#4472C4', 'font_color': 'white', 'border': 1, 'font_size': 9
        })
        text_format = workbook.add_format({
            'border': 1, 'font_size': 9, 'text_wrap': True, 'valign': 'vcenter'
        })
        text_left_format = workbook.add_format({
            'border': 1, 'font_size': 9, 'text_wrap': True, 'valign': 'vcenter', 'align': 'left'
        })
        number_format = workbook.add_format({
            'num_format': '#,##0', 'border': 1, 'font_size': 9, 'align': 'center', 'valign': 'vcenter'
        })
        currency_format = workbook.add_format({
            'num_format': '#,##0', 'border': 1, 'font_size': 9, 'align': 'right', 'valign': 'vcenter'
        })
        percent_format = workbook.add_format({
            'num_format': '0.00"%"', 'border': 1, 'font_size': 9, 'align': 'center', 'valign': 'vcenter'
        })
        title_format = workbook.add_format({
            'bold': True, 'font_size': 12, 'align': 'left', 'valign': 'vcenter'
        })
        am_header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'left',
            'fg_color': '#FFE699', 'border': 1, 'font_size': 10
        })
        total_format = workbook.add_format({
            'bold': True, 'border': 1, 'font_size': 9, 'align': 'center',
            'valign': 'vcenter', 'fg_color': '#E2EFDA'
        })
        total_left_format = workbook.add_format({
            'bold': True, 'border': 1, 'font_size': 9, 'align': 'left',
            'valign': 'vcenter', 'fg_color': '#E2EFDA'
        })
        total_number_format = workbook.add_format({
            'bold': True, 'num_format': '#,##0', 'border': 1, 'font_size': 9,
            'align': 'center', 'valign': 'vcenter', 'fg_color': '#E2EFDA'
        })
        total_currency_format = workbook.add_format({
            'bold': True, 'num_format': '#,##0', 'border': 1, 'font_size': 9,
            'align': 'right', 'valign': 'vcenter', 'fg_color': '#E2EFDA'
        })
        total_percent_format = workbook.add_format({
            'bold': True, 'num_format': '0.00"%"', 'border': 1, 'font_size': 9,
            'align': 'center', 'valign': 'vcenter', 'fg_color': '#E2EFDA'
        })
        region_total_format = workbook.add_format({
            'bold': True, 'border': 1, 'font_size': 9, 'align': 'center',
            'valign': 'vcenter', 'fg_color': '#DAEEF3'
        })
        region_total_left_format = workbook.add_format({
            'bold': True, 'border': 1, 'font_size': 9, 'align': 'left',
            'valign': 'vcenter', 'fg_color': '#DAEEF3'
        })
        region_total_number_format = workbook.add_format({
            'bold': True, 'num_format': '#,##0', 'border': 1, 'font_size': 9,
            'align': 'center', 'valign': 'vcenter', 'fg_color': '#DAEEF3'
        })
        region_total_currency_format = workbook.add_format({
            'bold': True, 'num_format': '#,##0', 'border': 1, 'font_size': 9,
            'align': 'right', 'valign': 'vcenter', 'fg_color': '#DAEEF3'
        })
        region_total_percent_format = workbook.add_format({
            'bold': True, 'num_format': '0.00"%"', 'border': 1, 'font_size': 9,
            'align': 'center', 'valign': 'vcenter', 'fg_color': '#DAEEF3'
        })
        india_total_format = workbook.add_format({
            'bold': True, 'border': 1, 'font_size': 9, 'align': 'center',
            'valign': 'vcenter', 'fg_color': '#FFC7CE'
        })
        india_total_left_format = workbook.add_format({
            'bold': True, 'border': 1, 'font_size': 9, 'align': 'left',
            'valign': 'vcenter', 'fg_color': '#FFC7CE'
        })
        india_total_number_format = workbook.add_format({
            'bold': True, 'num_format': '#,##0', 'border': 1, 'font_size': 9,
            'align': 'center', 'valign': 'vcenter', 'fg_color': '#FFC7CE'
        })
        india_total_currency_format = workbook.add_format({
            'bold': True, 'num_format': '#,##0', 'border': 1, 'font_size': 9,
            'align': 'right', 'valign': 'vcenter', 'fg_color': '#FFC7CE'
        })
        india_total_percent_format = workbook.add_format({
            'bold': True, 'num_format': '0.00"%"', 'border': 1, 'font_size': 9,
            'align': 'center', 'valign': 'vcenter', 'fg_color': '#FFC7CE'
        })
        date_format = workbook.add_format({
            'border': 1, 'font_size': 9, 'num_format': 'dd-mmm-yyyy',
            'align': 'center', 'valign': 'vcenter'
        })

        # ========================================
        # WORKSHEET
        # ========================================
        sheet_name = self.report_type.upper()
        ws = workbook.add_worksheet(sheet_name)
        ws.set_zoom(70)

        # ===== BASE COLUMNS (first 9) =====
        base_headers = [
            ('Store Name', 30),
            ('StoreCode', 10),
            ('City', 14),
            ('State', 14),
            ('Area Manager', 14),
            ('Region', 10),
            ('Clinic Type', 10),
            ('Opening Date', 12),
            ('Store Version', 14),
        ]
        for i, (h, w) in enumerate(base_headers):
            ws.merge_range(0, i, 1, i, h, base_header_format)
            ws.set_column(i, i, w)

        # ===== DYNAMIC METRIC COLUMNS =====
        # For each metric, we have: [child1, child2, ..., childN, OVERALL]
        METRIC_GROUPS = [
            ('TOTAL NUMBER OF APPOINTMENTS', 'ta', 'number'),
            ('TOTAL NUMBER OF DIAGNOSTIC APPOINTMENTS', 'da', 'number'),
            ('HEARING TEST APPOINTMENTS BOOKED', 'htb', 'number'),
            ('HEARING TEST APPOINTMENTS ATTENDED', 'hta', 'number'),
            ('NET ATTENDANCE %', 'nap', 'percent'),
            ('HEARING TEST OPPORTUNITY (HEARING LOSS)', 'hto', 'number'),
            ('Hearing Test Opportunity % (HL %)', 'htop', 'percent'),
            ('# Conversions (Prescriptions)', 'cp', 'number'),
            ('Conversion Rate %', 'crp', 'percent'),
            ('# Binaural', 'bin', 'number'),
            ('Binaural Rate %', 'brp', 'percent'),
            ('HA Units', 'ha', 'number'),
            ('ASP', 'asp', 'currency'),
            ('Gross Revenue', 'gr', 'currency'),
            ('Fitting Revenue', 'fr', 'currency'),
        ]

        col = 9
        metric_start_cols = {}   # prefix -> (start_col, overall_col, child_cols_map)
        col_map = {}             # (prefix, key) -> col_index

        for metric_name, prefix, fmt_type in METRIC_GROUPS:
            start_col = col

            # ===== ROW 0: Parent headers (dynamic hierarchy) =====
            # For each parent (Doctor, Marketing, OUTREACH), merge across its children
            parent_span_start = col
            for parent in hierarchy:
                children = parent['children']
                if not children:
                    continue
                # Count only children that appear in our all_keys
                valid_children = [c for c in children if c['key'] in all_keys]
                if not valid_children:
                    continue

                span = len(valid_children)
                ws.merge_range(0, parent_span_start, 0, parent_span_start + span - 1,
                               parent['parent_name'].upper(), parent_header_format)
                parent_span_start += span

            # OVERALL merged header for this metric
            overall_col = parent_span_start
            ws.merge_range(0, overall_col, 1, overall_col, 'OVERALL', overall_header_format)
            ws.set_column(overall_col, overall_col, 12)

            # ===== ROW 1: Child headers =====
            child_col = start_col
            child_col_map = {}
            for parent in hierarchy:
                for child in parent['children']:
                    if child['key'] not in all_keys:
                        continue
                    ws.write(1, child_col, child['name'], child_header_format)
                    ws.set_column(child_col, child_col, 11)
                    child_col_map[child['key']] = child_col
                    col_map[(prefix, child['key'])] = child_col
                    child_col += 1

            col_map[(prefix, 'OVERALL')] = overall_col
            metric_start_cols[prefix] = {
                'start': start_col,
                'overall': overall_col,
                'children': child_col_map,
                'fmt_type': fmt_type,
            }
            col = overall_col + 1

        # ===== Last two columns =====
        opening_date_col = col
        ws.merge_range(0, opening_date_col, 1, opening_date_col, 'Opening Date', base_header_format)
        ws.set_column(opening_date_col, opening_date_col, 12)

        closed_date_col = col + 1
        ws.merge_range(0, closed_date_col, 1, closed_date_col, 'Closed Date', base_header_format)
        ws.set_column(closed_date_col, closed_date_col, 12)

        total_cols = col + 2

        # ========================================
        # WRITE DATA
        # ========================================
        row = 2

        # Group clinics by (Area Manager, Region)
        am_groups = {}
        for clinic in clinics:
            am_name = clinic.area_manager_id.name if clinic.area_manager_id else 'Unassigned'
            region_name = clinic.region or 'Unassigned'
            am_groups.setdefault((am_name, region_name), []).append(clinic)

        region_overall = {}
        grand_overall = self._empty_metrics(all_keys)

        for (am_name, region_name), group_clinics in sorted(am_groups.items()):
            # AM header row
            ws.merge_range(row, 0, row, total_cols - 1,
                           f'AM: {am_name}  |  Region: {region_name}', am_header_format)
            row += 1

            am_metrics = self._empty_metrics(all_keys)

            for clinic in group_clinics:
                raw = self._compute_clinic_metrics(clinic, source_map, all_keys)
                raw = self._compute_percentages(raw, all_keys)

                # Accumulate into AM and Grand
                for k, v in raw.items():
                    if k in am_metrics and isinstance(v, (int, float)):
                        am_metrics[k] += v
                    if k in grand_overall and isinstance(v, (int, float)):
                        grand_overall[k] += v

                # Write base columns
                ws.write(row, 0, clinic.name or '', text_left_format)
                ws.write(row, 1, clinic.clinic_code or '', text_format)
                ws.write(row, 2, clinic.city or '', text_format)
                ws.write(row, 3, clinic.state_id.name if clinic.state_id else '', text_format)
                ws.write(row, 4, clinic.area_manager_id.name if clinic.area_manager_id else '', text_format)
                ws.write(row, 5, clinic.region or '', text_format)
                ws.write(row, 6, clinic.clinic_type or '', text_format)
                ws.write(row, 7, clinic.go_live_date, date_format)
                ws.write(row, 8, clinic.clinic_version or '', text_format)

                # Write metric columns
                for prefix, info in metric_start_cols.items():
                    fmt_type = info['fmt_type']
                    for key, c in info['children'].items():
                        val = raw.get(f'{prefix}_{key}', 0)
                        self._write_cell(ws, row, c, val, fmt_type,
                                        number_format, currency_format, percent_format)
                    # OVERALL
                    overall_key_map = {
                        'ta': 'total_appointments',
                        'da': 'total_diagnostic_appointments',
                        'htb': 'hearing_test_booked',
                        'hta': 'hearing_test_attended',
                        'nap': 'net_attendance_percent',
                        'hto': 'hearing_test_opportunity',
                        'htop': 'hearing_test_opportunity_percentage',
                        'cp': 'conversions_prescriptions',
                        'crp': 'conversion_rate_percent',
                        'bin': 'binaural',
                        'brp': 'binaural_rate_percentage',
                        'ha': 'hearing_unit',
                        'asp': 'average_selling_price',
                        'gr': 'gross_revenue',
                        'fr': 'fitting_revenue',
                    }
                    overall_val = raw.get(overall_key_map[prefix], 0)
                    self._write_cell(ws, row, info['overall'], overall_val, fmt_type,
                                    number_format, currency_format, percent_format)

                # Opening and closing date at end
                ws.write(row, opening_date_col, clinic.go_live_date, date_format)
                ws.write(row, closed_date_col, '', date_format)
                row += 1

            # ---- AM TOTAL ROW ----
            am_metrics = self._compute_percentages(am_metrics, all_keys)
            ws.write(row, 0, f'{am_name} Total', total_left_format)
            for i in range(1, 9):
                ws.write(row, i, '', total_format)
            self._write_total_metrics(ws, row, am_metrics, metric_start_cols,
                                     all_keys, 'total')
            ws.write(row, opening_date_col, '', total_format)
            ws.write(row, closed_date_col, '', total_format)
            row += 1

            # Accumulate region
            if region_name not in region_overall:
                region_overall[region_name] = self._empty_metrics(all_keys)
            for k, v in am_metrics.items():
                if k in region_overall[region_name] and isinstance(v, (int, float)):
                    region_overall[region_name][k] += v

        # ========================================
        # REGION TOTALS
        # ========================================
        row += 1
        ws.merge_range(row, 0, row, total_cols - 1, 'REGION TOTALS', parent_header_format)
        row += 1

        for region_name, reg_metrics in sorted(region_overall.items()):
            reg_metrics = self._compute_percentages(reg_metrics, all_keys)
            ws.write(row, 0, f'{region_name} Total', region_total_left_format)
            for i in range(1, 9):
                ws.write(row, i, '', region_total_format)
            self._write_total_metrics(ws, row, reg_metrics, metric_start_cols,
                                     all_keys, 'region')
            ws.write(row, opening_date_col, '', region_total_format)
            ws.write(row, closed_date_col, '', region_total_format)
            row += 1

        # ========================================
        # INDIA TOTAL
        # ========================================
        grand_overall = self._compute_percentages(grand_overall, all_keys)
        row += 1
        ws.merge_range(row, 0, row, total_cols - 1, 'INDIA TOTAL', parent_header_format)
        row += 1

        ws.write(row, 0, 'India Total', india_total_left_format)
        for i in range(1, 9):
            ws.write(row, i, '', india_total_format)
        self._write_total_metrics(ws, row, grand_overall, metric_start_cols,
                                 all_keys, 'india')

        workbook.close()

        # ========================================
        # DOWNLOAD
        # ========================================
        file_data = output.getvalue()
        today = fields.Date.today()
        file_name = f"{self.file_name}_{self.report_type}_{today.strftime('%Y%m%d')}.xlsx"
        file_data_base64 = base64.b64encode(file_data)

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_data_base64,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'cdt.journey.report.wizard',
            'res_id': self.id
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new'
        }

    # ========================================
    # HELPERS
    # ========================================
    def _write_cell(self, ws, row, col, val, fmt_type,
                    number_format, currency_format, percent_format):
        if fmt_type == 'number':
            ws.write(row, col, val or 0, number_format)
        elif fmt_type == 'currency':
            ws.write(row, col, val or 0, currency_format)
        elif fmt_type == 'percent':
            ws.write(row, col, val or 0, percent_format)
        else:
            ws.write(row, col, val or '', number_format)

    def _write_total_metrics(self, ws, row, m, metric_start_cols, all_keys, style):
        """Write total row metric cells with style variant: total/region/india"""
        style_map = {
            'total': (total_number_format, total_currency_format, total_percent_format),
            'region': (region_total_number_format, region_total_currency_format, region_total_percent_format),
            'india': (india_total_number_format, india_total_currency_format, india_total_percent_format),
        }
        num_f, cur_f, pct_f = style_map[style]

        overall_key_map = {
            'ta': 'total_appointments',
            'da': 'total_diagnostic_appointments',
            'htb': 'hearing_test_booked',
            'hta': 'hearing_test_attended',
            'nap': 'net_attendance_percent',
            'hto': 'hearing_test_opportunity',
            'htop': 'hearing_test_opportunity_percentage',
            'cp': 'conversions_prescriptions',
            'crp': 'conversion_rate_percent',
            'bin': 'binaural',
            'brp': 'binaural_rate_percentage',
            'ha': 'hearing_unit',
            'asp': 'average_selling_price',
            'gr': 'gross_revenue',
            'fr': 'fitting_revenue',
        }

        for prefix, info in metric_start_cols.items():
            fmt_type = info['fmt_type']
            for key, c in info['children'].items():
                val = m.get(f'{prefix}_{key}', 0)
                if fmt_type == 'number':
                    ws.write(row, c, val or 0, num_f)
                elif fmt_type == 'currency':
                    ws.write(row, c, val or 0, cur_f)
                elif fmt_type == 'percent':
                    ws.write(row, c, val or 0, pct_f)

            overall_val = m.get(overall_key_map[prefix], 0)
            if fmt_type == 'number':
                ws.write(row, info['overall'], overall_val or 0, num_f)
            elif fmt_type == 'currency':
                ws.write(row, info['overall'], overall_val or 0, cur_f)
            elif fmt_type == 'percent':
                ws.write(row, info['overall'], overall_val or 0, pct_f)