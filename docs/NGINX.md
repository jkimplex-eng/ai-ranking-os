# Nginx and TLS

The Compose Nginx provides routing, WebSocket support, gzip, static caching and security headers on
loopback port 8100. Host Nginx owns ports 80/443 and TLS. Use
`deployment/production/nginx/host-vhost.conf.example` as a new vhost; do not edit the existing
landing vhost.

Create DNS first. Then obtain a certificate manually with Certbot webroot or Nginx mode for
`app.xn--80aaatitma6afyf.xn--p1ai`. The project intentionally does not issue certificates
automatically. Validate with `nginx -t`, reload Nginx, confirm renewal timer and test HTTP-to-HTTPS,
HTTP/2, `/health`, `/api/auth/login`, WebSocket upgrade and HSTS.
