import logging
import traceback

from odoo import SUPERUSER_ID, api, fields, models

_logger = logging.getLogger(__name__)


class IrCron(models.Model):
    _inherit = "ir.cron"

    def _callback(self, cron_name, server_action_id):
        cron_id = self.id
        history_id = self._odoo_health_log_start(cron_id)
        try:
            result = super()._callback(cron_name, server_action_id)
        except Exception:
            self._odoo_health_log_end(history_id, "failed", traceback.format_exc())
            raise
        self._odoo_health_log_end(history_id, "success", None)
        return result

    def method_direct_trigger(self):
        for cron in self:
            history_id = cron._odoo_health_log_start(cron.id)
            try:
                super(IrCron, cron).method_direct_trigger()
            except Exception:
                cron._odoo_health_log_end(history_id, "failed", traceback.format_exc())
                raise
            cron._odoo_health_log_end(history_id, "success", None)
        return True

    def _odoo_health_log_start(self, cron_id):
        with self.pool.cursor() as new_cr:
            env = api.Environment(new_cr, SUPERUSER_ID, {})
            return env["ir.cron.history"].create({
                "cron_id": cron_id,
                "state": "running",
            }).id

    def _odoo_health_log_end(self, history_id, state, error_traceback):
        if not history_id:
            return
        # Write the history row in its own short-lived cursor so its row
        # lock is released the moment this block commits. The failure
        # email is enqueued afterwards in a separate cursor: send_mail
        # renders the template and creates mail.mail / mail.message rows,
        # which must not run while we hold the history row lock (no slow
        # work nested inside the lock). Both cursors stay isolated from
        # the monitored cron's main transaction on purpose, so the
        # history write and the alert survive its rollback.
        with self.pool.cursor() as new_cr:
            env = api.Environment(new_cr, SUPERUSER_ID, {})
            env["ir.cron.history"].browse(history_id).write({
                "state": state,
                "date_end": fields.Datetime.now(),
                "error_traceback": error_traceback,
            })
        if state == "failed":
            with self.pool.cursor() as mail_cr:
                env = api.Environment(mail_cr, SUPERUSER_ID, {})
                history = env["ir.cron.history"].browse(history_id)
                self._odoo_health_send_failure_email(env, history)


    @staticmethod
    def _odoo_health_send_failure_email(env, history):
        emails_param = (env["ir.config_parameter"].sudo()
                        .get_param("odoo_health_check.notify_emails") or "").strip()
        if not emails_param:
            return
        recipients = [e.strip() for e in emails_param.split(",") if e.strip()]
        if not recipients:
            return
        template = env.ref(
            "odoo_health_check.mail_template_cron_failure",
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "odoo_health_check: mail template not found, failure alert skipped"
            )
            return
        try:
            template.send_mail(
                history.id,
                force_send=False,
                email_values={"email_to": ",".join(recipients)},
            )
        except Exception:
            _logger.exception(
                "odoo_health_check: failed to enqueue cron failure email for history_id=%s",
                history.id,
            )
