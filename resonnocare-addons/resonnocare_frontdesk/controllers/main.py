from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
import logging

_logger = logging.getLogger(__name__)

class DiscountApprovalController(http.Controller):

    def _get_record_and_validate(self, record_id, token):
        """Helper to fetch record and validate token."""
        record = request.env['resonnocare.discount.approval.request'].sudo().browse(record_id)
        
        # Check if record exists
        if not record.exists():
            raise MissingError("The requested record does not exist.")
        
        # Validate token (ensure access_token field exists on your model)
        if not token or record.access_token != token:
            raise AccessError("Invalid or missing security token.")
            
        return record

    @http.route('/discount/approve/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def approve_discount(self, record_id, token=None, **kw):
        try:
            record = self._get_record_and_validate(record_id, token)
            
            # Optional: Prevent double approval
            if record.state == 'approved':
                return request.render('website.404', {'message': 'This request has already been approved.'})

            # Call your model's method
            record.action_approve()
            
            # Render a success template (You need to create this XML template)
            return request.render('your_module_name.approval_success_template', {
                'record': record,
                'action': 'Approved'
            })
            
        except (AccessError, MissingError) as e:
            return request.render('website.403', {'message': str(e)})
        except Exception as e:
            _logger.error("Approval Error: %s", str(e))
            return request.render('website.500', {'message': "An unexpected error occurred."})

    @http.route('/discount/reject/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def reject_discount(self, record_id, token=None, **kw):
        try:
            record = self._get_record_and_validate(record_id, token)
            
            if record.state == 'rejected':
                return request.render('website.404', {'message': 'This request has already been rejected.'})

            # Call your model's method
            record.action_reject()
            
            return request.render('your_module_name.approval_success_template', {
                'record': record,
                'action': 'Rejected'
            })
            
        except (AccessError, MissingError) as e:
            return request.render('website.403', {'message': str(e)})
        except Exception as e:
            _logger.error("Rejection Error: %s", str(e))
            return request.render('website.500', {'message': "An unexpected error occurred."})