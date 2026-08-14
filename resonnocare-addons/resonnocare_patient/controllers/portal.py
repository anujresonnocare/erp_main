# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ResonnocarePatientPortal(CustomerPortal):
    _SYSTEM_FIELDS = {
        "id",
        "display_name",
        "__last_update",
        "create_uid",
        "create_date",
        "write_uid",
        "write_date",
        "message_is_follower",
        "message_follower_ids",
        "message_partner_ids",
        "message_ids",
        "message_attachment_count",
        "activity_ids",
        "activity_state",
        "activity_exception_decoration",
        "activity_exception_icon",
        "activity_user_id",
        "activity_type_icon",
        "activity_date_deadline",
        "activity_summary",
        "activity_type_id",
        "activity_exception_icon",
        "activity_calendar_event_id",
        "website_message_ids",
    }

    def _get_current_patient_partner(self):
        partner = request.env.user.partner_id
        if partner.is_patient:
            return partner
        if partner.parent_id and partner.parent_id.is_patient:
            return partner.parent_id
        return request.env["res.partner"]

    def _format_field_value(self, record, field_name, field_info):
        value = record[field_name]
        field_type = field_info["type"]
        if field_type == "many2one":
            return value.display_name if value else "-"
        if field_type in ("many2many", "one2many"):
            if not value:
                return "-"
            names = [self._format_rel_record(rec) for rec in value]
            names = [n for n in names if n]
            if len(names) > 20:
                return ", ".join(names[:20]) + "..."
            return ", ".join(names)
        if field_type == "selection":
            selection_map = dict(field_info.get("selection") or [])
            return selection_map.get(value, value) if value else "-"
        if field_type == "boolean":
            return "Yes" if value else "No"
        return value if value not in (False, None, "") else "-"

    def _format_rel_record(self, rec):
        if "product_id" in rec._fields:
            product = rec["product_id"].display_name if rec["product_id"] else "-"
            qty = "-"
            if "product_uom_qty" in rec._fields:
                qty = rec["product_uom_qty"]
            elif "quantity" in rec._fields:
                qty = rec["quantity"]
            return f"{product} x {qty}"
        if "appointment_id" in rec._fields and "appointment_date" in rec._fields:
            appt = rec["appointment_id"] or rec.display_name
            date = rec["appointment_date"] or "-"
            return f"{appt} ({date})"
        return rec.display_name

    def _patient_profile_fields(self):
        return [
            "patient_id",
            "name",
            "gender",
            "birthdate_date",
            "clinic_id",
            "phone",
            "alternate_mobile",
            "email",
            "street",
            "city",
            "state_id",
            "zip",
            "visit_type",
            "referral_source",
            "visit_reason",
            "occupation",
            "health_expense_management",
            "accompanied_by",
            "heard_about_resonnocare",
            "ear_infection_history",
            "ear_infection_details",
            "difficulty_following_conversation",
            "sudden_hearing_loss",
            "dizziness",
            "ear_pain",
            "ear_pain_details",
            "tinnitus",
            "noise_exposure",
            "known_hearing_loss_cause",
            "known_hearing_loss_details",
            "ear_surgery_history",
            "ear_surgery_details",
            "memory_or_recall_issues",
            "long_conversation_difficulty",
            "other_significant_medical_problems",
            "communication_repetition_home_office",
            "communication_specific_speech_sounds",
            "communication_crowd_noise",
            "communication_telephone",
            "communication_tv_loud_volume",
            "communication_distance_vague",
            "communication_other_situations",
            "family_hearing_problem",
            "family_hearing_problem_details",
            "others_notice_hearing_problem",
            "used_hearing_aid_before",
            "used_hearing_aid_details",
            "important_to_improve_hearing",
            "interested_in_hearing_aid",
            "happy_with_hearing_status",
            "consent_hearing_aid_info",
            "additional_information",
            "referring_doctor",
        ]

    def _appointment_detail_fields(self):
        return [
            "status",
            "patient_id",
            "clinic_id",
            "appointment_id",
            "source",
            "parent_appointment_id",
            "appointment_role",
            "balance_due",
            "appointment_type_id",
            "appointment_date",
            "appointment_start_time",
            "appointment_end_time",
            "doctor_name",
            "audiologist_id",
            "technician_id",
            "sale_type",
            "diagnostic_item_ids",
            "device_sale_line_ids",
            "fitting_device_line_ids",
            "notes",
            "appointment_outcome_ids",
            "fitting_appointment_ids",
            "sale_order_id",
            "is_billed",
        ]

    def _should_include_field(self, record, name):
        # Match the same conditional visibility used in patient form.
        if name == "ear_infection_details":
            return record.ear_infection_history == "yes"
        if name == "ear_pain_details":
            return record.ear_pain == "yes"
        if name == "known_hearing_loss_details":
            return record.known_hearing_loss_cause == "yes"
        if name == "ear_surgery_details":
            return record.ear_surgery_history == "yes"
        if name == "family_hearing_problem_details":
            return record.family_hearing_problem == "yes"
        if name == "used_hearing_aid_details":
            return record.used_hearing_aid_before == "yes"
        return True

    def _serialize_record_for_portal(self, record, field_names=None):
        rows = []
        fields_meta = record.fields_get()
        selected_fields = field_names or list(fields_meta.keys())
        for name in selected_fields:
            info = fields_meta.get(name)
            if not info:
                continue
            if not self._should_include_field(record, name):
                continue
            if name in self._SYSTEM_FIELDS:
                continue
            if name.startswith("message_") or name.startswith("activity_"):
                continue
            if info.get("type") == "binary":
                continue
            label = info.get("string") or name
            try:
                value = self._format_field_value(record, name, info)
            except Exception:
                continue
            if value == "-":
                continue
            rows.append({"label": label, "value": value})
        return rows

    def _get_patient_appointment_domain(self):
        patient = self._get_current_patient_partner()
        if not patient:
            return [("id", "=", 0)]
        return [("patient_id", "=", patient.id)]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        # Hide generic sales/account portal cards for patient portal users.
        values.update(
            {
                "quotation_count": 0,
                "order_count": 0,
                "invoice_count": 0,
                "bill_count": 0,
            }
        )
        if "appointment_count" in counters:
            values["appointment_count"] = request.env["resonnocare.appointment"].search_count(
                self._get_patient_appointment_domain()
            )
        return values

    @http.route(["/my/profile"], type="http", auth="user", website=True)
    def portal_my_profile(self, **post):
        patient = self._get_current_patient_partner().sudo()
        if not patient:
            return request.redirect("/my")

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "patient_profile",
                "patient": patient,
                "profile_rows": self._serialize_record_for_portal(
                    patient, self._patient_profile_fields()
                ),
            }
        )

        return request.render("resonnocare_patient.portal_my_profile", values)

    @http.route(["/my/account"], type="http", auth="user", website=True)
    def portal_my_account_redirect(self, **kw):
        return request.redirect("/my/profile")

    @http.route(
        ["/my/appointments", "/my/appointments/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_appointments(self, page=1, **kw):
        appointment_model = request.env["resonnocare.appointment"]
        domain = self._get_patient_appointment_domain()

        total = appointment_model.search_count(domain)
        pager = portal_pager(url="/my/appointments", total=total, page=page, step=20)
        appointment_ids = appointment_model.search(
            domain,
            order="appointment_date desc, appointment_start_time desc, id desc",
            limit=20,
            offset=pager["offset"],
        ).ids
        appointments = appointment_model.sudo().browse(appointment_ids)

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "appointments",
                "appointments": appointments,
                "pager": pager,
                "default_url": "/my/appointments",
            }
        )
        return request.render("resonnocare_patient.portal_my_appointments", values)

    @http.route(
        ["/my/appointments/<int:appointment_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_appointment_detail(self, appointment_id, **kw):
        appointment = request.env["resonnocare.appointment"].search(
            [("id", "=", appointment_id)] + self._get_patient_appointment_domain(),
            limit=1,
        )
        if not appointment:
            return request.redirect("/my/appointments")
        appointment = appointment.sudo()

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "appointment_detail",
                "appointment": appointment,
                "appointment_rows": self._serialize_record_for_portal(
                    appointment, self._appointment_detail_fields()
                ),
            }
        )
        return request.render("resonnocare_patient.portal_appointment_detail", values)

    @http.route(
        ["/my/audiometry-results", "/my/audiometry-results/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_audiometry_results(self, page=1, **kw):
        patient = self._get_current_patient_partner().sudo()
        if not patient or not patient.id:
            return request.redirect("/my")

        model = request.env["resonnocare.audiometry.result"].sudo()
        domain = [("patient_id", "=", patient.id)]
        total = model.search_count(domain)
        pager = portal_pager(url="/my/audiometry-results", total=total, page=page, step=20)
        result_ids = model.search(
            domain,
            order="created_at desc, id desc",
            limit=20,
            offset=pager["offset"],
        ).ids
        results = model.sudo().browse(result_ids)

        # build download base url
        try:
            base = (request.httprequest.host_url or "").rstrip("/")
        except Exception:
            base = ""

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "audiometry_results",
                "audiometry_results": results,
                "pager": pager,
                "default_url": "/my/audiometry-results",
                "download_base": base + "/api/tests/audiometry-results/download-file?uid=",
            }
        )
        return request.render("resonnocare_patient.portal_my_audiometry_results", values)

    @http.route(["/my/audiometry-results/<string:uid>"], type="http", auth="user", website=True)
    def portal_audiometry_result_detail(self, uid, **kw):
        patient = self._get_current_patient_partner().sudo()
        if not patient or not patient.id:
            return request.redirect("/my")

        rec = request.env["resonnocare.audiometry.result"].sudo().search([("uid", "=", uid), ("patient_id", "=", patient.id)], limit=1)
        if not rec:
            return request.redirect("/my/audiometry-results")

        # prepare attachments list with download URLs
        attachments = (
            request.env["ir.attachment"].sudo().search([
                ("res_model", "=", "resonnocare.audiometry.result"),
                ("res_id", "=", rec.id),
            ])
        )
        try:
            base = (request.httprequest.host_url or "").rstrip("/")
            download_base = base + "/api/tests/audiometry-results/download-file?uid="
        except Exception:
            download_base = "/api/tests/audiometry-results/download-file?uid="

        attach_list = []
        for a in attachments:
            attach_list.append({
                "id": a.id,
                "name": getattr(a, "name", ""),
                "mimetype": getattr(a, "mimetype", ""),
                "url": download_base + rec.uid,
            })

        values = self._prepare_portal_layout_values()
        values.update({"page_name": "audiometry_result_detail", "result": rec, "attachments": attach_list})
        return request.render("resonnocare_patient.portal_audiometry_result_detail", values)
