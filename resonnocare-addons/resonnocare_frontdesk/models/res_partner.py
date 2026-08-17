from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    _CASE_HISTORY_REQUIRED_FIELDS = [
        # About your ears
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
        # About communication
        "communication_repetition_home_office",
        "communication_specific_speech_sounds",
        "communication_crowd_noise",
        "communication_telephone",
        "communication_tv_loud_volume",
        "communication_distance_vague",
        # Take action on hearing
        "family_hearing_problem",
        "others_notice_hearing_problem",
        "used_hearing_aid_before",
        "important_to_improve_hearing",
        "interested_in_hearing_aid",
        "happy_with_hearing_status",
        "consent_hearing_aid_info",
    ]

    is_patient = fields.Boolean(default=False, index=True)

    patient_id = fields.Char(string="Patient ID", readonly=True, index=True)

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Home Clinic",
        help="The clinic this patient is registered with",
        index=True,
    )

    registration_date = fields.Datetime(default=fields.Datetime.now, readonly=True)

    registered_by_id = fields.Many2one("res.users", readonly=True)

    alternate_mobile = fields.Char(string="Alternate Mobile")

    # Occupation
    occupation = fields.Selection(
        [
            ("govt", "Govt. Employee"),
            ("private", "Private Sector Employee"),
            ("business", "Business"),
            ("part_time", "Part-time Employed"),
            ("student", "Student"),
            ("retired", "Retired"),
            ("home_maker", "Home Maker"),
        ],
        string="Occupation",
    )

    # Health Expense Management
    health_expense_management = fields.Selection(
        [
            ("govt_support", "Govt. Support"),
            ("insurance", "Insurance"),
            ("corporate_insurance", "Corporate Insurance"),
            ("dependent_children", "Dependent on Children"),
            ("self", "On your Own"),
        ],
        string="Health Expense Management",
    )

    # Who has accompanied you
    accompanied_by = fields.Selection(
        [
            ("spouse", "Spouse"),
            ("parent", "Parent"),
            ("guardian", "Guardian/Teacher"),
            ("friend", "Friend"),
            ("self", "Self"),
            ("children", "Children"),
        ],
        string="Accompanied By",
    )

    # Marketing Source (free text)
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

    visit_reason = fields.Text()
    visit_type = fields.Selection([("new", "New"), ("followup", "Follow-up")])

    referral_source = fields.Selection(
        [
            ("crm", "CRM"),
            ("walkin", "Walk-in"),
            ("doctor", "Doctor"),
            ("marketing", "Marketing"),
            ("website", "Website"),
            ("hear_com", "hear.com"),
        ]
    )

    # Identity
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("other", "Other")], string="Gender"
    )

    birthdate_date = fields.Date(string="Date of Birth")

    _sql_constraints = [
        (
            "unique_patient_id_per_clinic",
            "unique(patient_id, company_id)",
            "A patient with this unique ID already exists for this clinic.",
        )
    ]

    @staticmethod
    def _normalize_phone_digits(number):
        return "".join(ch for ch in (number or "") if ch.isdigit())

    @classmethod
    def _is_valid_indian_mobile(cls, number):
        digits = cls._normalize_phone_digits(number)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return len(digits) == 10 and digits[0] in "6789"

    @classmethod
    def _is_valid_phone_general(cls, number):
        digits = cls._normalize_phone_digits(number)
        return 10 <= len(digits) <= 15

    @api.constrains("phone", "mobile", "alternate_mobile")
    def _check_phone_number_format(self):
        for rec in self:
            if rec.phone and not self._is_valid_phone_general(rec.phone):
                raise ValidationError(
                    "Phone number must contain 10 to 15 digits."
                )
            if rec.mobile and not self._is_valid_indian_mobile(rec.mobile):
                raise ValidationError(
                    "Mobile number must be a valid 10-digit Indian mobile number."
                )
            if rec.alternate_mobile and not self._is_valid_indian_mobile(
                rec.alternate_mobile
            ):
                raise ValidationError(
                    "Alternate Mobile must be a valid 10-digit Indian mobile number."
                )

    def _get_missing_case_history_labels(self):
        self.ensure_one()
        missing = []
        for field_name in self._CASE_HISTORY_REQUIRED_FIELDS:
            if not self[field_name]:
                missing.append(self._fields[field_name].string or field_name)
        return missing

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records.filtered(lambda r: r.is_patient):
            missing = rec._get_missing_case_history_labels()
            if missing:
                raise ValidationError(
                    "Case History is mandatory for patient creation.\n"
                    "Please fill: %s" % ", ".join(missing)
                )
        return records
