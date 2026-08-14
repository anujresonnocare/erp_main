/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillUnmount, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class NotificationBell extends Component {
    setup() {
        // State management
        this.state = useState({
            notifications: [],
            unreadCount: 0,
            isOpen: false
        });
        
        // Use only available services
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        // Load initial data
        this.loadNotifications();
        
        // Setup periodic refresh
        this.interval = setInterval(() => this.loadNotifications(), 30000);
        
        // Cleanup on component unmount
        onWillUnmount(() => {
            if (this.interval) {
                clearInterval(this.interval);
            }
            // Remove click outside listener
            if (this.clickOutsideHandler) {
                document.removeEventListener('click', this.clickOutsideHandler);
            }
        });
        
        // Setup click outside listener
        onMounted(() => {
            this.clickOutsideHandler = this.handleClickOutside.bind(this);
            document.addEventListener('click', this.clickOutsideHandler);
        });
    }
    
    handleClickOutside(event) {
        const dropdown = document.querySelector('.o_crm_notification_bell');
        if (dropdown && !dropdown.contains(event.target) && this.state.isOpen) {
            this.state.isOpen = false;
        }
    }
    
    async loadNotifications() {
        try {
            const notifications = await this.orm.call(
                "crm.lead.notification",
                "get_recent_notifications",
                [20]
            );
            
            const validNotifications = (notifications || []).filter(n => n && n.id);
            
            const unreadCount = await this.orm.call(
                "crm.lead.notification",
                "get_unread_count",
                []
            );
            
            this.state.notifications = validNotifications;
            this.state.unreadCount = unreadCount || 0;
        } catch (error) {
            console.error("Failed to load notifications:", error);
            this.state.notifications = [];
            this.state.unreadCount = 0;
        }
    }
    
    async markAsRead(notificationId, event) {
        if (event) {
            event.stopPropagation();
        }
        
        if (!notificationId) return;
        
        try {
            await this.orm.call(
                "crm.lead.notification",
                "action_mark_as_read",
                [[notificationId]]
            );
            await this.loadNotifications();
        } catch (error) {
            console.error("Failed to mark notification as read:", error);
        }
    }
    
    async markAllAsRead(event) {
        if (event) {
            event.stopPropagation();
        }
        
        try {
            const unreadIds = this.state.notifications
                .filter(n => n && n.id && !n.is_read)
                .map(n => n.id);
            
            if (unreadIds.length > 0) {
                await this.orm.call(
                    "crm.lead.notification",
                    "action_mark_as_read",
                    [unreadIds]
                );
                await this.loadNotifications();
            }
        } catch (error) {
            console.error("Failed to mark all as read:", error);
        }
    }


    async openNotification(notification) {

        await this.orm.call(
            "crm.lead.notification",
            "action_mark_as_read",
            [[notification.id]]
        );

        if (notification.model && notification.record_id) {

            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: notification.model,
                res_id: notification.record_id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    
    toggleDropdown(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        this.state.isOpen = !this.state.isOpen;
    }
    
    closeDropdown() {
        this.state.isOpen = false;
    }
    
    openLead(leadId, event) {
        if (event) {
            event.stopPropagation();
        }
        
        if (!leadId) {
            console.warn("No lead ID provided");
            return;
        }
        
        // Direct navigation - works without action service
        const url = `/web#id=${leadId}&model=crm.lead&view_type=form`;
        window.location.href = url;
        
        this.state.isOpen = false;
    }

    // Replace your existing openLead method with this:
    openRecord(recordId, model, event) {
        if (event) event.stopPropagation();
        if (!recordId) return;
        
        // Navigate to the record (lead or partner)
        window.location.href = `/web#id=${recordId}&model=${model}&view_type=form`;
        this.state.isOpen = false;
    }
    
    getFormattedDate(dateStr) {
        if (!dateStr) return "Just now";
        try {
            const date = new Date(dateStr);
            const now = new Date();
            const diff = Math.floor((now - date) / 1000);
            
            if (diff < 60) return "Just now";
            if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
            if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
            if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
            return date.toLocaleDateString();
        } catch (e) {
            return "Recently";
        }
    }
}

NotificationBell.template = "crm_lead_notification_bell.NotificationBell";

// Register the systray item
registry.category("systray").add("crm.notification.bell", {
    Component: NotificationBell,
});