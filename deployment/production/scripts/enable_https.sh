#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
./scripts/dns_readiness.sh

domain=${APP_DOMAIN:?APP_DOMAIN is required}
email=${LETSENCRYPT_EMAIL:-}
cert=/etc/letsencrypt/live/$domain/fullchain.pem
if [ ! -f "$cert" ]; then
  if [ -n "$email" ]; then
    certbot certonly --webroot -w /var/www/letsencrypt -d "$domain" --agree-tos --non-interactive --email "$email"
  else
    certbot certonly --webroot -w /var/www/letsencrypt -d "$domain" --agree-tos --non-interactive --register-unsafely-without-email
  fi
fi

template=nginx/host-vhost.conf.example
target=/etc/nginx/sites-available/ai-ranking-os-app
temporary=$(mktemp)
trap 'rm -f "$temporary"' EXIT
sed "s/app.xn--80aaatitma6afyf.xn--p1ai/$domain/g" "$template" > "$temporary"
install -m 0644 "$temporary" "$target"
ln -sfn "$target" /etc/nginx/sites-enabled/ai-ranking-os-app
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt -untrusted "/etc/letsencrypt/live/$domain/chain.pem" "/etc/letsencrypt/live/$domain/cert.pem"
nginx -t
systemctl reload nginx
curl --fail --silent --show-error --proto '=https' --tlsv1.2 "https://$domain/health" >/dev/null
curl --fail --silent --show-error "http://$domain/health" -o /dev/null -w '%{redirect_url}\n' | grep -q "https://$domain/health"
echo "https=PASS domain=$domain"
