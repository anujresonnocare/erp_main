# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DiscountApprovalController(http.Controller):

    def _get_request(self, request_id, token):
        if not token:
            return None
        rec = (
            request.env["resonnocare.discount.approval.request"]
            .sudo()
            .browse(request_id)
        )
        if not rec.exists() or not rec.access_token or rec.access_token != token:
            return None
        return rec

    @http.route(
        "/discount/approve/<int:request_id>",
        type="http",
        auth="public",
        csrf=False,
    )
    def approve_discount(self, request_id, token=None, **kw):
        rec = self._get_request(request_id, token)
        if not rec:
            return request.render(
                "resonnocare_discount_approval.approval_result_template",
                {"success": False, "message": "Invalid or expired approval link."},
            )
        if rec.state != "submitted":
            return request.render(
                "resonnocare_discount_approval.approval_result_template",
                {
                    "success": False,
                    "message": f"This request is already '{rec.state}'. No action taken.",
                },
            )
        rec.action_approve()
        _logger.info("Discount request %s approved via email link", rec.name)
        return request.render(
            "resonnocare_discount_approval.approval_result_template",
            {
                "success": True,
                "message": f"Request {rec.name} has been approved successfully.",
            },
        )

    @http.route(
        "/discount/reject/<int:request_id>",
        type="http",
        auth="public",
        csrf=False,
    )
    def reject_discount(self, request_id, token=None, **kw):
        rec = self._get_request(request_id, token)
        if not rec:
            return request.render(
                "resonnocare_discount_approval.approval_result_template",
                {"success": False, "message": "Invalid or expired rejection link."},
            )
        if rec.state != "submitted":
            return request.render(
                "resonnocare_discount_approval.approval_result_template",
                {
                    "success": False,
                    "message": f"This request is already '{rec.state}'. No action taken.",
                },
            )
        rec.action_reject()
        _logger.info("Discount request %s rejected via email link", rec.name)
        return request.render(
            "resonnocare_discount_approval.approval_result_template",
            {
                "success": True,
                "message": f"Request {rec.name} has been rejected.",
            },
        )