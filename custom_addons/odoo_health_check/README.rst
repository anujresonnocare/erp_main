=================
Odoo Health Check
=================

Daily health check for your Odoo. Catch cron failures, monitor disk
space, see PostgreSQL growth - before your users complain.

.. image:: https://img.shields.io/badge/odoo-18-714B67.svg
    :alt: Odoo 18

.. image:: https://img.shields.io/badge/license-LGPL--3-00D4AA.svg
    :alt: License: LGPL-3

.. contents::
    :local:

What it does
============

Self-hosted Odoo runs dozens of scheduled actions that you never see -
until one quietly fails and a customer notices first. **Odoo Health
Check** turns that black box into a visible audit trail and a small set
of focused alerts. Install it, configure two email addresses, and the
module runs the rest.

Key features
============

1. At-a-glance dashboard
------------------------

Four tiles in one form view:

* Cron failures in the last 24h and 7d
* Current disk usage on OS root and the Odoo filestore
* The most recent PostgreSQL growth report

No stored state - every open re-reads the underlying models. The
Refresh button takes a fresh snapshot in one click.

2. Cron execution history with traceback
-----------------------------------------

Every scheduled action run is logged with start time, end time,
duration (millisecond precision via ``time.perf_counter``), and
execution state. When a cron fails, the full Python traceback is
captured and attached to the row. The history table writes through an
independent database cursor, so a cron rollback never erases the audit
trail.

Optional email alert on every failure with a one-click "View in Cron
History" deep link and the traceback collapsed inside a ``<details>``
block - the inbox preview stays clean.

3. Disk monitoring with smart alerts
------------------------------------

Hourly samples of OS root and the Odoo filestore mount via
``shutil.disk_usage``. Each sample stores total / free bytes, used
percentage, and a status badge: OK, Warning, Critical, or Error.
Thresholds are configurable per environment.

Email alerts fire **only on worsening transitions** (ok → warn,
ok → critical, warn → critical). Steady state and recovery never
notify - no hourly spam. A measurement error between two healthy
samples is skipped when computing transitions, so a flaky filesystem
read does not generate false alarms.

4. Monthly PostgreSQL growth report
-----------------------------------

On the 1st of each month at 08:00, a snapshot of the top-10 tables by
total relation size is captured (including indexes and TOAST). The
report compares against the previous month and emails the recipients
an HTML digest with size, Δ size, row count, and Δ rows per table,
plus total database size delta.

Row counts use ``pg_class.reltuples`` (PostgreSQL's own statistics from
the last ``ANALYZE``) - fast on multi-million-row tables, never times
out, accurate enough for trend reports.

Available in your language
==========================

UI labels, settings help, search filters, dashboard tiles, action
menus, cron names, and the three alert emails are translated to seven
additional languages. Translations apply automatically based on each
user's Odoo language preference - no extra configuration.

* English (``en``)
* Русский (``ru``)
* Українська (``uk``)
* Deutsch (``de``)
* Español (``es``)
* Română (``ro``)
* Polski (``pl``)
* العربية (``ar``)

Contributions for additional languages are welcome - the canonical
``.pot`` template ships at ``odoo_health_check/i18n/odoo_health_check.pot``.

Configuration
=============

Open **Health Check → Settings** after installation and fill in
whichever fields are relevant. Every email address is independent - you
can route cron failures to engineering, disk alerts to sysadmins, and
the PG digest to a DBA, all from one screen.

Settings:

* **Cron Failure Emails** - recipients of immediate alerts when any
  scheduled action fails
* **History Retention (days)** - how long execution rows are kept
  (default 30, set 0 to disable cleanup)
* **Disk Warning / Critical Threshold (%)** - usage levels that flip a
  sample to warn or critical (defaults 80 and 90)
* **Disk Alert Emails** - recipients for disk transition alerts
* **PG Report Emails** - recipients for the monthly PostgreSQL growth
  digest

Technical details
=================

* **Targets:** Odoo 18 Enterprise self-hosted. Community installations
  also work - the module depends only on ``base`` and ``mail``.
* **License:** LGPL-3, free.
* **Security:** all menus and records restricted to
  ``base.group_system`` (admin only). No public HTTP endpoints, no
  external network calls.
* **Storage:** two new tables (``ir_cron_history``,
  ``health_check_result``). Retention cleanup keeps both bounded.
* **No external dependencies:** no Slack, no PagerDuty, no third-party
  APIs. Email goes through your existing Odoo outgoing mail server.

Test coverage: 60+ unit and integration tests covering every cron path,
every email transition, every threshold edge case, and the dashboard
snapshot logic.

What this module does NOT do
============================

* It does not page on-call (no Slack, PagerDuty, SMS - only email)
* It does not monitor remote servers - only the host Odoo runs on
* It does not predict future disk usage - only reports current state
  and month-over-month deltas
* Database row counts are PostgreSQL estimates from
  ``pg_class.reltuples``, accurate enough for trends but not for
  billing or audit

If you need any of the above, a paid Pro variant is in development -
get in touch.

Installation
============

Install from `apps.odoo.com <https://apps.odoo.com>`_, or clone this
repository into your Odoo addons path:

.. code-block:: bash

    cd /path/to/odoo/addons
    git clone https://github.com/alex-odoo/odoo-health-check.git
    # restart Odoo, then Apps → Update Apps List → install "Odoo Health Check"

Verification
============

A 10-minute walkthrough to confirm everything works on your install is
provided in
`TESTING.md <https://github.com/alex-odoo/odoo-health-check/blob/main/TESTING.md>`_
at the repository root.

Bug reports and feature requests
================================

Source code, issues, and feature requests:
`github.com/alex-odoo/odoo-health-check
<https://github.com/alex-odoo/odoo-health-check>`_

Maintainer
==========

Built and maintained by **Rteam**, an Odoo Enterprise consulting
agency: `rteam.agency <https://rteam.agency>`_

License
=======

LGPL-3. See ``LICENSE`` for the full text.
