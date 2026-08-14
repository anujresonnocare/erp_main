# -*- coding: utf-8 -*-

import json
import logging
import base64
import uuid
import random
import requests
import hashlib
import hmac
import ssl
from datetime import datetime
try:
    from urllib3.poolmanager import PoolManager
except ImportError:
    try:
        from requests.packages.urllib3.poolmanager import PoolManager
    except ImportError:
        PoolManager = None
from requests.adapters import HTTPAdapter

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TLSAdapter(HTTPAdapter):
    """Transport adapter that enforces TLSv1.2 or higher."""
    def init_poolmanager(self, connections, maxsize, block=False):
        if PoolManager is None:
            _logger.warning("PoolManager is not available. Using default HTTPAdapter pool manager.")
            return super().init_poolmanager(connections, maxsize, block=block)
        
        # Create standard context enforcing TLS 1.2+
        context = ssl.create_default_context()
        if hasattr(ssl, "TLSVersion"):
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        else:
            # Fallback for older python versions
            context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=context
        )




class ResonnocareIntegrationAPI(http.Controller):
    def __init__(self):
        _logger.info("🔴 ResonnocareIntegrationAPI Controller Initialized!")
        super().__init__()


    def _json_response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload),
            headers=[("Content-Type", "application/json")],
            status=status,
        )

    def _check_api_key(self):
        """Optional API key check.
        If `resonnocare.integration_api_key` is set, caller must pass same value
        in `X-API-Key` header.
        """
        expected = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("resonnocare.integration_api_key")
            or ""
        ).strip()
        if not expected:
            return True
        supplied = (request.httprequest.headers.get("X-API-Key") or "").strip()
        return supplied == expected

    def _split_name(self, full_name):
        full_name = (full_name or "").strip()
        if not full_name:
            return "", ""
        parts = full_name.split()
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    def _format_gender(self, gender):
        mapping = {
            "male": "M",
            "female": "F",
            "other": "O",
            "m": "M",
            "f": "F",
        }
        return mapping.get((gender or "").strip().lower(), "")

  

    @http.route(
        "/api/SetUpCenter/CentreCode",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        cors="*"
    )
    def setup_center_code(self, **kwargs):
        try:
            if not self._check_api_key():
                return self._json_response(
                    {"status": False, "message": "Unauthorized API access."},
                    status=401,
                )

            centre_code = (kwargs.get("CentreCode") or "").strip()
            if not centre_code:
                return self._json_response(
                    {"status": False, "message": "CentreCode is required."},
                    status=400,
                )

            clinic = (
                request.env["resonnocare.clinic"]
                .sudo()
                .search([("clinic_code", "=", centre_code)], limit=1)
            )
            if not clinic:
                return self._json_response(
                    {"status": False, "message": "Invalid Centre Code."},
                    status=404,
                )
            
            # if clinic.clinic_status and clinic.clinic_status.lower() != "active":
                # return self._json_response(
                #     {"status": False, "message": "Centre code already registered."},
                #     status=409,
                # )
            


            payload = {
                "status": True,
                "message": "Centre Code validated successfully.",
                "data": {
                    "CentreCode": clinic.clinic_code or "",
                    "CentreName": clinic.name or  clinic.street2,
                    "Address": clinic.street or "",
                    "City": clinic.city or "",
                    "State": clinic.state_id.name or "",
                    "Country": clinic.country_id.name or "",
                    "ZipCode": clinic.zip or "",
                    # "Status": (clinic.clinic_status or "").capitalize() or "Active",
                },
            }
            return self._json_response(payload, status=200)
        except Exception as err:
            _logger.exception("SetUpCenter/CentreCode API error")
            return self._json_response(
                {
                    "status": False,
                    "message": "An unexpected error occurred.",
                    "error": str(err),
                },
                status=500,
            )

    @http.route(
        "/api/patientlist/CentreCode",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        cors="*"
    )
    def patient_list_by_centre(self, **kwargs):
        try:
            if not self._check_api_key():
                return self._json_response(
                    {"status": False, "message": "Unauthorized API access."},
                    status=401,
                )

            centre_code = (kwargs.get("CentreCode") or "").strip()
            if not centre_code:
                return self._json_response(
                    {"status": False, "message": "CentreCode is required."},
                    status=400,
                )

            clinic = (
                request.env["resonnocare.clinic"]
                .sudo()
                .search([("clinic_code", "=", centre_code)], limit=1)
            )
            if not clinic:
                return self._json_response(
                    {"status": False, "message": "Invalid Centre Code."},
                    status=404,
                )

            appointments = (
                request.env["resonnocare.appointment"]
                .sudo()
                .search(
                    [
                        ("clinic_id", "=", clinic.id),
                        ("patient_id", "!=", False),
                        ("status", "!=", "cancelled"),
                    ],
                    order="appointment_date desc, id desc",
                )
            )

            seen = set()
            data = []
            for appt in appointments:
                patient = appt.patient_id
                if not patient or patient.id in seen:
                    continue
                seen.add(patient.id)
                first_name, last_name = self._split_name(patient.name)
                dob = patient.birthdate_date
                dob_str = (
                    fields.Date.to_date(dob).strftime("%Y-%m-%d")
                    if dob
                    else ""
                )
                data.append(
                    {
                        "PatientId": patient.patient_id or str(patient.id),
                        "FirstName": first_name,
                        "LastName": last_name,
                        "DateOfBirth": dob_str,
                        "Gender": self._format_gender(patient.gender),
                    }
                )

            if not data:
                return self._json_response(
                    {
                        "status": False,
                        "message": "No patients found for the given Centre Code.",
                    },
                    status=404,
                )

            return self._json_response(
                {
                    "status": True,
                    "message": "Patient list retrieved successfully.",
                    "data": data,
                },
                status=200,
            )
        except Exception as err:
            _logger.exception("patientlist/CentreCode API error")
            return self._json_response(
                {
                    "status": False,
                    "message": "An unexpected error occurred.",
                    "error": str(err),
                },
                status=500,
            )

    @http.route(
        "/api/tests/audiometry-results",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def save_audiometry_results(self, **kwargs):
        """Save Audiometry test results"""
        try:
            if not self._check_api_key():
                return self._json_response(
                    {"success": False, "error": "Unauthorized API access."},
                    status=401,
                )

            # Parse JSON body
            try:
                data = json.loads(request.httprequest.data.decode("utf-8"))
            except Exception as e:
                return self._json_response(
                    {
                        "success": False,
                        "error": f"Invalid JSON body: {str(e)}",
                    },
                    status=400,
                )

            # Validate required fields
            session_id = (data.get("sessionId") or "").strip()
            patient_id = (data.get("patientId") or "").strip()
            centre_code = (data.get("centreCode") or "").strip()
            test_name = (data.get("testName") or "").strip()
            created_at = (data.get("createdAt") or "").strip()
            clinical_impresion_left = (data.get("clinicalImpresionLeft") or "").strip()
            clinical_impresion_right = (data.get("clinicalImpresionRight") or "").strip()
            recommendation = (data.get("recommendation") or "").strip()
            result_marks = data.get("resultMarks") or []

            if not all([session_id, patient_id, centre_code, test_name, created_at]):
                return self._json_response(
                    {
                        "success": False,
                        "error": "Missing required fields: sessionId, patientId, centreCode, testName, createdAt",
                    },
                    status=400,
                )

            # Validate centre code
            clinic = (
                request.env["resonnocare.clinic"]
                .sudo()
                .search([("clinic_code", "=", centre_code)], limit=1)
            )
            if not clinic:
                return self._json_response(
                    {"success": False, "error": f"Invalid Centre Code: {centre_code}"},
                    status=404,
                )

            # Find patient by patient_id or create a reference
            patient = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("patient_id", "=", patient_id),
                        ("is_patient", "=", True),
                    ],
                    limit=1,
                )
            )
            if not patient:
                return self._json_response(
                    {"success": False, "error": f"Patient not found: {patient_id}"},
                    status=404,
                )

            # Generate unique ID for this test result
            uid = str(uuid.uuid4())

            # Create audiometry test result record
            test_result = request.env["resonnocare.audiometry.result"].sudo().create(
                {
                    "uid": uid,
                    "session_id": session_id,
                    "patient_id": patient.id,
                    "clinic_id": clinic.id,
                    "test_name": test_name,
                    "created_at": created_at,
                    "clinical_impresion_left": clinical_impresion_left,
                    "clinical_impresion_right": clinical_impresion_right,
                    "recommendation": recommendation,
                }
            )

            # Create result marks
            for mark in result_marks:
                ear = (mark.get("ear") or "").strip().lower()
                mode = (mark.get("mode") or "").strip().upper()
                masking = mark.get("masking", False)
                frequency = mark.get("frequency") or 0
                intensity = mark.get("intensity") or 0
                response = (mark.get("response") or "").strip()
                transaction_date = (mark.get("transactionDate") or "").strip()
                c1 = (mark.get("C1") or "").strip()
                c2 = (mark.get("C2") or "").strip()
                c3 = (mark.get("C3") or "").strip()
                c4 = (mark.get("C4") or "").strip()
                c5 = (mark.get("C5") or "").strip()
                c6 = (mark.get("C6") or "").strip()

                # Validate ear and mode
                if ear not in ["left", "right"]:
                    continue
                if mode not in ["AC", "BC", "FF"]:
                    continue

                request.env["resonnocare.audiometry.result.mark"].sudo().create(
                    {
                        "result_id": test_result.id,
                        "ear": ear,
                        "mode": mode,
                        "masking": masking,
                        "frequency": frequency,
                        "intensity": intensity,
                        "response": response,
                        "transaction_date": transaction_date,
                        "c1": c1,
                        "c2": c2,
                        "c3": c3,
                        "c4": c4,
                        "c5": c5,
                        "c6": c6,
                    }
                )

            return self._json_response(
                {
                    "success": True,
                    "data": {
                        "uid": uid,
                        "message": "Audiometry results saved successfully",
                    },
                    "error": None,
                },
                status=200,
            )

        except Exception as err:
            _logger.exception("Save audiometry results API error")
            return self._json_response(
                {
                    "success": False,
                    "error": f"An unexpected error occurred: {str(err)}",
                },
                status=500,
            )

    @http.route(
        "/api/tests/audiometry-results/download-file",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    def download_audiometry_report(self, **kwargs):
        """Download audiometry report (PDF) by test result `uid`"""
        try:
            uid = (kwargs.get("uid") or "").strip()
            if not uid:
                return self._json_response(
                    {"success": False, "error": "Missing required parameter: uid"},
                    status=400,
                )

            test_result = (
                request.env["resonnocare.audiometry.result"].sudo()
                .search([("uid", "=", uid)], limit=1)
            )
            if not test_result:
                return self._json_response(
                    {"success": False, "error": f"Test result not found: {uid}"},
                    status=404,
                )

            # Prefer explicit attachment relation if available
            attachment = None
            try:
                if getattr(test_result, "report_attachment_id", False):
                    attachment = (
                        request.env["ir.attachment"].sudo().browse(int(test_result.report_attachment_id))
                    )
                    if not attachment.exists():
                        attachment = None
            except Exception:
                attachment = None

            # Fallback: search attachments linked to the record
            if not attachment:
                attachment = (
                    request.env["ir.attachment"].sudo()
                    .search(
                        [
                            ("res_model", "=", "resonnocare.audiometry.result"),
                            ("res_id", "=", test_result.id),
                        ],
                        limit=1,
                    )
                )

            if not attachment:
                return self._json_response(
                    {"success": False, "error": "No report attachment found for this test result."},
                    status=404,
                )

            file_b64 = getattr(attachment, "datas", None)
            if isinstance(file_b64, bytes):
                try:
                    file_b64 = file_b64.decode("utf-8")
                except Exception:
                    # keep as bytes if it is raw binary
                    file_b64 = None

            file_binary = b""
            if file_b64:
                try:
                    file_binary = base64.b64decode(file_b64)
                except Exception:
                    file_binary = file_b64.encode("utf-8") if isinstance(file_b64, str) else b""
            else:
                # As a last resort, try reading attachment.datas_file or db field directly
                raw = getattr(attachment, "db_datas", None) or getattr(attachment, "file", None)
                if isinstance(raw, (bytes, bytearray)):
                    file_binary = bytes(raw)

            if not file_binary:
                return self._json_response(
                    {"success": False, "error": "Attachment found but file content could not be read."},
                    status=500,
                )

            filename = attachment.name or f"{uid}.pdf"
            mimetype = getattr(attachment, "mimetype", "") or "application/pdf"

            return request.make_response(
                file_binary,
                headers=[
                    ("Content-Type", mimetype),
                    ("Content-Disposition", f'attachment; filename="{filename}"'),
                ],
                status=200,
            )

        except Exception as err:
            _logger.exception("Download audiometry report API error")
            return self._json_response(
                {
                    "success": False,
                    "error": f"An unexpected error occurred: {str(err)}",
                },
                status=500,
            )

    @http.route(
        "/api/tests/audiometry-results/upload-file",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def upload_audiometry_report(self, **kwargs):
        """Upload audiometry report (PDF) for a test result"""
        try:
            if not self._check_api_key():
                return self._json_response(
                    {"success": False, "error": "Unauthorized API access."},
                    status=401,
                )

            # Parse JSON body
            try:
                data = json.loads(request.httprequest.data.decode("utf-8"))
            except Exception as e:
                return self._json_response(
                    {
                        "success": False,
                        "error": f"Invalid JSON body: {str(e)}",
                    },
                    status=400,
                )

            # Validate required fields
            uid = (data.get("uid") or "").strip()
            file_name = (data.get("fileName") or "").strip()
            file_content = (data.get("fileContent") or "").strip()

            if not all([uid, file_name, file_content]):
                return self._json_response(
                    {
                        "success": False,
                        "error": "Missing required fields: uid, fileName, fileContent",
                    },
                    status=400,
                )

            # Find test result by uid
            test_result = (
                request.env["resonnocare.audiometry.result"]
                .sudo()
                .search([("uid", "=", uid)], limit=1)
            )
            if not test_result:
                return self._json_response(
                    {"success": False, "error": f"Test result not found: {uid}"},
                    status=404,
                )

            # Decode base64 file content
            try:
                file_binary = base64.b64decode(file_content)
            except Exception as e:
                return self._json_response(
                    {
                        "success": False,
                        "error": f"Invalid Base64 file content: {str(e)}",
                    },
                    status=400,
                )

            # Create attachment (ir.attachment)
            attachment = request.env["ir.attachment"].sudo().create(
                {
                    "name": file_name,
                    "type": "binary",
                    "datas": base64.b64encode(file_binary),
                    "res_model": "resonnocare.audiometry.result",
                    "res_id": test_result.id,
                }
            )

            # Update test result with attachment reference
            test_result.write({"report_attachment_id": attachment.id})

            return self._json_response(
                {
                    "success": True,
                    "data": {
                        "message": "Report uploaded successfully",
                    },
                    "error": None,
                },
                status=200,
            )

        except Exception as err:
            _logger.exception("Upload audiometry report API error")
            return self._json_response(
                {
                    "success": False,
                    "error": f"An unexpected error occurred: {str(err)}",
                },
                status=500,
            )

    @http.route(
        "/api/tests/audiometry-results/patient",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    def get_audiometry_results_by_patient(self, **kwargs):
        """Return all audiometry results (including marks and attachment metadata) for a given patientId"""
        try:
            if not self._check_api_key():
                return self._json_response(
                    {"success": False, "error": "Unauthorized API access."},
                    status=401,
                )

            patient_id = (kwargs.get("patientId") or "").strip()
            if not patient_id:
                return self._json_response(
                    {"success": False, "error": "Missing required parameter: patientId"},
                    status=400,
                )

            patient = (
                request.env["res.partner"].sudo().search(
                    [("patient_id", "=", patient_id), ("is_patient", "=", True)],
                    limit=1,
                )
            )
            if not patient:
                return self._json_response(
                    {"success": False, "error": f"Patient not found: {patient_id}"},
                    status=404,
                )

            results = (
                request.env["resonnocare.audiometry.result"].sudo()
                .search([("patient_id", "=", patient.id)], order="created_at desc, id desc")
            )

            data = []
            for r in results:
                # marks
                marks = []
                mark_recs = (
                    request.env["resonnocare.audiometry.result.mark"].sudo()
                    .search([("result_id", "=", r.id)], order="id asc")
                )
                for m in mark_recs:
                    marks.append(
                        {
                            "ear": getattr(m, "ear", ""),
                            "mode": getattr(m, "mode", ""),
                            "masking": bool(getattr(m, "masking", False)),
                            "frequency": getattr(m, "frequency", 0),
                            "intensity": getattr(m, "intensity", 0),
                            "response": getattr(m, "response", ""),
                            "transactionDate": getattr(m, "transaction_date", ""),
                            "C1": getattr(m, "c1", ""),
                            "C2": getattr(m, "c2", ""),
                            "C3": getattr(m, "c3", ""),
                            "C4": getattr(m, "c4", ""),
                            "C5": getattr(m, "c5", ""),
                            "C6": getattr(m, "c6", ""),
                        }
                    )

                # attachments metadata (include download URL)
                attachments = (
                    request.env["ir.attachment"].sudo()
                    .search([
                        ("res_model", "=", "resonnocare.audiometry.result"),
                        ("res_id", "=", r.id),
                    ])
                )
                attach_list = []
                # build download URL using the test result uid
                try:
                    base = (request.httprequest.host_url or "").rstrip("/")
                    download_url = f"{base}/api/tests/audiometry-results/download-file?uid={r.uid}"
                except Exception:
                    download_url = ""
                for a in attachments:
                    attach_list.append(
                        {
                            "id": a.id,
                            "name": getattr(a, "name", ""),
                            "mimetype": getattr(a, "mimetype", ""),
                            "url": download_url,
                        }
                    )

                data.append(
                    {
                        "uid": getattr(r, "uid", ""),
                        "sessionId": getattr(r, "session_id", ""),
                        "testName": getattr(r, "test_name", ""),
                        "createdAt": getattr(r, "created_at", ""),
                        "clinicalImpresionLeft": getattr(r, "clinical_impresion_left", ""),
                        "clinicalImpresionRight": getattr(r, "clinical_impresion_right", ""),
                        "recommendation": getattr(r, "recommendation", ""),
                        "marks": marks,
                        "attachments": attach_list,
                    }
                )

            return self._json_response(
                {
                    "success": True,
                    "data": data,
                    "error": None,
                },
                status=200,
            )

        except Exception as err:
            _logger.exception("Get audiometry results by patient API error")
            return self._json_response(
                {"success": False, "error": f"An unexpected error occurred: {str(err)}"},
                status=500,
            )


    def _generate_reqhash(self, secret_key, payload):
        """
        Paytm EDC reqHash — exact as per working sample code
        Simple compact JSON, no sort_keys
        """
        body_json_str = json.dumps(payload, separators=(',', ':'))
        _logger.info("Hash input string: %s", body_json_str)
        digest = hmac.new(
            secret_key.encode('utf-8'),
            body_json_str.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(digest).decode('utf-8')

    @http.route(
        "/api/paytm/payment-request",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    def paytm_payment_request(self, **kwargs):
        """Create Paytm POS Payment Request"""

        try:
            # ---------------------------------------------------------
            # API KEY VALIDATION
            # ---------------------------------------------------------
            if not self._check_api_key():
                return self._json_response(
                    {"success": False, "error": "Unauthorized API access"},
                    status=401,
                )

            # ---------------------------------------------------------
            # PARSE REQUEST BODY
            # ---------------------------------------------------------
            try:
                raw_data = request.httprequest.data.decode("utf-8")
                data = json.loads(raw_data)
            except Exception as e:
                return self._json_response(
                    {"success": False, "error": f"Invalid JSON body: {str(e)}"},
                    status=400,
                )

            if not isinstance(data, dict):
                return self._json_response(
                    {"success": False, "error": "Invalid JSON body: expected a JSON object"},
                    status=400,
                )

            # ---------------------------------------------------------
            # VALIDATE INPUTS
            # ---------------------------------------------------------
            amount = data.get("amount")
            order_id = (data.get("orderId") or "").strip()

            if not amount:
                return self._json_response(
                    {"success": False, "error": "Amount is required"},
                    status=400,
                )

            if not order_id:
                order_id = "TXN0" + str(random.randint(100000, 999999))

            if not order_id.isalnum():
                return self._json_response(
                    {"success": False, "error": "orderId must be alphanumeric only (A-Z, 0-9)"},
                    status=400,
                )

            # ---------------------------------------------------------
            # PAYTM CONFIG
            # ---------------------------------------------------------
            params = request.env["ir.config_parameter"].sudo()

            merchant_id = (
                params.get_param("resonnocare.paytm_merchant_id")
                or "EAR36056844945908889"
            )
            merchant_key = (
                params.get_param("resonnocare.paytm_merchant_key")
                or "7fK9xQ2mLp8VzR4cYn6Hd3BaW1sTg5Ju"
            )
            client_id = (
                params.get_param("resonnocare.paytm_client_id")
                or "resonnocare"
            )
            paytm_url = (
                params.get_param("resonnocare.paytm_url")
                or "https://securegw-stage.paytm.in/edc-integration-service/payment/request"
            )

            if not merchant_id or not merchant_key or not client_id:
                return self._json_response(
                    {"success": False, "error": "Paytm configuration is incomplete"},
                    status=500,
                )

            # ---------------------------------------------------------
            # TERMINAL ID (TID)
            # ---------------------------------------------------------
            terminal_id = (data.get("terminalId") or data.get("tid") or "").strip()
            if not terminal_id:
                terminal_id = (params.get_param("resonnocare.paytm_terminal_id") or "").strip()
            if not terminal_id:
                return self._json_response(
                    {"success": False, "error": "Terminal ID (terminalId) is required"},
                    status=400,
                )

            # ---------------------------------------------------------
            # FORMAT AMOUNT (PAISE FORMAT)
            # ---------------------------------------------------------
            amount_str = str(amount).strip()
            try:
                float_val = float(amount_str)
                # Convert Rupees to Paise
                amount_paise = int(round(float_val * 100))
                amount = str(amount_paise)
            except (TypeError, ValueError):
                return self._json_response(
                    {"success": False, "error": "Amount must be numeric"},
                    status=400,
                )

            # ---------------------------------------------------------
            # BUILD PAYLOAD
            # ---------------------------------------------------------
            txn_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            merchant_reference_no = (
                (data.get("merchantReferenceNo") or "").strip()
                or str(random.randint(100000, 999999))
            )

            additional_info = data.get("additionalInfo")
            if not isinstance(additional_info, dict):
                additional_info = {}

            if not additional_info.get("paymentMode"):
                additional_info["paymentMode"] = (
                    data.get("paymentMode") or "ALL"
                ).strip() or "ALL"

            request_body = {
                "txnDate": txn_date,
                "merchantTxnId": order_id,
                "txnAmount": amount,
                "mid": merchant_id,
                "terminalId": terminal_id,
                "merchantReferenceNo": merchant_reference_no,
                "additionalInfo": additional_info,
            }

            # ---------------------------------------------------------
            # GENERATE HASH
            # ---------------------------------------------------------
            _logger.info("Paytm reqHash body: %s", json.dumps(request_body, separators=(',', ':')))
            req_hash = self._generate_reqhash(merchant_key, request_body)
            _logger.info("Computed Paytm reqHash: %s", req_hash)

            # ---------------------------------------------------------
            # FINAL PAYLOAD
            # ---------------------------------------------------------
            request_payload = {
                "head": {
                    "clientId": client_id,
                    "reqHash": req_hash,
                },
                "body": request_body,
            }

            _logger.info("Paytm Final Request Payload: %s", json.dumps(request_payload, indent=2))

            # ---------------------------------------------------------
            # PAYTM API CALL (TLS 1.2 Enforced Session)
            # ---------------------------------------------------------
            session = requests.Session()
            session.mount("https://", TLSAdapter())
            paytm_response = session.post(
                paytm_url,
                headers={"Content-Type": "application/json"},
                json=request_payload,
                timeout=30,
            )

            response_text = paytm_response.text
            _logger.info(
                "Paytm Response [%s]: %s",
                paytm_response.status_code,
                response_text,
            )

            # ---------------------------------------------------------
            # PARSE RESPONSE
            # ---------------------------------------------------------
            try:
                response_json = paytm_response.json()
            except Exception:
                response_json = {"raw_response": response_text}

            # ---------------------------------------------------------
            # SUCCESS
            # ---------------------------------------------------------
            if paytm_response.status_code in [200, 201]:
                txn_id = ""
                if isinstance(response_json, dict) and "body" in response_json:
                    body_data = response_json["body"] or {}
                    txn_id = body_data.get("txnId") or body_data.get("txnID") or ""

                return self._json_response(
                    {
                        "success": True,
                        "message": "Payment request created successfully",
                        "data": {
                            "merchantTxnId": order_id,
                            "orderId": order_id,
                            "amount": amount,
                            "txnId": txn_id,
                            "paytmResponse": response_json,
                        },
                    },
                    status=200,
                )

            # ---------------------------------------------------------
            # API FAILURE
            # ---------------------------------------------------------
            return self._json_response(
                {
                    "success": False,
                    "error": "Paytm API Error",
                    "paytmResponse": response_json,
                },
                status=paytm_response.status_code,
            )

        except requests.exceptions.RequestException as e:
            _logger.exception("Paytm connection error")
            return self._json_response(
                {"success": False, "error": f"Connection error: {str(e)}"},
                status=503,
            )

        except Exception as e:
            _logger.exception("Paytm POS API Error")
            return self._json_response(
                {"success": False, "error": str(e)},
                status=500,
            )

    @http.route(
        "/api/paytm/check-status",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    def paytm_check_status(self, **kwargs):
        """Check Paytm POS Transaction Status"""
        try:
            if not self._check_api_key():
                return self._json_response(
                    {"success": False, "error": "Unauthorized API access"},
                    status=401,
                )

            try:
                raw_data = request.httprequest.data.decode("utf-8")
                data = json.loads(raw_data)
            except Exception as e:
                return self._json_response(
                    {"success": False, "error": f"Invalid JSON body: {str(e)}"},
                    status=400,
                )

            if not isinstance(data, dict):
                return self._json_response(
                    {"success": False, "error": "Invalid JSON body: expected a JSON object"},
                    status=400,
                )

            order_id = (data.get("orderId") or data.get("merchantTxnId") or "").strip()
            if not order_id:
                return self._json_response(
                    {"success": False, "error": "orderId (merchantTxnId) is required"},
                    status=400,
                )

            if not order_id.isalnum():
                return self._json_response(
                    {"success": False, "error": "orderId must be alphanumeric only (no special characters)"},
                    status=400,
                )

            params = request.env["ir.config_parameter"].sudo()
            merchant_id = (
                params.get_param("resonnocare.paytm_merchant_id")
                or "EAR36056844945908889"
            )
            merchant_key = (
                params.get_param("resonnocare.paytm_merchant_key")
                or "7fK9xQ2mLp8VzR4cYn6Hd3BaW1sTg5Ju"
            )
            client_id = (
                params.get_param("resonnocare.paytm_client_id")
                or "resonnocare"
            )
            status_url = (
                params.get_param("resonnocare.paytm_status_url")
                or "https://securegw-stage.paytm.in/edc-integration-service/payment/status"
            )

            if not merchant_id or not merchant_key or not client_id:
                return self._json_response(
                    {"success": False, "error": "Paytm configuration is incomplete"},
                    status=500,
                )

            # Build Check-Status Request Body
            request_body = {
                "mid": merchant_id,
                "merchantTxnId": order_id,
            }

            _logger.info("Paytm Check Status reqHash body: %s", json.dumps(request_body, separators=(',', ':')))
            req_hash = self._generate_reqhash(merchant_key, request_body)
            _logger.info("Computed Paytm Check Status reqHash: %s", req_hash)

            request_payload = {
                "head": {
                    "clientId": client_id,
                    "reqHash": req_hash,
                },
                "body": request_body,
            }

            _logger.info("Paytm Final Check Status Request Payload: %s", json.dumps(request_payload, indent=2))

            session = requests.Session()
            session.mount("https://", TLSAdapter())
            paytm_response = session.post(
                status_url,
                headers={"Content-Type": "application/json"},
                json=request_payload,
                timeout=30,
            )

            response_text = paytm_response.text
            _logger.info("Paytm Check Status Response [%s]: %s", paytm_response.status_code, response_text)

            try:
                response_json = paytm_response.json()
            except Exception:
                response_json = {"raw_response": response_text}

            if paytm_response.status_code in [200, 201]:
                txn_id = ""
                if isinstance(response_json, dict) and "body" in response_json:
                    body_data = response_json["body"] or {}
                    txn_id = body_data.get("txnId") or body_data.get("txnID") or ""

                return self._json_response(
                    {
                        "success": True,
                        "message": "Status checked successfully",
                        "data": {
                            "merchantTxnId": order_id,
                            "txnId": txn_id,
                            "paytmResponse": response_json,
                        },
                    },
                    status=200,
                )

            return self._json_response(
                {
                    "success": False,
                    "error": "Paytm API Error during check status",
                    "paytmResponse": response_json,
                },
                status=paytm_response.status_code,
            )

        except requests.exceptions.RequestException as e:
            _logger.exception("Paytm connection error during check status")
            return self._json_response(
                {"success": False, "error": f"Connection error: {str(e)}"},
                status=503,
            )
        except Exception as e:
            _logger.exception("Paytm Check Status POS API Error")
            return self._json_response(
                {"success": False, "error": str(e)},
                status=500,
            )

    @http.route(
        "/api/paytm/abort-request",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    def paytm_abort_request(self, **kwargs):
        """Abort Paytm POS Transaction"""
        try:
            if not self._check_api_key():
                return self._json_response(
                    {"success": False, "error": "Unauthorized API access"},
                    status=401,
                )

            try:
                raw_data = request.httprequest.data.decode("utf-8")
                data = json.loads(raw_data)
            except Exception as e:
                return self._json_response(
                    {"success": False, "error": f"Invalid JSON body: {str(e)}"},
                    status=400,
                )

            if not isinstance(data, dict):
                return self._json_response(
                    {"success": False, "error": "Invalid JSON body: expected a JSON object"},
                    status=400,
                )

            order_id = (data.get("orderId") or data.get("merchantTxnId") or "").strip()
            if not order_id:
                return self._json_response(
                    {"success": False, "error": "orderId (merchantTxnId) is required"},
                    status=400,
                )

            if not order_id.isalnum():
                return self._json_response(
                    {"success": False, "error": "orderId must be alphanumeric only (no special characters)"},
                    status=400,
                )

            params = request.env["ir.config_parameter"].sudo()
            merchant_id = (
                params.get_param("resonnocare.paytm_merchant_id")
                or "EAR36056844945908889"
            )
            merchant_key = (
                params.get_param("resonnocare.paytm_merchant_key")
                or "7fK9xQ2mLp8VzR4cYn6Hd3BaW1sTg5Ju"
            )
            client_id = (
                params.get_param("resonnocare.paytm_client_id")
                or "resonnocare"
            )
            abort_url = (
                params.get_param("resonnocare.paytm_abort_url")
                or "https://securegw-stage.paytm.in/edc-integration-service/payment/abort"
            )

            if not merchant_id or not merchant_key or not client_id:
                return self._json_response(
                    {"success": False, "error": "Paytm configuration is incomplete"},
                    status=500,
                )

            # Build Abort Request Body
            request_body = {
                "mid": merchant_id,
                "merchantTxnId": order_id,
            }

            _logger.info("Paytm Abort reqHash body: %s", json.dumps(request_body, separators=(',', ':')))
            req_hash = self._generate_reqhash(merchant_key, request_body)
            _logger.info("Computed Paytm Abort reqHash: %s", req_hash)

            request_payload = {
                "head": {
                    "clientId": client_id,
                    "reqHash": req_hash,
                },
                "body": request_body,
            }

            _logger.info("Paytm Final Abort Request Payload: %s", json.dumps(request_payload, indent=2))

            session = requests.Session()
            session.mount("https://", TLSAdapter())
            paytm_response = session.post(
                abort_url,
                headers={"Content-Type": "application/json"},
                json=request_payload,
                timeout=30,
            )

            response_text = paytm_response.text
            _logger.info("Paytm Abort Response [%s]: %s", paytm_response.status_code, response_text)

            try:
                response_json = paytm_response.json()
            except Exception:
                response_json = {"raw_response": response_text}

            if paytm_response.status_code in [200, 201]:
                return self._json_response(
                    {
                        "success": True,
                        "message": "Payment aborted successfully",
                        "data": {
                            "merchantTxnId": order_id,
                            "paytmResponse": response_json,
                        },
                    },
                    status=200,
                )

            return self._json_response(
                {
                    "success": False,
                    "error": "Paytm API Error during payment abort",
                    "paytmResponse": response_json,
                },
                status=paytm_response.status_code,
            )

        except requests.exceptions.RequestException as e:
            _logger.exception("Paytm connection error during payment abort")
            return self._json_response(
                {"success": False, "error": f"Connection error: {str(e)}"},
                status=503,
            )
        except Exception as e:
            _logger.exception("Paytm Abort POS API Error")
            return self._json_response(
                {"success": False, "error": str(e)},
                status=500,
            )