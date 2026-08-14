# -*- coding: utf-8 -*-
##############################################################################
#
#    Jupical Technologies Pvt. Ltd.
#    Copyright (C) 2024-TODAY Jupical Technologies(<http://www.jupical.io>).
#
##############################################################################
import base64
import io
from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import openpyxl
except ImportError:
    openpyxl = None


class StudentTransferWizard(models.TransientModel):
    _name = 'student.transfer.wizard'
    _description = 'Student Transfer Wizard'

    # Source class 
    from_year_id = fields.Many2one('year.year', string='From Year', required=True)
    from_standard_id = fields.Many2one('student.standard', string='From Standard', required=True)
    from_div_id = fields.Many2one('standard.division', string='From Division', required=True)

    # Destination class 
    to_year_id = fields.Many2one('year.year', string='To Year', required=True)
    to_standard_id = fields.Many2one('student.standard', string='To Standard', required=True)
    to_div_id = fields.Many2one('standard.division', string='To Division', required=True)

    # Students matched from source 
    student_ids = fields.Many2many(
        'res.partner',
        'student_transfer_wizard_rel',
        'wizard_id',
        'student_id',
        string='Students to Transfer',
    )
    student_count = fields.Integer(
        string='Total Students',
        compute='_compute_student_count',
    )

    # Report Layout fields
    download_report_ready = fields.Boolean(string="Report Ready Status", default=False)
    report_file = fields.Binary(string="Report File Data")
    report_name = fields.Char(string="Report File Name", default="Score_Summary_Report.xlsx")

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    # Auto-load students when source class is selected 
    @api.onchange('from_year_id', 'from_standard_id', 'from_div_id')
    def _onchange_from_fields(self):
        domain = [('is_student', '=', True)]
        if self.from_year_id:
            domain.append(('curr_year', '=', self.from_year_id.id))
        if self.from_standard_id:
            domain.append(('standard', '=', self.from_standard_id.id))
        if self.from_div_id:
            domain.append(('div', '=', self.from_div_id.id))
        students = self.env['res.partner'].search(domain)
        self.student_ids = [(6, 0, students.ids)]

    # Validate destination != source 
    @api.constrains('from_year_id', 'from_standard_id', 'from_div_id',
                    'to_year_id', 'to_standard_id', 'to_div_id')
    def _check_different_class(self):
        for rec in self:
            if (rec.from_year_id == rec.to_year_id and
                    rec.from_standard_id == rec.to_standard_id and
                    rec.from_div_id == rec.to_div_id):
                raise UserError(_(
                    'Source and destination class are the same. '
                    'Please select a different destination.'
                ))

    # Helper function to generate Excel byte stream
    def _generate_excel_report(self, students, from_yr, from_std, from_dv, to_yr, to_std, to_dv):
        output = io.BytesIO()
        workbook = openpyxl.Workbook() if openpyxl else None
        
        if workbook:
            sheet = workbook.active
            sheet.title = "Transfer Summary"
            headers = ["Student ID", "Student Name", "From Year", "From Standard", "From Division", "To Year", "To Standard", "To Division"]
            sheet.append(headers)
            
            for student in students:
                sheet.append([
                    student.id,
                    student.name or '',
                    from_yr,
                    from_std,
                    from_dv,
                    to_yr,
                    to_std,
                    to_dv
                ])
            workbook.save(output)
        else:
            output.write(b"ID,Name,From Year,From Standard,From Division,To Year,To Standard,To Division\n")
            for student in students:
                row = f"{student.id},{student.name},{from_yr},{from_std},{from_dv},{to_yr},{to_std},{to_dv}\n"
                output.write(row.encode('utf-8'))
                
        return base64.b64encode(output.getvalue())

    # Transfer action 
    def action_transfer(self):
        self.ensure_one()
        if not self.student_ids:
            raise UserError(_('No students found for the selected source class.'))

        old_standard = self.from_standard_id
        new_standard = self.to_standard_id

        for student in self.student_ids:
            self.env['student.history'].create({
                'student_id': student.id,
                'year_changed_from': self.from_year_id.id,
                'year_changed_to': self.to_year_id.id,
                'reason': 'Class Transfer: %s %s → %s %s' % (
                    self.from_standard_id.name or '',
                    self.from_div_id.name or '',
                    self.to_standard_id.name or '',
                    self.to_div_id.name or '',
                ),
            })

        f_yr, f_std, f_div = self.from_year_id.name, self.from_standard_id.name, self.from_div_id.name
        t_yr, t_std, t_div = self.to_year_id.name, self.to_standard_id.name, self.to_div_id.name
        report_data = self._generate_excel_report(self.student_ids, f_yr, f_std, f_div, t_yr, t_std, t_div)

        self.student_ids.write({
            'curr_year': self.to_year_id.id,
            'standard': self.to_standard_id.id,
            'div': self.to_div_id.id,
        })

        if hasattr(old_standard, '_compute_occupied_seats'):
            (old_standard | new_standard)._compute_occupied_seats()
        if hasattr(old_standard, '_compute_available_seats'):
            (old_standard | new_standard)._compute_available_seats()

        self.write({
            'download_report_ready': True,
            'report_file': report_data,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class StudentUpdateAllWizard(models.TransientModel):
    _name = 'student.update.all.wizard'
    _description = 'Update All Students Wizard'

    # Multi-select source filters
    filter_year_ids = fields.Many2many('year.year', 'rel_src_years', 'wiz_id', 'yr_id', string='Current Years (Filter)')
    filter_standard_ids = fields.Many2many('student.standard', 'rel_src_stds', 'wiz_id', 'std_id', string='Current Standards (Filter)')
    filter_div_ids = fields.Many2many('standard.division', 'rel_src_divs', 'wiz_id', 'div_id', string='Current Divisions (Filter)')

    # Target Destinations (Completely manual, no auto-compute setup)
    new_year_ids = fields.Many2many('year.year', 'rel_tgt_years', 'wiz_id', 'yr_id', string='Target Destination Years')
    new_standard_ids = fields.Many2many('student.standard', 'rel_tgt_stds', 'wiz_id', 'std_id', string='Target Destination Standards')
    new_div_ids = fields.Many2many('standard.division', 'rel_tgt_divs', 'wiz_id', 'div_id', string='Target Destination Divisions')

    student_count = fields.Integer(string='Students to Update', compute='_compute_student_count')
    download_report_ready = fields.Boolean(string="Report Ready Status", default=False)
    report_file = fields.Binary(string="Report File Data")
    report_name = fields.Char(string="Report File Name", default="Sequential_Promotion_Report.xlsx")

    @api.depends('filter_year_ids', 'filter_standard_ids', 'filter_div_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec._get_target_students())

    def _get_target_students(self):
        domain = [('is_student', '=', True)]
        if self.filter_year_ids:
            domain.append(('curr_year', 'in', self.filter_year_ids.ids))
        if self.filter_standard_ids:
            domain.append(('standard', 'in', self.filter_standard_ids.ids))
        if self.filter_div_ids:
            domain.append(('div', 'in', self.filter_div_ids.ids))
        return self.env['res.partner'].search(domain)

    def _is_next_sequence(self, model_name, current_record, target_record):
        """ Checks if target_record is exactly the next sequential step after current_record """
        if not current_record or not target_record:
            return False
        sort_field = 'sequence' if 'sequence' in self.env[model_name]._fields else 'id'
        current_val = getattr(current_record, sort_field)
        
        # Find what the true next sequence record should be
        next_rec = self.env[model_name].search([(sort_field, '>', current_val)], order=f"{sort_field} asc", limit=1)
        return next_rec and next_rec.id == target_record.id

    def action_update_all(self):
        self.ensure_one()
        
        if not self.new_year_ids or not self.new_standard_ids:
            raise UserError(_('Please manually select at least one Target Year and Target Standard.'))

        students = self._get_target_students()
        if not students:
            raise UserError(_('No student records found matching your active filter choices.'))

        old_standards = students.mapped('standard')
        output = io.BytesIO()
        workbook = openpyxl.Workbook() if openpyxl else None
        if workbook:
            sheet = workbook.active
            sheet.title = "Bulk Promotion Summary"
            sheet.append(["Student ID", "Student Name", "Old Year", "Old Standard", "Old Division", "New Year", "New Standard", "New Division"])

        records_updated = False

        for student in students:
            match_found = False
            target_year = None
            target_standard = None
            target_div = None

            # Loop through manual selections to see if any pair meets the exact +1 sequence rule
            for t_year in self.new_year_ids:
                if self._is_next_sequence('year.year', student.curr_year, t_year):
                    for t_std in self.new_standard_ids:
                        if self._is_next_sequence('student.standard', student.standard, t_std):
                            
                            # Division check: Match if selected in targets, otherwise fallback to their original division
                            if self.new_div_ids:
                                # Find if their old division name matches any manually selected target division
                                matching_div = self.new_div_ids.filtered(lambda d: d.name == student.div.name)
                                target_div = matching_div[0] if matching_div else self.new_div_ids[0]
                            else:
                                target_div = student.div
                            
                            target_year = t_year
                            target_standard = t_std
                            match_found = True
                            break
                if match_found:
                    break

            # If this specific student doesn't fit the +1 sequence of your manual targets, skip them
            if not match_found:
                continue

            records_updated = True

            if workbook:
                sheet.append([
                    student.id, student.name or '',
                    student.curr_year.name or '', student.standard.name or '', student.div.name or '',
                    target_year.name or '', target_standard.name or '', target_div.name or ''
                ])

            self.env['student.history'].create({
                'student_id': student.id,
                'year_changed_from': student.curr_year.id,
                'year_changed_to': target_year.id,
                'reason': 'Manual Promotion Sequence Verified (+1 Step): %s (%s) → %s (%s)' % (
                    student.curr_year.name or '', student.standard.name or '', 
                    target_year.name or '', target_standard.name or ''
                ),
            })

            # Commit the manual sequence advancement
            student.write({
                'curr_year': target_year.id,
                'standard': target_standard.id,
                'div': target_div.id if target_div else student.div.id,
            })

        if not records_updated:
            raise UserError(_('No records were updated. None of the filtered students matched an exact +1 sequence progression to your manually selected targets.'))

        # Recalculate seats tracking across all touched fields
        all_affected_standards = old_standards | students.mapped('standard')
        if hasattr(all_affected_standards, '_compute_occupied_seats'):
            all_affected_standards._compute_occupied_seats()

        if workbook:
            workbook.save(output)
            report_data = base64.b64encode(output.getvalue())
        else:
            report_data = base64.b64encode(b"Excel extraction libraries unavailable.")

        self.write({'download_report_ready': True, 'report_file': report_data})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }