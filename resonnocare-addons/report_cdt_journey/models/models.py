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

    # =====================================================================
    # CONSTANTS
    # =====================================================================
    APPT_TYPE_DIAGNOSTIC   = 'Diagnostics'
    APPT_TYPE_HEARING_TEST = 'Hearing Test & Trial'
    APPT_TYPE_SPEECH       = 'Speech'
    APPT_TYPE_VOICE        = 'Voice'
    APPT_TYPE_SWALLOWING   = 'Swallowing'
    APPT_TYPE_SLEEP        = 'Sleep'
    APPT_TYPE_DEVICE_SALE  = 'Device Sale'

    HEARING_LOSS_OUTCOMES = ('HATS', 'RX', 'DEF', 'DRREF', 'USER')
    EXCLUDED_OUTCOMES     = ('ANSP', 'FTA')
    SPEECH_TYPES          = ('Speech', 'Voice', 'Swallowing')

    OUTCOME_NAME_MAP = {
        'FAILED TO ATTEND':                    'FTA',
        'HEARING AID TRIAL SUCCESSFUL':        'HATS',
        'PRESCRIBED':                          'RX',
        'PRESCRIPTION':                        'RX',
        'REFERRED TO DOCTOR':                  'DRREF',
        'REFERRED TO DOCTOR.':                 'DRREF',
        'CLIENT DEFERRED':                     'DEF',
        'APPOINTMENT SUCCESSFULLY COMPLETED':  'ASC',
        'APPOINTMENT SUCCESSFUL':              'ASC',
        'NORMAL HEARING':                      'NORM',
        'ATTENDED NO SERVICE PROVIDED':        'ANSP',
        'HA USER':                             'USER',
        'HEARING AID USER':                    'USER',
    }

    # =====================================================================
    # METRIC PREFIXES
    #   mrp    = MRP (HA)                    (list amount, no discount)
    #   disc   = Discount (HA)
    #   gr     = Gross Revenue (HA)          (after discount)
    #   mrpsp  = MRP (Speech)
    #   discsp = Discount (Speech)
    #   sgr    = Gross Revenue (Speech)
    #   mrpsl  = MRP (Sleep)
    #   discsl = Discount (Sleep)
    #   slgr   = Gross Revenue (Sleep)
    #   mrpgh  = MRP (Diagnostics HA)
    #   discgh = Discount (Diagnostics HA)
    #   dgha   = Gross Revenue (Diagnostics HA)
    #   mrpgp  = MRP (Diagnostics Speech)
    #   discgp = Discount (Diagnostics Speech)
    #   dgsp   = Gross Revenue (Diagnostics Speech)
    #   mrpgl  = MRP (Diagnostics Sleep)
    #   discgl = Discount (Diagnostics Sleep)
    #   dgsl   = Gross Revenue (Diagnostics Sleep)
    # =====================================================================
    INT_PREFIXES = (
        'da', 'htb', 'hta', 'hl', 'cp', 'bin', 'ha',
        'sphb', 'spha', 'ther', 'slpb', 'slpa', 'pap',
    )
    FLOAT_PREFIXES = (
        'asp',
        'mrp', 'disc', 'gr',
        'mrpsp', 'discsp', 'sgr',
        'mrpsl', 'discsl', 'slgr',
        'mrpgh', 'discgh', 'dgha',
        'mrpgp', 'discgp', 'dgsp',
        'mrpgl', 'discgl', 'dgsl',
    )

    # =====================================================================
    # ONCHANGE / ACTIONS
    # =====================================================================
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

    # =====================================================================
    # SOURCE HIERARCHY
    # =====================================================================
    def _get_source_hierarchy(self):
        CustomSource = self.env['custom.source'].sudo()
        parents = CustomSource.search(
            [('parent_id', '=', False), ('active', '=', True)], order='code'
        )

        hierarchy = []
        for parent in parents:
            children = CustomSource.search([
                ('parent_id', '=', parent.id),
                ('active', '=', True)
            ], order='code')

            children_data = []
            for child in children:
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
                'children': children_data,
            })

        return hierarchy

    def _build_source_map(self, hierarchy):
        source_map = {}
        all_keys = []
        for parent in hierarchy:
            for child in parent['children']:
                source_map[child['id']] = child['key']
                all_keys.append(child['key'])
        return source_map, all_keys

    def _get_source_key_for_appointment(self, appointment, source_map):
        if not appointment.ref_source:
            return None
        return source_map.get(appointment.ref_source.id)

    # =====================================================================
    # HELPERS
    # =====================================================================
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
        """HA item_type == 'ha'."""
        if not product:
            return False
        item_type = False
        if hasattr(product, 'item_type'):
            item_type = product.item_type
        elif hasattr(product.product_tmpl_id, 'item_type'):
            item_type = product.product_tmpl_id.item_type
        return item_type == 'ha'

    def _appt_type_name(self, appointment):
        if appointment.appointment_type_id:
            return appointment.appointment_type_id.name
        return None

    def _outcome_codes(self, appointment):
        """Return a set of UPPERCASE short outcome codes for this appointment."""
        outcomes = appointment.appointment_outcome_ids
        codes = set()
        if not outcomes:
            return codes

        for o in outcomes:
            raw_code = (getattr(o, 'code', '') or '').strip().upper()
            # resonnocare.appointment.outcome has NO `name` field.
            raw_name = (getattr(o, 'outcome', None)
                        or getattr(o, 'name', None)
                        or '').strip().upper()

            if raw_code:
                mapped_code = self.OUTCOME_NAME_MAP.get(raw_code, raw_code)
                if mapped_code:
                    codes.add(mapped_code)
                continue

            if raw_name:
                mapped_name = self.OUTCOME_NAME_MAP.get(raw_name, raw_name)
                if mapped_name:
                    codes.add(mapped_name)

        return codes

    def _is_diagnostic_type(self, appointment):
        return self._appt_type_name(appointment) == self.APPT_TYPE_DIAGNOSTIC

    def _is_hearing_test_type(self, appointment):
        return self._appt_type_name(appointment) == self.APPT_TYPE_HEARING_TEST

    def _is_speech_type(self, appointment):
        return self._appt_type_name(appointment) in self.SPEECH_TYPES

    def _is_sleep_type(self, appointment):
        return self._appt_type_name(appointment) == self.APPT_TYPE_SLEEP

    def _is_device_sale_type(self, appointment):
        return self._appt_type_name(appointment) == self.APPT_TYPE_DEVICE_SALE

    def _is_attended(self, appointment):
        """status = completed AND no outcome is ANSP / FTA."""
        if appointment.status != 'completed':
            return False
        codes = self._outcome_codes(appointment)
        excluded = {c.upper() for c in self.EXCLUDED_OUTCOMES}
        if codes & excluded:
            return False
        return True

    def _has_hearing_loss(self, appointment):
        codes = self._outcome_codes(appointment)
        hl_set = {c.upper() for c in self.HEARING_LOSS_OUTCOMES}
        return bool(codes & hl_set)

    def _is_scm_order_completed(self, sale_order):
        """SCM order created + completed."""
        if not sale_order:
            return False
        is_scm = getattr(sale_order, 'is_scm_order', True)
        is_done = sale_order.state in ('sale', 'done')
        return is_scm and is_done

    def _line_amounts(self, line):
        """Return (mrp, discount, gross) for a single sale.order.line.
        mrp     = price_unit * product_uom_qty        (list amount)
        gross   = price_subtotal_after_discount or price_subtotal  (after discount)
        discount= mrp - gross
        """
        mrp = line.price_unit * line.product_uom_qty
        gross = getattr(line, 'price_subtotal_after_discount', None) or line.price_subtotal
        discount = mrp - gross
        return mrp, discount, gross

    def _get_clinics(self):
        domain = []
        if self.clinic_ids:
            domain.append(('id', 'in', self.clinic_ids.ids))
        if self.area_manager_id:
            domain.append(('area_manager_id', '=', self.area_manager_id.id))
        if self.region:
            domain.append(('region', '=', self.region))
        return self.env['resonnocare.clinic'].search(
            domain, order='region, area_manager_id, name'
        )

    def _get_appointments(self, clinic):
        return self.env['resonnocare.appointment'].search([
            ('clinic_id', '=', clinic.id),
            ('appointment_date', '>=', self.date_from),
            ('appointment_date', '<=', self.date_to),
        ])

    # =====================================================================
    # METRICS
    # =====================================================================
    def _empty_metrics(self, all_keys):
        m = {}

        # HA funnel
        m['diag_appts']              = 0
        m['ht_booked']               = 0
        m['ht_attended']             = 0
        m['hearing_loss']            = 0
        m['conversions_ha']          = 0
        m['binaural']                = 0
        m['ha_units']                = 0
        m['asp']                     = 0.0
        m['mrp_ha']                  = 0.0
        m['disc_rev_ha']             = 0.0
        m['gross_rev_ha']            = 0.0

        # Speech
        m['speech_booked']           = 0
        m['speech_attended']         = 0
        m['therapy_enrolls']         = 0
        m['mrp_speech']              = 0.0
        m['disc_rev_speech']         = 0.0
        m['gross_rev_speech']        = 0.0

        # Sleep
        m['sleep_booked']            = 0
        m['sleep_attended']          = 0
        m['pap_conversions']         = 0
        m['mrp_sleep']               = 0.0
        m['disc_rev_sleep']          = 0.0
        m['gross_rev_sleep']         = 0.0

        # Diagnostics
        m['mrp_diag_ha']             = 0.0
        m['disc_rev_diag_ha']        = 0.0
        m['gross_rev_diag_ha']       = 0.0
        m['mrp_diag_speech']         = 0.0
        m['disc_rev_diag_speech']    = 0.0
        m['gross_rev_diag_speech']   = 0.0
        m['mrp_diag_sleep']          = 0.0
        m['disc_rev_diag_sleep']     = 0.0
        m['gross_rev_diag_sleep']    = 0.0

        # Dynamic per-source
        for prefix in self.INT_PREFIXES:
            for key in all_keys:
                m[f'{prefix}_{key}'] = 0
        for prefix in self.FLOAT_PREFIXES:
            for key in all_keys:
                m[f'{prefix}_{key}'] = 0.0

        return m

    def _compute_clinic_metrics(self, clinic, source_map, all_keys):
        m = self._empty_metrics(all_keys)
        appointments = self._get_appointments(clinic)

        for appt in appointments:
            source_key = self._get_source_key_for_appointment(appt, source_map)
            is_fup = self._is_followup(appt)
            fup_suffix = '_fup' if is_fup else ''

            dyn_key = None
            if source_key:
                fup_key = f'{source_key}{fup_suffix}'
                if fup_key in all_keys:
                    dyn_key = fup_key
                elif source_key in all_keys:
                    dyn_key = source_key

            def bump(prefix, val):
                if dyn_key:
                    k = f'{prefix}_{dyn_key}'
                    if k in m:
                        m[k] += val

            is_completed = appt.status == 'completed'
            is_attended  = self._is_attended(appt)

            sale_order = appt.sale_order_id or (
                appt.parent_appointment_id.sale_order_id
                if appt.parent_appointment_id else False
            )

            # -----------------------------------------------------
            # BLOCK A: HA FUNNEL
            # -----------------------------------------------------
            if self._is_diagnostic_type(appt):
                m['diag_appts'] += 1
                bump('da', 1)

            if self._is_hearing_test_type(appt):
                m['ht_booked'] += 1
                bump('htb', 1)

            if self._is_hearing_test_type(appt) and is_attended:
                m['ht_attended'] += 1
                bump('hta', 1)
                if self._has_hearing_loss(appt):
                    m['hearing_loss'] += 1
                    bump('hl', 1)

            if self._is_device_sale_type(appt) and self._is_scm_order_completed(sale_order):
                m['conversions_ha'] += 1
                bump('cp', 1)

                ha_lines = sale_order.order_line.filtered(
                    lambda l: l.product_id and self._is_ha_product(l.product_id)
                )
                if ha_lines:
                    ha_qty = sum(ha_lines.mapped('product_uom_qty'))
                    if ha_qty >= 2:
                        m['binaural'] += 1
                        bump('bin', 1)

                    m['ha_units'] += int(ha_qty)
                    bump('ha', int(ha_qty))

                    mrp = disc = gross = 0.0
                    for l in ha_lines:
                        a, b, c = self._line_amounts(l)
                        mrp += a; disc += b; gross += c
                    m['mrp_ha'] += mrp;         bump('mrp', mrp)
                    m['disc_rev_ha'] += disc;   bump('disc', disc)
                    m['gross_rev_ha'] += gross; bump('gr', gross)

            # -----------------------------------------------------
            # BLOCK B: SPEECH
            # -----------------------------------------------------
            if self._is_speech_type(appt):
                m['speech_booked'] += 1
                bump('sphb', 1)

                if is_attended:
                    m['speech_attended'] += 1
                    bump('spha', 1)

                if is_completed:
                    m['therapy_enrolls'] += 1
                    bump('ther', 1)

                if sale_order and is_completed:
                    sp_lines = sale_order.order_line.filtered(
                        lambda l: l.product_id and
                                  l.product_id.product_tmpl_id.item_category == 'Speech'
                    )
                    if sp_lines:
                        mrp = disc = gross = 0.0
                        for l in sp_lines:
                            a, b, c = self._line_amounts(l)
                            mrp += a; disc += b; gross += c
                        m['mrp_speech'] += mrp;         bump('mrpsp', mrp)
                        m['disc_rev_speech'] += disc;   bump('discsp', disc)
                        m['gross_rev_speech'] += gross; bump('sgr', gross)

            # -----------------------------------------------------
            # BLOCK C: SLEEP
            # -----------------------------------------------------
            if self._is_sleep_type(appt):
                m['sleep_booked'] += 1
                bump('slpb', 1)

                if is_attended:
                    m['sleep_attended'] += 1
                    bump('slpa', 1)

                if self._is_scm_order_completed(sale_order):
                    m['pap_conversions'] += 1
                    bump('pap', 1)

                if sale_order and is_completed:
                    sl_lines = sale_order.order_line.filtered(
                        lambda l: l.product_id and
                                  l.product_id.product_tmpl_id.item_category == 'Sleep'
                    )
                    if sl_lines:
                        mrp = disc = gross = 0.0
                        for l in sl_lines:
                            a, b, c = self._line_amounts(l)
                            mrp += a; disc += b; gross += c
                        m['mrp_sleep'] += mrp;         bump('mrpsl', mrp)
                        m['disc_rev_sleep'] += disc;   bump('discsl', disc)
                        m['gross_rev_sleep'] += gross; bump('slgr', gross)

            # -----------------------------------------------------
            # BLOCK D: DIAGNOSTICS REVENUE
            # -----------------------------------------------------
            if is_completed and sale_order:
                diag_lines = sale_order.order_line.filtered(
                    lambda l: l.product_id and
                              l.product_id.product_tmpl_id.item_category == 'Diagnostic Services'
                )
                for line in diag_lines:
                    product = line.product_id.product_tmpl_id
                    mrp, disc, gross = self._line_amounts(line)

                    if product.item_type == 'ha' or product.item_category == 'Hearing Device':
                        m['mrp_diag_ha']           += mrp;   bump('mrpgh', mrp)
                        m['disc_rev_diag_ha']      += disc;  bump('discgh', disc)
                        m['gross_rev_diag_ha']     += gross; bump('dgha', gross)
                    elif self._is_speech_type(appt):
                        m['mrp_diag_speech']       += mrp;   bump('mrpgp', mrp)
                        m['disc_rev_diag_speech']  += disc;  bump('discgp', disc)
                        m['gross_rev_diag_speech'] += gross; bump('dgsp', gross)
                    elif self._is_sleep_type(appt):
                        m['mrp_diag_sleep']        += mrp;   bump('mrpgl', mrp)
                        m['disc_rev_diag_sleep']   += disc;  bump('discgl', disc)
                        m['gross_rev_diag_sleep']  += gross; bump('dgsl', gross)

        m['asp'] = (m['mrp_ha'] / m['ha_units']) if m['ha_units'] else 0.0
        return m

    # =====================================================================
    # EXCEL GENERATION
    # =====================================================================
    def _generate_excel_report(self):
        clinics = self._get_clinics()
        if not clinics:
            raise ValidationError(_('No clinics found.'))

        hierarchy = self._get_source_hierarchy()
        source_map, all_keys = self._build_source_map(hierarchy)
        if not all_keys:
            raise ValidationError(
                _('No custom source children found. Please configure Source Hierarchy.')
            )

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # -----------------------------------------------------------------
        # FORMATS
        # -----------------------------------------------------------------
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
            'num_format': '#,##0', 'border': 1, 'font_size': 9,
            'align': 'center', 'valign': 'vcenter'
        })
        currency_format = workbook.add_format({
            'num_format': '#,##0', 'border': 1, 'font_size': 9,
            'align': 'right', 'valign': 'vcenter'
        })
        percent_format = workbook.add_format({
            'num_format': '0.00"%"', 'border': 1, 'font_size': 9,
            'align': 'center', 'valign': 'vcenter'
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
        date_format = workbook.add_format({
            'border': 1, 'font_size': 9, 'num_format': 'dd-mmm-yyyy',
            'align': 'center', 'valign': 'vcenter'
        })

        formats = {
            'number': number_format,
            'currency': currency_format,
            'percent': percent_format,
            'text': text_format,
            'text_left': text_left_format,
            'date': date_format,
            'total': {
                'number': total_number_format,
                'currency': total_currency_format,
                'percent': percent_format,
                'text': total_format,
                'text_left': total_left_format,
            },
            'region': {
                'number': region_total_number_format,
                'currency': region_total_currency_format,
                'percent': percent_format,
                'text': region_total_format,
                'text_left': region_total_left_format,
            },
            'india': {
                'number': india_total_number_format,
                'currency': india_total_currency_format,
                'percent': percent_format,
                'text': india_total_format,
                'text_left': india_total_left_format,
            },
        }

        # -----------------------------------------------------------------
        # WORKSHEET — three-row header
        # -----------------------------------------------------------------
        sheet_name = self.report_type.upper()
        ws = workbook.add_worksheet(sheet_name)
        ws.set_zoom(70)

        HEADER_ROW_METRIC = 0
        HEADER_ROW_PARENT = 1
        HEADER_ROW_CHILD  = 2
        DATA_START_ROW    = 3

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
            ws.merge_range(HEADER_ROW_METRIC, i, HEADER_ROW_CHILD, i,
                           h, base_header_format)
            ws.set_column(i, i, w)

        # -----------------------------------------------------------------
        # METRIC GROUPS
        #   Order per block: MRP → DISCOUNT → GROSS REVENUE
        # -----------------------------------------------------------------
        METRIC_GROUPS = [
            # HA Funnel
            ('TOTAL # DIAGNOSTIC APPTS',                 'da',     'number'),
            ('TOTAL # HEARING TEST BOOKED',              'htb',    'number'),
            ('TOTAL # HEARING TEST ATTENDED',            'hta',    'number'),
            ('TOTAL # HEARING LOSS',                     'hl',     'number'),
            ('# CONVERSIONS (Rx) (HA)',                  'cp',     'number'),
            ('# BINAURAL (Rx)',                          'bin',    'number'),
            ('HA UNITS',                                 'ha',     'number'),
            ('ASP',                                      'asp',    'currency'),
            ('MRP (HA)',                                 'mrp',    'currency'),
            ('DISCOUNT (HA)',                            'disc',   'currency'),
            ('GROSS REVENUE (HA)',                       'gr',     'currency'),

            # Speech
            ('TOTAL # SPEECH APPT BOOKED',               'sphb',   'number'),
            ('TOTAL # SPEECH APPT ATTENDED',             'spha',   'number'),
            ('TOTAL # THERAPY ENROLLS',                  'ther',   'number'),
            ('MRP (SPEECH)',                             'mrpsp',  'currency'),
            ('DISCOUNT (SPEECH)',                        'discsp', 'currency'),
            ('GROSS REVENUE (SPEECH)',                   'sgr',    'currency'),

            # Sleep
            ('TOTAL # SLEEP APPT BOOKED',                'slpb',   'number'),
            ('TOTAL # SLEEP APPT ATTENDED',              'slpa',   'number'),
            ('TOTAL # CONVERSION (Rx) PAP',              'pap',    'number'),
            ('MRP (SLEEP)',                              'mrpsl',  'currency'),
            ('DISCOUNT (SLEEP)',                         'discsl', 'currency'),
            ('GROSS REVENUE (SLEEP)',                    'slgr',   'currency'),

            # Diagnostics Revenue
            ('MRP (DIAGNOSTICS) (HA)',                   'mrpgh',  'currency'),
            ('DISCOUNT (DIAGNOSTICS) (HA)',              'discgh', 'currency'),
            ('GROSS REVENUE (DIAGNOSTICS) (HA)',         'dgha',   'currency'),
            ('MRP (DIAGNOSTICS) (SPEECH)',               'mrpgp',  'currency'),
            ('DISCOUNT (DIAGNOSTICS) (SPEECH)',          'discgp', 'currency'),
            ('GROSS REVENUE (DIAGNOSTICS) (SPEECH)',     'dgsp',   'currency'),
            ('MRP (DIAGNOSTICS) (SLEEP)',                'mrpgl',  'currency'),
            ('DISCOUNT (DIAGNOSTICS) (SLEEP)',           'discgl', 'currency'),
            ('GROSS REVENUE (DIAGNOSTICS) (SLEEP)',      'dgsl',   'currency'),
        ]

        col = 9
        metric_start_cols = {}

        for metric_name, prefix, fmt_type in METRIC_GROUPS:
            start_col = col
            parent_span_start = col

            # Row 1: parent group headers
            for parent in hierarchy:
                valid_children = [c for c in parent['children'] if c['key'] in all_keys]
                if not valid_children:
                    continue
                span = len(valid_children)
                ws.merge_range(HEADER_ROW_PARENT, parent_span_start,
                               HEADER_ROW_PARENT, parent_span_start + span - 1,
                               parent['parent_name'].upper(), parent_header_format)
                parent_span_start += span

            # OVERALL column (spans rows 1 & 2)
            overall_col = parent_span_start
            ws.merge_range(HEADER_ROW_PARENT, overall_col,
                           HEADER_ROW_CHILD,  overall_col,
                           'OVERALL', overall_header_format)
            ws.set_column(overall_col, overall_col, 12)

            # Row 2: child headers
            child_col = start_col
            child_col_map = {}
            for parent in hierarchy:
                for child in parent['children']:
                    if child['key'] not in all_keys:
                        continue
                    ws.write(HEADER_ROW_CHILD, child_col, child['name'], child_header_format)
                    ws.set_column(child_col, child_col, 11)
                    child_col_map[child['key']] = child_col
                    child_col += 1

            # Row 0: metric name merged across the whole block
            ws.merge_range(HEADER_ROW_METRIC, start_col,
                           HEADER_ROW_METRIC, overall_col,
                           metric_name, base_header_format)

            metric_start_cols[prefix] = {
                'start': start_col,
                'overall': overall_col,
                'children': child_col_map,
                'fmt_type': fmt_type,
            }
            col = overall_col + 1

        opening_date_col = col
        ws.merge_range(HEADER_ROW_METRIC, opening_date_col,
                       HEADER_ROW_CHILD,  opening_date_col,
                       'Opening Date', base_header_format)
        ws.set_column(opening_date_col, opening_date_col, 12)

        closed_date_col = col + 1
        ws.merge_range(HEADER_ROW_METRIC, closed_date_col,
                       HEADER_ROW_CHILD,  closed_date_col,
                       'Closed Date', base_header_format)
        ws.set_column(closed_date_col, closed_date_col, 12)

        total_cols = col + 2

        # -----------------------------------------------------------------
        # OVERALL MAP
        # -----------------------------------------------------------------
        overall_map = {
            'da':     'diag_appts',
            'htb':    'ht_booked',
            'hta':    'ht_attended',
            'hl':     'hearing_loss',
            'cp':     'conversions_ha',
            'bin':    'binaural',
            'ha':     'ha_units',
            'asp':    'asp',

            'mrp':    'mrp_ha',
            'disc':   'disc_rev_ha',
            'gr':     'gross_rev_ha',

            'sphb':   'speech_booked',
            'spha':   'speech_attended',
            'ther':   'therapy_enrolls',
            'mrpsp':  'mrp_speech',
            'discsp': 'disc_rev_speech',
            'sgr':    'gross_rev_speech',

            'slpb':   'sleep_booked',
            'slpa':   'sleep_attended',
            'pap':    'pap_conversions',
            'mrpsl':  'mrp_sleep',
            'discsl': 'disc_rev_sleep',
            'slgr':   'gross_rev_sleep',

            'mrpgh':  'mrp_diag_ha',
            'discgh': 'disc_rev_diag_ha',
            'dgha':   'gross_rev_diag_ha',
            'mrpgp':  'mrp_diag_speech',
            'discgp': 'disc_rev_diag_speech',
            'dgsp':   'gross_rev_diag_speech',
            'mrpgl':  'mrp_diag_sleep',
            'discgl': 'disc_rev_diag_sleep',
            'dgsl':   'gross_rev_diag_sleep',
        }

        # -----------------------------------------------------------------
        # WRITE DATA
        # -----------------------------------------------------------------
        row = DATA_START_ROW
        am_groups = {}
        for clinic in clinics:
            am_name = clinic.area_manager_id.name if clinic.area_manager_id else 'Unassigned'
            region_name = clinic.region or 'Unassigned'
            am_groups.setdefault((am_name, region_name), []).append(clinic)

        region_overall = {}
        grand_overall = self._empty_metrics(all_keys)

        for (am_name, region_name), group_clinics in sorted(am_groups.items()):
            ws.merge_range(row, 0, row, total_cols - 1,
                           f'AM: {am_name}  |  Region: {region_name}', am_header_format)
            row += 1

            am_metrics = self._empty_metrics(all_keys)

            for clinic in group_clinics:
                raw = self._compute_clinic_metrics(clinic, source_map, all_keys)

                for k, v in raw.items():
                    if isinstance(v, (int, float)):
                        if k in am_metrics:
                            am_metrics[k] += v
                        if k in grand_overall:
                            grand_overall[k] += v

                ws.write(row, 0, clinic.name or '', text_left_format)
                ws.write(row, 1, clinic.clinic_code or '', text_format)
                ws.write(row, 2, clinic.city or '', text_format)
                ws.write(row, 3, clinic.state_id.name if clinic.state_id else '', text_format)
                ws.write(row, 4, clinic.area_manager_id.name if clinic.area_manager_id else '', text_format)
                ws.write(row, 5, clinic.region or '', text_format)
                ws.write(row, 6, clinic.clinic_type or '', text_format)
                ws.write(row, 7, clinic.go_live_date, date_format)
                ws.write(row, 8, clinic.clinic_version or '', text_format)

                for prefix, info in metric_start_cols.items():
                    fmt_type = info['fmt_type']
                    for key, c in info['children'].items():
                        val = raw.get(f'{prefix}_{key}', 0)
                        self._write_cell(ws, row, c, val, fmt_type, formats)
                    overall_val = raw.get(overall_map.get(prefix, ''), 0)
                    self._write_cell(ws, row, info['overall'], overall_val, fmt_type, formats)

                ws.write(row, opening_date_col, clinic.go_live_date, date_format)
                ws.write(row, closed_date_col, '', date_format)
                row += 1

            # AM total row
            self._recalc_derived(am_metrics)
            ws.write(row, 0, f'{am_name} Total', total_left_format)
            for i in range(1, 9):
                ws.write(row, i, '', total_format)
            self._write_total_metrics(ws, row, am_metrics, metric_start_cols,
                                      overall_map, 'total', formats)
            ws.write(row, opening_date_col, '', total_format)
            ws.write(row, closed_date_col, '', total_format)
            row += 1

            if region_name not in region_overall:
                region_overall[region_name] = self._empty_metrics(all_keys)
            for k, v in am_metrics.items():
                if isinstance(v, (int, float)) and k in region_overall[region_name]:
                    region_overall[region_name][k] += v

        # Region totals
        row += 1
        ws.merge_range(row, 0, row, total_cols - 1, 'REGION TOTALS', parent_header_format)
        row += 1
        for region_name, reg_metrics in sorted(region_overall.items()):
            self._recalc_derived(reg_metrics)
            ws.write(row, 0, f'{region_name} Total', region_total_left_format)
            for i in range(1, 9):
                ws.write(row, i, '', region_total_format)
            self._write_total_metrics(ws, row, reg_metrics, metric_start_cols,
                                      overall_map, 'region', formats)
            ws.write(row, opening_date_col, '', region_total_format)
            ws.write(row, closed_date_col, '', region_total_format)
            row += 1

        # India total
        row += 1
        ws.merge_range(row, 0, row, total_cols - 1, 'INDIA TOTAL', parent_header_format)
        row += 1
        self._recalc_derived(grand_overall)
        ws.write(row, 0, 'India Total', india_total_left_format)
        for i in range(1, 9):
            ws.write(row, i, '', india_total_format)
        self._write_total_metrics(ws, row, grand_overall, metric_start_cols,
                                  overall_map, 'india', formats)

        ws.freeze_panes(DATA_START_ROW, 9)
        workbook.close()

        # -----------------------------------------------------------------
        # DOWNLOAD
        # -----------------------------------------------------------------
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

    # =====================================================================
    # HELPERS
    # =====================================================================
    def _recalc_derived(self, m):
        """Recompute ASP on aggregate rows."""
        m['asp'] = (m['mrp_ha'] / m['ha_units']) if m.get('ha_units') else 0.0

    def _write_cell(self, ws, row, col, val, fmt_type, formats):
        if fmt_type == 'number':
            ws.write(row, col, val or 0, formats['number'])
        elif fmt_type == 'currency':
            ws.write(row, col, val or 0, formats['currency'])
        elif fmt_type == 'percent':
            ws.write(row, col, val or 0, formats['percent'])
        else:
            ws.write(row, col, val or '', formats['number'])

    def _write_total_metrics(self, ws, row, m, metric_start_cols,
                             overall_map, style, formats):
        style_formats = formats.get(style, formats['total'])
        num_f = style_formats['number']
        cur_f = style_formats['currency']
        pct_f = style_formats['percent']

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

            overall_val = m.get(overall_map.get(prefix, ''), 0)
            if fmt_type == 'number':
                ws.write(row, info['overall'], overall_val or 0, num_f)
            elif fmt_type == 'currency':
                ws.write(row, info['overall'], overall_val or 0, cur_f)
            elif fmt_type == 'percent':
                ws.write(row, info['overall'], overall_val or 0, pct_f)