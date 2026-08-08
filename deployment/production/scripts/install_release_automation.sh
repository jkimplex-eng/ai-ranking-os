#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y certbot dnsutils ca-certificates curl openssl
install -d -m 0755 /var/www/letsencrypt
for unit in systemd/*.service systemd/*.timer; do
  install -m 0644 "$unit" "/etc/systemd/system/$(basename "$unit")"
done
systemctl daemon-reload
systemctl enable --now ai-ranking-release.timer ai-ranking-monitor.timer ai-ranking-backup.timer
systemctl list-timers 'ai-ranking-*' --no-pager
