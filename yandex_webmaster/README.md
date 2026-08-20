# Yandex Webmaster integration

Organization-scoped, read-only integration with the official Yandex Webmaster API 4.1.

## Flow

1. An organization administrator starts OAuth from Settings → Integrations.
2. The backend creates a single-use state and PKCE verifier.
3. Yandex redirects to `/integrations/yandex-webmaster/callback`.
4. Access and refresh tokens are encrypted at rest and never returned to the browser.
5. The administrator selects one of the sites available to the authorized account.
6. AI Ranking OS reads real popular search queries for research planning.

The application requests only `webmaster:hostinfo`. It does not request profile,
email, phone, or site-verification permissions.

## Server configuration

Set `YANDEX_WEBMASTER_CLIENT_ID`, `YANDEX_WEBMASTER_CLIENT_SECRET`, and
`YANDEX_WEBMASTER_REDIRECT_URI` in the deployment secret store. Never commit the
client secret or send it through chat.

The production callback is:

`https://app.разуммаркета.рф/api/integrations/yandex-webmaster/callback`

Alice AI visibility is not scraped. It may be imported only through an official
documented API or an explicit export supplied by the user.
