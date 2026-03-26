#!/bin/bash
# install-service.sh — Install the Fruit Sorter as a systemd service (auto-start on boot)
#
# Usage:  sudo bash scripts/install-service.sh

set -e

SERVICE_NAME="fruit-sorter"
SERVICE_FILE="$(dirname "$(realpath "$0")")/../fruit-sorter.service"
DEST="/etc/systemd/system/${SERVICE_NAME}.service"

echo "=== Fruit Sorter — Service Installer ==="
echo ""

# 1. Copy service file
echo "  Copying service file → ${DEST}"
cp "$SERVICE_FILE" "$DEST"

# 2. Reload systemd
echo "  Reloading systemd daemon..."
systemctl daemon-reload

# 3. Enable on boot
echo "  Enabling ${SERVICE_NAME} to start on boot..."
systemctl enable "$SERVICE_NAME"

# 4. Start now
echo "  Starting ${SERVICE_NAME} now..."
systemctl start "$SERVICE_NAME"

echo ""
echo "  ✅ Done! The fruit sorter will now start automatically on every boot."
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status  ${SERVICE_NAME}   # Check status"
echo "    sudo systemctl stop    ${SERVICE_NAME}   # Stop"
echo "    sudo systemctl restart ${SERVICE_NAME}   # Restart"
echo "    sudo journalctl -u     ${SERVICE_NAME} -f # Live logs"
echo "    sudo systemctl disable ${SERVICE_NAME}   # Disable auto-start"
echo ""
