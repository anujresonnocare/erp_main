#!/bin/bash
# =============================================================================
# Resonnocare Repair Module - Production Deployment Script
# =============================================================================
# Usage:
#   sudo bash /opt/odoo18/resonnocare/resonnocare_repair/scripts/deploy.sh [install|upgrade|fix]
#
#   install  - First time install (fresh deployment)
#   upgrade  - Upgrade existing installation (code changes)
#   fix      - Fix stuck module state (to install / to upgrade)
# =============================================================================

set -e

# ---- Configuration (adjust for your server) ----
ODOO_USER="odoo18"
ODOO_VENV="/opt/odoo18/odoo18-venv/bin/python3"
ODOO_BIN="/opt/odoo18/odoo18/odoo-bin"
ODOO_CONF="/etc/odoo18.conf"
ODOO_SERVICE="odoo18"
DB_NAME=""  # Will be auto-detected from config if empty
MODULE_NAME="resonnocare_repair"

# ---- Auto-detect DB name from config ----
if [ -z "$DB_NAME" ]; then
    DB_NAME=$(grep -oP '^\s*db_name\s*=\s*\K\S+' "$ODOO_CONF" 2>/dev/null || true)
fi
if [ -z "$DB_NAME" ]; then
    # Try to get from running database
    DB_NAME=$(sudo -u "$ODOO_USER" psql -t -A -c "SELECT datname FROM pg_database WHERE datname NOT IN ('postgres','template0','template1') AND datistemplate = false LIMIT 1;" 2>/dev/null || true)
fi
if [ -z "$DB_NAME" ]; then
    echo "❌ ERROR: Cannot detect database name. Set DB_NAME in this script or add db_name to $ODOO_CONF"
    exit 1
fi

echo "============================================"
echo " Resonnocare Repair - Deployment Tool"
echo "============================================"
echo " Database : $DB_NAME"
echo " Module   : $MODULE_NAME"
echo " Action   : ${1:-install}"
echo "============================================"

ACTION="${1:-install}"

case "$ACTION" in
    install)
        echo ""
        echo "▶ Step 1: Stopping Odoo service..."
        sudo systemctl stop "$ODOO_SERVICE"
        sleep 2

        echo "▶ Step 2: Installing module via CLI..."
        sudo -u "$ODOO_USER" "$ODOO_VENV" "$ODOO_BIN" \
            -c "$ODOO_CONF" \
            -d "$DB_NAME" \
            -i "$MODULE_NAME" \
            --stop-after-init \
            --no-http 2>&1 | tail -30

        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Module installed successfully!"
        else
            echo ""
            echo "❌ Module installation failed. Check logs: /var/log/odoo18/odoo18.log"
            echo "   Attempting to fix stuck state..."
            sudo -u "$ODOO_USER" psql -d "$DB_NAME" -c \
                "UPDATE ir_module_module SET state='uninstalled' WHERE name='$MODULE_NAME' AND state='to install';" 2>/dev/null
            sudo systemctl start "$ODOO_SERVICE"
            exit 1
        fi

        echo "▶ Step 3: Starting Odoo service..."
        sudo systemctl start "$ODOO_SERVICE"
        sleep 5

        # Verify
        STATE=$(sudo -u "$ODOO_USER" psql -d "$DB_NAME" -t -A -c \
            "SELECT state FROM ir_module_module WHERE name='$MODULE_NAME';" 2>/dev/null)
        echo ""
        echo "▶ Verification: Module state = '$STATE'"
        if [ "$STATE" = "installed" ]; then
            echo "✅ Deployment SUCCESSFUL!"
        else
            echo "⚠️  Module state is '$STATE', expected 'installed'. Run: $0 fix"
        fi
        ;;

    upgrade)
        echo ""
        echo "▶ Step 1: Stopping Odoo service..."
        sudo systemctl stop "$ODOO_SERVICE"
        sleep 2

        echo "▶ Step 2: Upgrading module via CLI..."
        sudo -u "$ODOO_USER" "$ODOO_VENV" "$ODOO_BIN" \
            -c "$ODOO_CONF" \
            -d "$DB_NAME" \
            -u "$MODULE_NAME" \
            --stop-after-init \
            --no-http 2>&1 | tail -30

        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Module upgraded successfully!"
        else
            echo ""
            echo "❌ Module upgrade failed. Check logs."
            # Reset stuck state on failure
            sudo -u "$ODOO_USER" psql -d "$DB_NAME" -c \
                "UPDATE ir_module_module SET state='installed' WHERE name='$MODULE_NAME' AND state='to upgrade';" 2>/dev/null
            sudo systemctl start "$ODOO_SERVICE"
            exit 1
        fi

        echo "▶ Step 3: Starting Odoo service..."
        sudo systemctl start "$ODOO_SERVICE"
        echo "✅ Deployment SUCCESSFUL!"
        ;;

    fix)
        echo ""
        echo "▶ Fixing stuck module state..."

        # Check current state
        STATE=$(sudo -u "$ODOO_USER" psql -d "$DB_NAME" -t -A -c \
            "SELECT state FROM ir_module_module WHERE name='$MODULE_NAME';" 2>/dev/null)
        echo "  Current state: '$STATE'"

        if [ "$STATE" = "installed" ]; then
            echo "✅ Module is already installed. No fix needed."
            exit 0
        fi

        echo "▶ Stopping Odoo service..."
        sudo systemctl stop "$ODOO_SERVICE"
        sleep 2

        if [ "$STATE" = "to install" ]; then
            echo "▶ Running fresh install via CLI..."
            sudo -u "$ODOO_USER" "$ODOO_VENV" "$ODOO_BIN" \
                -c "$ODOO_CONF" \
                -d "$DB_NAME" \
                -i "$MODULE_NAME" \
                --stop-after-init \
                --no-http 2>&1 | tail -20

            # Verify and force if needed
            STATE=$(sudo -u "$ODOO_USER" psql -d "$DB_NAME" -t -A -c \
                "SELECT state FROM ir_module_module WHERE name='$MODULE_NAME';" 2>/dev/null)
            if [ "$STATE" != "installed" ]; then
                echo "▶ CLI install didn't update state. Forcing via DB..."
                sudo -u "$ODOO_USER" psql -d "$DB_NAME" -c \
                    "UPDATE ir_module_module SET state='installed', latest_version='18.0.1.0.0' WHERE name='$MODULE_NAME';"
            fi

        elif [ "$STATE" = "to upgrade" ]; then
            echo "▶ Running upgrade via CLI..."
            sudo -u "$ODOO_USER" "$ODOO_VENV" "$ODOO_BIN" \
                -c "$ODOO_CONF" \
                -d "$DB_NAME" \
                -u "$MODULE_NAME" \
                --stop-after-init \
                --no-http 2>&1 | tail -20

            STATE=$(sudo -u "$ODOO_USER" psql -d "$DB_NAME" -t -A -c \
                "SELECT state FROM ir_module_module WHERE name='$MODULE_NAME';" 2>/dev/null)
            if [ "$STATE" != "installed" ]; then
                echo "▶ Forcing state via DB..."
                sudo -u "$ODOO_USER" psql -d "$DB_NAME" -c \
                    "UPDATE ir_module_module SET state='installed', latest_version='18.0.1.0.0' WHERE name='$MODULE_NAME';"
            fi
        else
            echo "⚠️  Unexpected state: '$STATE'. Manual intervention needed."
            sudo systemctl start "$ODOO_SERVICE"
            exit 1
        fi

        echo "▶ Starting Odoo service..."
        sudo systemctl start "$ODOO_SERVICE"
        sleep 5

        STATE=$(sudo -u "$ODOO_USER" psql -d "$DB_NAME" -t -A -c \
            "SELECT state FROM ir_module_module WHERE name='$MODULE_NAME';" 2>/dev/null)
        echo ""
        echo "▶ Final state: '$STATE'"
        if [ "$STATE" = "installed" ]; then
            echo "✅ Fix SUCCESSFUL!"
        else
            echo "❌ Fix failed. Check /var/log/odoo18/odoo18.log"
            exit 1
        fi
        ;;

    *)
        echo "Usage: $0 [install|upgrade|fix]"
        echo ""
        echo "  install  - First time install (fresh deployment to production)"
        echo "  upgrade  - Upgrade after code changes"
        echo "  fix      - Fix stuck module (to install / to upgrade state)"
        exit 1
        ;;
esac
