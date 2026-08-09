#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
domain=${APP_DOMAIN:?APP_DOMAIN is required}
expected=${EXPECTED_IPV4:?EXPECTED_IPV4 is required}

command -v dig >/dev/null 2>&1 || { echo "dig is required" >&2; exit 2; }
authoritative=$(dig +short NS "${domain#app.}" | head -n 1)
test -n "$authoritative"
authoritative_ip=$(dig +short "@$authoritative" "$domain" A | tail -n 1)
cloudflare_ip=$(dig +short @1.1.1.1 "$domain" A | tail -n 1)
google_ip=$(dig +short @8.8.8.8 "$domain" A | tail -n 1)
ttl=$(dig +noall +answer @1.1.1.1 "$domain" A | awk 'NR==1 {print $2}')
aaaa=$(dig +short @1.1.1.1 "$domain" AAAA | paste -sd, -)

test "$authoritative_ip" = "$expected"
test "$cloudflare_ip" = "$expected"
test "$google_ip" = "$expected"
nginx -T 2>/dev/null | grep -q "server_name $domain;"
printf 'dns=PASS domain=%s ipv4=%s ttl=%s aaaa=%s\n' "$domain" "$expected" "${ttl:-unknown}" "${aaaa:-none}"
