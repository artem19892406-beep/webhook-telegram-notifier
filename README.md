# webhook-telegram-notifier

A tiny webhook receiver that forwards incoming leads (or any form submission) to a Telegram chat. One Python file, standard library only, no dependencies.

Useful as a starting point when you want instant "new lead" alerts from a website form, a landing page builder, n8n, Zapier or any service that can send a webhook.

## Features

- `POST /webhook` accepts JSON with `name`, `phone`, `email`, `source`, `message`
- optional shared secret in the `X-Webhook-Secret` header (constant-time comparison)
- request size limit (64 KB) and input validation
- payloads are never written to logs
- `GET /health` for uptime checks
- Dockerfile included, runs as a non-root user

## Quick start

1. Create a bot with [@BotFather](https://t.me/BotFather) and get its token.
2. Write to your bot once, then find your chat id (for example via `https://api.telegram.org/bot<TOKEN>/getUpdates`).
3. Run:

```bash
export TELEGRAM_BOT_TOKEN="123456:your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
export WEBHOOK_SECRET="choose-a-long-random-string"   # optional but recommended
python notifier.py
```

4. Send a test lead:

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: choose-a-long-random-string" \
  -d '{"name":"Test","phone":"+1 555 0100","message":"Interested in a quote","source":"site"}'
```

The chat receives:

```
New lead
Name: Test
Phone: +1 555 0100
Source: site
Message: Interested in a quote
```

## Docker

```bash
docker build -t webhook-telegram-notifier .
docker run -p 8080:8080 \
  -e TELEGRAM_BOT_TOKEN=... -e TELEGRAM_CHAT_ID=... -e WEBHOOK_SECRET=... \
  webhook-telegram-notifier
```

## Configuration

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | yes | Chat or user id that receives alerts |
| `WEBHOOK_SECRET` | no | If set, requests must send it in `X-Webhook-Secret` |
| `PORT` | no | Listen port, default `8080` |
| `TELEGRAM_API_BASE` | no | Override for testing, default `https://api.telegram.org` |

## Tests

```bash
python -m unittest -v
```

The tests run against a local fake Telegram server, so no token is needed.

## Run it behind HTTPS

The server speaks plain HTTP. In production put it behind a reverse proxy (Caddy, nginx) or a platform that terminates TLS.

## Author

Artem, AI automation: Python, REST APIs, webhooks, n8n, OpenAI/Claude APIs, Telegram bots.
Telegram: [@krd_lider](https://t.me/krd_lider)

License: MIT
