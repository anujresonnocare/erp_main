from odoo.tests import TransactionCase


class TestEngine(TransactionCase):
    def test_run_creates_scored_run(self):
        # run_audit returns the run id (RPC-safe), not the recordset.
        run_id = self.env['health.audit.engine'].run_audit(trigger='manual')
        run = self.env['health.audit.run'].browse(run_id)
        self.assertTrue(run.exists())
        self.assertGreaterEqual(run.overall_score, 0)
        self.assertLessEqual(run.overall_score, 100)

    def test_only_installed_module_checks_run(self):
        self.env['health.check'].create({
            'name': 'Bogus', 'category': 'sales',
            'module_dependency': 'no_such_module_xyz',
            'method_name': '_check_noop', 'default_severity': 'info',
        })
        run_id = self.env['health.audit.engine'].run_audit()
        run = self.env['health.audit.run'].browse(run_id)
        self.assertFalse(
            run.finding_ids.filtered(lambda f: f.check_id.name == 'Bogus'))
