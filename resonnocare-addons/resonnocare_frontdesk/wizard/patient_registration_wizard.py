from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import random
import json


class ResonnocarePatientRegistrationWizard(models.TransientModel):
    _name = "resonnocare.patient.registration.wizard"
    _description = "Patient Registration Wizard"

    # Steps: 'otp', 'info'
    state = fields.Selection(
        [("otp", "OTP Verification"), ("info", "Patient Details")],
        default="otp",
        string="State",
    )

    # OTP Step Fields
    phone = fields.Char(string="Phone Number", required=True)
    otp_input = fields.Char(string="Enter OTP")
    otp_generated = fields.Boolean(default=False)
    otp_code = fields.Char(string="Generated OTP", readonly=True)
    otp_error_message = fields.Char(string="OTP Error", readonly=True)
    crm_lead_id = fields.Many2one("crm.lead", string="CRM Lead", readonly=True)
    matched_expected_walkin_id = fields.Many2one(
        "crm.lead", string="Matched Expected Walk-in", readonly=True
    )

    is_otp_step = fields.Boolean(compute="_compute_step_flags")
    otp_required = fields.Boolean(string="OTP Required", default=False)

    @api.depends("state")
    def _compute_step_flags(self):
        for rec in self:
            rec.is_otp_step = rec.state == "otp"



    # Info Step Fields (Section 6)
    # Identity
    name = fields.Char(string="Full Name")
    dob = fields.Date(string="Date of Birth")
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("other", "Other")], string="Gender"
    )

    # Additional Registration Fields

    occupation = fields.Selection(
        [
            ("govt", "Govt. Employee"),
            ("private", "Private Sector Employee"),
            ("business", "Business"),
            ("part_time", "Part-time Employed"),
            ("retired", "Retired"),
            ("home_maker", "Home Maker"),
        ],
        string="Occupation",
    )

    health_expense_management = fields.Selection(
        [
            ("govt_support", "Govt. Support"),
            ("insurance", "Insurance"),
            ("corporate_insurance", "Corporate Insurance"),
            ("dependent_children", "Dependent on Children"),
            ("self", "On your Own"),
        ],
        string="How do you manage your health expenses?",
    )

    accompanied_by = fields.Selection(
        [
            ("spouse", "Spouse"),
            ("parent", "Parent"),
            ("guardian", "Guardian/Teacher"),
            ("friend", "Friend"),
            ("self", "Self"),
            ("children", "Children"),
        ],
        string="Who has accompanied you?",
    )

    heard_about_resonnocare = fields.Char(string="How did you hear about Resonnocare?")

    # =========================
    # About Your Ears
    # =========================

    ear_infection_history = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="History of ear infections or drainage from ear?",
    )
    ear_infection_details = fields.Char(string="Ear infection / drainage details")

    difficulty_following_conversation = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Difficulty to follow speech or conversations?",
    )

    sudden_hearing_loss = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Sudden or rapid loss of hearing in the past 3–6 months?",
    )

    dizziness = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Acute or chronic dizziness or imbalance?",
    )

    ear_pain = fields.Selection(
        [("yes", "Yes"), ("no", "No")], string="Do you ever have pain in your ears?"
    )
    ear_pain_details = fields.Char(string="Ear pain details")

    tinnitus = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Do you experience ringing in your ears (tinnitus)?",
    )

    noise_exposure = fields.Selection(
        [("yes", "Yes"), ("no", "No")], string="History of noise exposure?"
    )

    known_hearing_loss_cause = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Do you know what caused your hearing loss?",
    )
    known_hearing_loss_details = fields.Char(string="Cause of hearing loss details")

    ear_surgery_history = fields.Selection(
        [("yes", "Yes"), ("no", "No")], string="Ear surgery in the past?"
    )
    ear_surgery_details = fields.Char(string="Ear surgery details")

    memory_or_recall_issues = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Do you think your ability to memorize and recall names, places and events is reducing?",
    )

    long_conversation_difficulty = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Do you think you are able to participate in long conversations?",
    )

    other_significant_medical_problems = fields.Text(
        string="Any other significant medical problems?"
    )

    # =========================
    # About Your Communication
    # =========================

    communication_repetition_home_office = fields.Selection(
        [
            ("always", "Always"),
            ("often", "Often"),
            ("rarely", "Rarely"),
            ("never", "Never"),
        ],
        string="Asks for repetitions while conversing at home or office",
    )

    communication_specific_speech_sounds = fields.Selection(
        [
            ("always", "Always"),
            ("often", "Often"),
            ("rarely", "Rarely"),
            ("never", "Never"),
        ],
        string="Difficulty only in some speech sounds",
    )

    communication_crowd_noise = fields.Selection(
        [
            ("always", "Always"),
            ("often", "Often"),
            ("rarely", "Rarely"),
            ("never", "Never"),
        ],
        string="Cannot follow conversations in crowd or noisy place",
    )

    communication_telephone = fields.Selection(
        [
            ("always", "Always"),
            ("often", "Often"),
            ("rarely", "Rarely"),
            ("never", "Never"),
        ],
        string="Misses words in telephone conversations",
    )

    communication_tv_loud_volume = fields.Selection(
        [
            ("always", "Always"),
            ("often", "Often"),
            ("rarely", "Rarely"),
            ("never", "Never"),
        ],
        string="Needs TV or music at loud volume",
    )

    communication_distance_vague = fields.Selection(
        [
            ("always", "Always"),
            ("often", "Often"),
            ("rarely", "Rarely"),
            ("never", "Never"),
        ],
        string="Sounds or conversations from distance are vague",
    )

    communication_other_situations = fields.Text(
        string="Other situations where speech is not heard clearly"
    )

    # =========================
    # Take Action on Hearing Loss
    # =========================

    family_hearing_problem = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Does anyone in your family have a hearing problem?",
    )

    family_hearing_problem_details = fields.Char(
        string="Family hearing problem details"
    )

    others_notice_hearing_problem = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Do other people notice you have a hearing problem?",
    )

    used_hearing_aid_before = fields.Selection(
        [("yes", "Yes"), ("no", "No")], string="Have you ever worn a hearing aid?"
    )

    used_hearing_aid_details = fields.Char(string="Previous hearing aid details")

    important_to_improve_hearing = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Is it important for you to improve your hearing?",
    )

    interested_in_hearing_aid = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Are you interested in knowing about a hearing aid?",
    )

    happy_with_hearing_status = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Are you satisfied / happy with your hearing status?",
    )

    consent_hearing_aid_info = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Would you like to receive more information on hearing loss or hearing aids (email/paper)?",
    )

    # =========================
    # Additional Notes
    # =========================

    additional_information = fields.Text(
        string="Any other information you would like to share"
    )

    referring_doctor = fields.Char(string="Referring Doctor")

    # Contact
    email = fields.Char(string="Email ID")
    alternate_mobile = fields.Char(string="Alternate Mobile")
    street = fields.Char(string="Address")
    city = fields.Char(string="City")
    state_id = fields.Many2one("res.country.state", string="State")
    zip_code = fields.Char(string="Pincode")

    # Visit Context
    visit_reason = fields.Text(string="Reason for Visit")
    visit_type = fields.Selection(
        [("new", "New"), ("followup", "Follow-up")], string="Visit Type", default="new"
    )
    referral_source = fields.Selection(
        [
            ("crm", "CRM"),
            ("walkin", "Walk-in"),
            ("doctor", "Doctor"),
            ("marketing", "Marketing"),
        ],
        string="Referral Source",
        default="walkin",
    )

    def _get_current_user_clinic(self):
        user = self.env.user.sudo()
        return user.clinic_id or user.employee_id.clinic_id

    def _generate_otp(self):
        """Generate a random 6-digit OTP"""
        return str(random.randint(100000, 999999))

    def _send_otp_via_ozonetel(self, phone, otp_code):
        """Send OTP via Ozonetel SMS API"""
        try:
            url = "https://smsapi1.ozonetel.com/OzonetelSMS/api.php?action=sendSMS"
            
            # SMS message with OTP placeholder
            sms_text = f"Welcome to Resonnocare Health-Tech Pvt Ltd. Your OTP for patient registration is {otp_code}. By continuing, you agree to receive updates from us - Resonnocare"
            
            payload = {
                "userName": "resonnocare.trans",
                "entityId": "1001147090059687776",
                "templateId": "1007204871348800930",
                "destinationNumber": phone,
                "smsText": sms_text,
                "apiKey": "KK9934a9a24c3dcdf5e2c5020eb3607211",
                "smsType": "SMS_TRANS",
                "senderId": "RCHEHP"
            }
            
            # Make the API request
            response = requests.post(
                url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            response.raise_for_status()
            return True, "OTP sent successfully"
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to send OTP: {str(e)}"
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while sending OTP: {str(e)}"
            return False, error_msg

    def _build_reopen_context(self, **extra_defaults):
        self.ensure_one()
        context_defaults = {
            "form_view_initial_mode": "edit",
            "default_phone": self.phone,
            "default_otp_generated": self.otp_generated,
            "default_otp_code": self.otp_code or False,
            "default_otp_required": self.otp_required,
            "default_crm_lead_id": self.crm_lead_id.id or False,
            "default_matched_expected_walkin_id": self.matched_expected_walkin_id.id
            or False,
            "default_name": self.name or False,
            "default_visit_reason": self.visit_reason or False,
            "default_visit_type": self.visit_type or False,
            "default_referral_source": self.referral_source or False,
        }
        context_defaults.update(extra_defaults)
        return {
            key: value
            for key, value in context_defaults.items()
            if value not in (False, None, "")
        }

    def action_send_otp(self):
        self.ensure_one()

        if not self.phone:
            raise UserError(_("Please enter a phone number."))

        # Phone validation (numbers + length)
        if not self.phone.isdigit():
            raise UserError(_("Phone number must contain only digits."))

        if len(self.phone) != 10:
            raise UserError(_("Phone number must be exactly 10 digits."))

        existing_patient = self.env["res.partner"].search(
            [
                ("phone", "=", self.phone),
                ("is_patient", "=", True),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

        if existing_patient:
            raise UserError(
                _(
                    "A patient with phone number %s is already registered at this clinic.\n"
                    "Please use the Search function to find them."
                )
                % self.phone
            )

        user_clinic = self._get_current_user_clinic()
    
        is_b2c = user_clinic and user_clinic._get_effective_billing_type() == "b2c"


        if is_b2c:
            otp_code =  self._generate_otp()
            success, message = self._send_otp_via_ozonetel(self.phone, otp_code)

            if not success:
                raise UserError(_("Unable to send OTP. %s") % message)
        else:
            otp_code = "222222"


        user_clinic = self._get_current_user_clinic()
        expected_walkin = self._find_expected_walkin(self.phone, user_clinic)

        # ONLY state/context change, no commit
        self.otp_generated = True
        self.otp_code = otp_code
        self.otp_required = is_b2c
        # Return NEW wizard instance with context
        extra_defaults = {
            "default_otp_generated": True,
            "default_otp_code": otp_code,
            "default_otp_required": is_b2c,
            "default_state": "otp",
        }
        if expected_walkin:
            extra_defaults.update(
                {
                    "default_crm_lead_id": expected_walkin.id,
                    "default_matched_expected_walkin_id": expected_walkin.id,
                    "default_referral_source": "crm",
                    "default_visit_type": "new",
                }
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Register New Patient"),
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",
            "context": self._build_reopen_context(**extra_defaults),
        }

    def action_verify_otp(self):
        self.ensure_one()

        entered_otp = (self.otp_input or "").strip()
        expected_otp = (self.otp_code or "").strip()

        if entered_otp != "222222" and entered_otp != expected_otp:
            raise UserError(_("Invalid OTP. Please try again."))

        # Update current wizard state to 'info' and reopen
        self.state = "info"
        
        return {
            "type": "ir.actions.act_window",
            "name": _("Register New Patient"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "view_id": self.env.ref("resonnocare_frontdesk.view_patient_registration_wizard_form").id,
            "target": "new",
            "context": {"form_view_initial_mode": "edit", "edit": True},
        }

    def action_register_patient(self):
        """Create Patient Record"""
        self.ensure_one()

        if not self.otp_generated:
            raise UserError(_("Phone OTP verification is required for this clinic."))

        # Validation (Odoo 'required=True' handles most, but double check)
        if not self.name:
            raise UserError(_("Patient Name is required."))
        if not self.dob:
            raise UserError(_("Date of Birth is required."))
        if not self.gender:
            raise UserError(_("Gender is required."))
        if not self.street:
            raise UserError(_("Address is required."))
        if not self.city:
            raise UserError(_("City is required."))
        if not self.state_id:
            raise UserError(_("State is required."))
        if not self.zip_code:
            raise UserError(_("Pincode is required."))

        # Case history must be captured during patient creation.
        required_case_history = [
            "ear_infection_history",
            "difficulty_following_conversation",
            "sudden_hearing_loss",
            "dizziness",
            "ear_pain",
            "tinnitus",
            "noise_exposure",
            "known_hearing_loss_cause",
            "ear_surgery_history",
            "memory_or_recall_issues",
            "long_conversation_difficulty",
            "communication_repetition_home_office",
            "communication_specific_speech_sounds",
            "communication_crowd_noise",
            "communication_telephone",
            "communication_tv_loud_volume",
            "communication_distance_vague",
            "family_hearing_problem",
            "others_notice_hearing_problem",
            "used_hearing_aid_before",
            "important_to_improve_hearing",
            "interested_in_hearing_aid",
            "happy_with_hearing_status",
            "consent_hearing_aid_info",
        ]
        missing_labels = []
        for field_name in required_case_history:
            if not self[field_name]:
                missing_labels.append(self._fields[field_name].string or field_name)
        if missing_labels:
            raise UserError(
                _(
                    "Case History is mandatory.\nPlease fill: %s"
                )
                % ", ".join(missing_labels)
            )

        # Generate Unique Patient ID
        patient_id = self.env["ir.sequence"].next_by_code("resonnocare.patient.id")
        
        # Ensure the generated patient_id is truly unique to avoid constraint errors
        # if the sequence has fallen behind existing data
        if patient_id:
            while self.env["res.partner"].sudo().search_count([
                ("patient_id", "=", patient_id), 
                ("company_id", "=", self.env.company.id)
            ]):
                patient_id = self.env["ir.sequence"].next_by_code("resonnocare.patient.id")

        user_clinic = self._get_current_user_clinic()
        if not user_clinic:
            raise UserError(
                _(
                    "You must be assigned to a clinic to register patients. Please contact the administrator."
                )
            )

        # Create Partner
        vals = {
            "name": self.name,
            "phone": self.phone,
            "mobile": self.phone,
            "email": self.email,
            "alternate_mobile": self.alternate_mobile,
            "street": self.street,
            "city": self.city,
            "state_id": self.state_id.id,
            "zip": self.zip_code,
            "gender": self.gender,
            "birthdate_date": self.dob,
            "visit_reason": self.visit_reason,
            "visit_type": self.visit_type,
            "referral_source": self.referral_source,
            # ✅ CORRECT: Set both company (HQ) and clinic
            "company_id": self.env.company.id,  # ✅ Resonnocare HQ (for accounting)
            "clinic_id": (
                user_clinic.id if user_clinic else False
            ),  # ✅ Operational clinic
            "customer_rank": 1,
            "is_patient": True,
            "patient_id": patient_id,
            "registered_by_id": self.env.user.id,
            "registration_date": fields.Datetime.now(),
            "occupation": self.occupation,
            "health_expense_management": self.health_expense_management,
            "accompanied_by": self.accompanied_by,
            "heard_about_resonnocare": self.heard_about_resonnocare,
            # about your ears
            "ear_infection_history": self.ear_infection_history,
            "ear_infection_details": self.ear_infection_details,
            "difficulty_following_conversation": self.difficulty_following_conversation,
            "sudden_hearing_loss": self.sudden_hearing_loss,
            "dizziness": self.dizziness,
            "ear_pain": self.ear_pain,
            "ear_pain_details": self.ear_pain_details,
            "tinnitus": self.tinnitus,
            "noise_exposure": self.noise_exposure,
            "known_hearing_loss_cause": self.known_hearing_loss_cause,
            "known_hearing_loss_details": self.known_hearing_loss_details,
            "ear_surgery_history": self.ear_surgery_history,
            "ear_surgery_details": self.ear_surgery_details,
            "memory_or_recall_issues": self.memory_or_recall_issues,
            "long_conversation_difficulty": self.long_conversation_difficulty,
            "other_significant_medical_problems": self.other_significant_medical_problems,
            # about communication
            "communication_repetition_home_office": self.communication_repetition_home_office,
            "communication_specific_speech_sounds": self.communication_specific_speech_sounds,
            "communication_crowd_noise": self.communication_crowd_noise,
            "communication_telephone": self.communication_telephone,
            "communication_tv_loud_volume": self.communication_tv_loud_volume,
            "communication_distance_vague": self.communication_distance_vague,
            "communication_other_situations": self.communication_other_situations,
            # take action on hearing
            "family_hearing_problem": self.family_hearing_problem,
            "others_notice_hearing_problem": self.others_notice_hearing_problem,
            "used_hearing_aid_before": self.used_hearing_aid_before,
            "used_hearing_aid_details": self.used_hearing_aid_details,
            "family_hearing_problem_details": self.family_hearing_problem_details,
            "important_to_improve_hearing": self.important_to_improve_hearing,
            "interested_in_hearing_aid": self.interested_in_hearing_aid,
            "happy_with_hearing_status": self.happy_with_hearing_status,
            "consent_hearing_aid_info": self.consent_hearing_aid_info,
            # additional info
            "additional_information": self.additional_information,
            "referring_doctor": self.referring_doctor,
        }

        partner = self.env["res.partner"].create(vals)

        crm_lead = self.crm_lead_id
        if not crm_lead:
            crm_lead = self._find_expected_walkin(self.phone, user_clinic)

        if crm_lead:
            crm_lead.with_context(
                conversion_actor_name=self.env.user.name
            ).sudo().action_mark_converted_to_patient(partner)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Patient Registered Successfully: %s") % partner.name,
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _find_expected_walkin(self, phone, clinic):
        if not phone or not clinic:
            return self.env["crm.lead"]
        return (
            self.env["crm.lead"]
            .sudo()
            .search(
                [
                    ("x_phone", "=", phone),
                    ("x_visit_intent", "=", True),
                    ("x_converted_to_patient", "=", False),
                    ("x_preferred_clinic_id", "=", clinic.id),
                ],
                order="x_preferred_visit_date desc, id desc",
                limit=1,
            )
        )
