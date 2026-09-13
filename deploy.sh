#!/usr/bin/env bash
# ==============================================================================
# Deployment Script for royal300 Monthly Report Generator
# Domain: https://report.royal300.com
# VPS: 93.127.206.52
# ==============================================================================
set -e

VPS_HOST="93.127.206.52"
VPS_USER="root"

echo "==> Deploying latest changes to $VPS_HOST (report.royal300.com)..."

ssh "$VPS_USER@$VPS_HOST" "bash /root/deploy_royal300_monthly_report.sh"

echo "==> Checking service status..."
ssh "$VPS_USER@$VPS_HOST" "systemctl is-active royal300_monthly_report_gunicorn.service"

echo "==> Deployment successfully completed! Visit: https://report.royal300.com"
