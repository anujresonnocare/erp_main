/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

export class AiQueryBar extends Component {
    static template = "ridhira_ai_chat_report.AiQueryBar";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            isOpen: false,
            prompt: "",
            isLoading: false,
            error: null,
            results: null,
        });
    }

    togglePanel() {
        this.state.isOpen = !this.state.isOpen;
    }

    async submitQuery() {
        if (!this.state.prompt.trim()) return;
        
        this.state.isLoading = true;
        this.state.error = null;
        this.state.results = null;

        try {
            const response = await this.orm.call(
                "ai.report.query",
                "action_generate_query",
                [this.state.prompt]
            );
            
            this.state.isOpen = false;
            
            // Execute standard Odoo action to render the graph/pivot natively
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: `AI Report: ${this.state.prompt}`,
                res_model: response.model_name,
                view_mode: `${response.chart_type === 'pivot' ? 'pivot' : 'graph'},list`,
                views: [
                    [false, response.chart_type === 'pivot' ? 'pivot' : 'graph'],
                    [false, "list"]
                ],
                domain: response.domain,
                context: {
                    group_by: response.groupby,
                    // If line chart, try to pass to context (some views respect it, otherwise user can switch)
                    graph_mode: response.chart_type === 'line' ? 'line' : (response.chart_type === 'pie' ? 'pie' : 'bar')
                },
                target: "current",
            });
            
        } catch (error) {
            this.state.error = error.message || "Failed to generate report. Please try again.";
            console.error(error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.submitQuery();
        }
    }
}

export const systrayItem = {
    Component: AiQueryBar,
};

registry.category("systray").add("ridhira_ai_chat_report.AiQueryBar", systrayItem, { sequence: 100 });
