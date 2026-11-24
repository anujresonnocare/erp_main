from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
import logging

_logger = logging.getLogger(__name__)

class DiscountApprovalController(http.Controller):

    def _get_record_and_validate(self, record_id, token):
        """Helper to fetch record and validate token."""
        # Use .sudo() to bypass record rules for the initial fetch
        record = request.env['resonnocare.discount.approval.request'].sudo().browse(record_id)
        
        if not record.exists():
            raise MissingError("The requested record does not exist.")
        
        # Validate token
        if not token or record.access_token != token:
            raise AccessError("Invalid or missing security token.")
            
        return record

    @http.route('/discount/approve/<int:record_id>', type='http', auth='user', website=True, csrf=False)
    def approve_discount(self, record_id, token=None, **kw):
        try:
            # 1. Fetch and validate the record
            record = self._get_record_and_validate(record_id, token)
            
            if record.state == 'approved':
                return request.redirect(f'/web#id={record.id}&model=resonnocare.discount.approval.request&view_type=form')

            # 2. Perform the approval action as the logged-in user
            record.with_user(request.env.user).action_approve()
            
            # 3. Redirect to the form view
            return request.redirect(f'/web#id={record.id}&model=resonnocare.discount.approval.request&view_type=form')
            
        except AccessError as e:
            return request.render('your_module_name.error_403_template', {'message': str(e)})
        except MissingError as e:
            return request.render('your_module_name.error_404_template', {'message': str(e)})
        except Exception as e:
            _logger.error("Approval Error: %s", str(e))
            return request.render('your_module_name.error_500_template', {'message': "An unexpected error occurred."})

    @http.route('/discount/reject/<int:record_id>', type='http', auth='user', website=True, csrf=False)
    def reject_discount(self, record_id, token=None, **kw):
        try:
            # 1. Fetch and validate the record
            record = self._get_record_and_validate(record_id, token)
            
            if record.state == 'rejected':
                return request.redirect(f'/web#id={record.id}&model=resonnocare.discount.approval.request&view_type=form')

            # 2. Perform the rejection action as the logged-in user
            record.with_user(request.env.user).action_reject()
            
            # 3. Redirect to the form view
            return request.redirect(f'/web#id={record.id}&model=resonnocare.discount.approval.request&view_type=form')
            
        except AccessError as e:
            return request.render('your_module_name.error_403_template', {'message': str(e)})
        except MissingError as e:
            return request.render('your_module_name.error_404_template', {'message': str(e)})
        except Exception as e:
            _logger.error("Rejection Error: %s", str(e))
            return request.render('your_module_name.error_500_template', {'message': "An unexpected error occurred."})