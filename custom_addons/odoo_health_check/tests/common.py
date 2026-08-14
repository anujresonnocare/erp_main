from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests import TransactionCase


class OdooHealthTestCommon(TransactionCase):
    """Shared setup for odoo_health_check tests.

    The module isolates history writes in an independent cursor
    (`self.pool.cursor()`) so a cron's own rollback never erases the
    audit trail. That isolation, unmodified, would also hide test-seeded
    rows from the test's transactional rollback. We patch the registry
    cursor factory to hand out the test's own cursor, so history writes
    ride the test savepoint and get cleaned up automatically.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.History = cls.env["ir.cron.history"]
        cls.Cron = cls.env["ir.cron"]
        cls.Params = cls.env["ir.config_parameter"].sudo()

    def setUp(self):
        super().setUp()

        @contextmanager
        def _reuse_test_cursor():
            yield self.env.cr

        self._cursor_patcher = patch.object(
            self.env.registry, "cursor", _reuse_test_cursor,
        )
        self._cursor_patcher.start()
        self.addCleanup(self._cursor_patcher.stop)

    def _make_cron(self, name="oh_test", code="pass", active=False):
        server_action = self.env["ir.actions.server"].create({
            "name": name,
            "model_id": self.env.ref("base.model_ir_cron").id,
            "state": "code",
            "code": code,
        })
        return self.Cron.create({
            "name": name,
            "ir_actions_server_id": server_action.id,
            "interval_number": 1,
            "interval_type": "days",
            "active": active,
        })
