/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { formatDateTime, deserializeDateTime } from "@web/core/l10n/dates";

const RUN_FIELDS = [
    "overall_score",
    "score_finance",
    "score_sales",
    "score_inventory",
    "score_data_quality",
    "score_security",
    "count_critical",
    "count_warning",
    "count_info",
    "duration",
    "scanned_app_count",
    "active_check_count",
    "trigger",
    "create_date",
];

// Labels mirror the Selection values defined on our own models.
const CATEGORY_LABELS = {
    finance: "Finance",
    sales: "Sales",
    inventory: "Inventory",
    data_quality: "Data Quality",
    security: "Security",
};
const CATEGORY_ORDER = ["finance", "sales", "inventory", "data_quality", "security"];
const SEVERITY_LABELS = { info: "Info", warning: "Warning", critical: "Critical" };

// SVG gauge geometry (r = 52 -> circumference).
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 52;

export class HealthDashboard extends Component {
    static template = "codeerts_odoo_health_audit.HealthDashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ run: null, prev: null, findings: [], loading: true, delta: null });
        onWillStart(async () => await this.load());
    }

    async load() {
        this.state.loading = true;
        const runs = await this.orm.searchRead("health.audit.run", [], RUN_FIELDS, {
            limit: 2,
            order: "create_date desc",
        });
        const run = runs[0] || null;
        const prev = runs[1] || null;
        this.state.run = run;
        this.state.prev = prev;
        this.state.delta = run && prev ? run.overall_score - prev.overall_score : null;
        if (run) {
            this.state.findings = await this.orm.searchRead(
                "health.audit.finding",
                [["run_id", "=", run.id]],
                ["check_id", "category", "severity", "count", "affected_model"]
            );
        } else {
            this.state.findings = [];
        }
        this.state.loading = false;
    }

    async runAudit() {
        await this.orm.call("health.audit.engine", "run_audit", [], { trigger: "manual" });
        await this.load();
    }

    async viewRecords(findingId) {
        const action = await this.orm.call(
            "health.audit.finding",
            "action_view_records",
            [findingId]
        );
        await this.action.doAction(action);
    }

    // --- display helpers ---

    // Server datetimes come back in UTC; show them in the user's timezone.
    formatRunDate(value) {
        return value ? formatDateTime(deserializeDateTime(value)) : "";
    }

    categoryLabel(key) {
        return CATEGORY_LABELS[key] || key;
    }

    severityLabel(key) {
        return SEVERITY_LABELS[key] || key;
    }

    scoreClass(score) {
        if (score >= 80) {
            return "o_health_good";
        }
        if (score >= 50) {
            return "o_health_warn";
        }
        return "o_health_bad";
    }

    scoreColor(score) {
        if (score >= 80) {
            return "#0e8377";
        }
        if (score >= 50) {
            return "#b8860b";
        }
        return "#c0392b";
    }

    scoreLabel(score) {
        if (score >= 80) {
            return "Healthy";
        }
        if (score >= 50) {
            return "Needs attention";
        }
        return "At risk";
    }

    gaugeStyle(score) {
        const offset = GAUGE_CIRCUMFERENCE * (1 - Math.max(0, Math.min(100, score)) / 100);
        return `stroke:${this.scoreColor(score)};stroke-dasharray:${GAUGE_CIRCUMFERENCE.toFixed(
            2
        )};stroke-dashoffset:${offset.toFixed(2)};`;
    }

    countByCategory(key) {
        return this.state.findings.filter((f) => f.category === key).length;
    }

    get categories() {
        const r = this.state.run;
        if (!r) {
            return [];
        }
        const scores = {
            finance: r.score_finance,
            sales: r.score_sales,
            inventory: r.score_inventory,
            data_quality: r.score_data_quality,
            security: r.score_security,
        };
        return CATEGORY_ORDER.map((key) => ({
            key,
            label: CATEGORY_LABELS[key],
            score: scores[key],
            issues: this.countByCategory(key),
        }));
    }

    get deltaText() {
        const d = this.state.delta;
        if (d === null) {
            return "";
        }
        if (d > 0) {
            return `▲ +${d} since last run`;
        }
        if (d < 0) {
            return `▼ ${d} since last run`;
        }
        return "No change since last run";
    }
}

registry.category("actions").add("codeerts_health_dashboard", HealthDashboard);
