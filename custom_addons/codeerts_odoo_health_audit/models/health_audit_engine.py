import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

CATEGORIES = ['finance', 'sales', 'inventory', 'data_quality', 'security']
SEVERITY_WEIGHT = {'info': 1, 'warning': 4, 'critical': 10}


class HealthAuditEngine(models.AbstractModel):
    _name = 'health.audit.engine'
    _description = 'Health Audit Engine'

    @api.model
    def _installed_modules(self):
        mods = self.env['ir.module.module'].search([('state', '=', 'installed')])
        return set(mods.mapped('name'))

    @api.model
    def _active_checks(self):
        installed = self._installed_modules()
        checks = self.env['health.check'].search([('active', '=', True)])
        return checks.filtered(lambda c: c.module_dependency in installed)

    @api.model
    def run_audit(self, trigger='manual'):
        start = fields.Datetime.now()
        run = self.env['health.audit.run'].create({'trigger': trigger})
        cat_penalty = {c: 0 for c in CATEGORIES}
        counts = {'info': 0, 'warning': 0, 'critical': 0}
        active_checks = self._active_checks()
        for check in active_checks:
            try:
                count, domain, severity = getattr(self, check.method_name)(check)
                if not count:
                    continue
                if severity not in SEVERITY_WEIGHT:
                    _logger.warning(
                        "Health check %s returned invalid severity %r; defaulting to 'info'.",
                        check.name, severity)
                    severity = 'info'
                self.env['health.audit.finding'].create({
                    'run_id': run.id,
                    'check_id': check.id,
                    'severity': severity,
                    'count': count,
                    'affected_model': self._affected_model(check),
                    'domain': domain,
                })
                counts[severity] += 1
                if check.category in cat_penalty:
                    cat_penalty[check.category] += SEVERITY_WEIGHT[severity]
            except Exception:
                _logger.exception("Health check %s failed", check.name)
                continue
        scores = {c: max(0, 100 - min(100, cat_penalty[c] * 5)) for c in CATEGORIES}
        overall = round(sum(scores.values()) / len(CATEGORIES))
        run.write({
            'overall_score': overall,
            'score_finance': scores['finance'],
            'score_sales': scores['sales'],
            'score_inventory': scores['inventory'],
            'score_data_quality': scores['data_quality'],
            'score_security': scores['security'],
            'count_critical': counts['critical'],
            'count_warning': counts['warning'],
            'count_info': counts['info'],
            'duration': (fields.Datetime.now() - start).total_seconds(),
            'active_check_count': len(active_checks),
            'scanned_app_count': len(set(active_checks.mapped('module_dependency'))),
        })
        # Return the id (not the recordset) so the method is safe to call over
        # XML-RPC: v18 cannot marshal a recordset return value.
        return run.id

    @api.model
    def _affected_model(self, check):
        # Optional companion method '<method_name>_model' on a check mixin
        # returns the affected model name for the "View Records" action.
        getter = check.method_name + '_model'
        if hasattr(self, getter):
            return getattr(self, getter)() or False
        return False
