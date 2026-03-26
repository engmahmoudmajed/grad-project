#!/bin/bash
# uninstall-service.sh — Remove the Fruit Sorter systemd service
#
# Usage:  sudo bash scripts/uninstall-service.sh

set -e

SERVICE_NAME="fruit-sorter"

echo "=== Fruit Sorter — Service Uninstaller ==="
echo ""

echo "  Stopping ${SERVICE_NAME}..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true

echo "  Disabling auto-start..."
systemctl disable "$SERVICE_NAME" 2>/dev/null || true

echo "  Removing service file..."
rm -f "/etc/systemd/system/${SERVICE_NAME}.service"

echo "  Reloading systemd daemon..."
systemctl daemon-reload

echo ""
echo "  ✅ Service removed. The system will no longer auto-start on boot."
echo ""
