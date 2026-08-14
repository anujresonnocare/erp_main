from odoo.tests import TransactionCase


class TestHealthCheck(TransactionCase):
    def test_param_min_max_guard(self):
        check = self.env['health.check'].create({
            'name': 'X', 'category': 'data_quality',
            'module_dependency': 'base', 'method_name': '_noop',
            'default_severity': 'warning',
        })
        with self.assertRaises(Exception):
            self.env['health.check.param'].create({
                'check_id': check.id, 'key': 'months', 'label': 'Months',
                'ptype': 'int', 'value': '0', 'default': '24',
                'min_val': 1, 'max_val': 120,
            })

    def test_reset_to_default(self):
        check = self.env['health.check'].create({
            'name': 'Y', 'category': 'data_quality',
            'module_dependency': 'base', 'method_name': '_noop',
            'default_severity': 'warning',
        })
        param = self.env['health.check.param'].create({
            'check_id': check.id, 'key': 'months', 'label': 'Months',
            'ptype': 'int', 'value': '12', 'default': '24',
            'min_val': 1, 'max_val': 120,
        })
        param.reset_to_default()
        self.assertEqual(param.value, '24')


class TestDataQualityChecks(TransactionCase):
    def test_partner_no_email_detected(self):
        self.env['res.partner'].create({'name': 'NoEmail Co'})
        engine = self.env['health.audit.engine']
        # call the check directly with a matching health.check record
        check = self.env['health.check'].create({
            'name': 'No email', 'category': 'data_quality',
            'module_dependency': 'base', 'method_name': '_check_partner_no_email',
            'default_severity': 'warning',
        })
        count, domain, severity = engine._check_partner_no_email(check)
        self.assertGreaterEqual(count, 1)
        self.assertEqual(severity, 'warning')
