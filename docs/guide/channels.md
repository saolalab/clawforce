# Channel Setup

Step-by-step setup for messaging channels used by clawbot agents.

## Slack (Socket Mode)

1. Create an app at [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From scratch.
2. **OAuth & Permissions** → Bot Token Scopes: add `app_mentions:read`, `chat:write`, `channels:history`, `groups:history`, `im:history`, `reactions:write`.
3. **Event Subscriptions** → Enable Events → Subscribe to bot events: `app_mention`, `message.channels`, `message.groups`, `message.im`.
4. **Socket Mode** → Enable Socket Mode → create an App-level token with `connections:write`.
5. **Install App** to your workspace.
6. Add the bot to channels (invite it with `/invite @YourBot`).
7. In agent Channels settings: Bot Token (`xoxb-...`), App Token (`xapp-...`).

**In channels**, the bot responds only when @mentioned (default `group_policy: mention`). **In DMs**, it responds to any message. Run with `LOGURU_LEVEL=DEBUG` to see why messages are ignored.

## Telegram

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts (name, username).
3. Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`).
4. In agent Channels settings: set `token` to your bot token.

Optional: `group_policy: mention` (default) — bot replies only when @mentioned in groups. Set to `open` to reply to all messages.

## Discord

1. Go to [Discord Developer Portal](https://discord.com/developers/applications) → New Application.
2. **Bot** → Add Bot → Reset Token (copy and store securely).
3. **OAuth2** → URL Generator: select scopes `bot`, permissions `Send Messages`, `Read Message History`, `View Channels`, `Read Messages/View Channels`.
4. Invite the bot to your server using the generated URL.
5. In agent Channels settings: set `token` to your bot token.

## Feishu / Lark

Uses WebSocket long connection — no public IP or webhook required.

1. Create an app at [Feishu Open Platform](https://open.feishu.cn/app) (or [Lark](https://open.larksuite.com/app) for non-China).
2. **Credentials & Basic Info** → copy App ID and App Secret.
3. **App Capability** → enable **Bot**.
4. **Event Subscription** → enable `im.message.receive_v1`.
5. In agent Channels settings: set `appId` and `appSecret`.

## WhatsApp

Requires the Node.js bridge (`bridges/whatsapp/` in this repo). WhatsApp has no official bot API; the bridge uses [Baileys](https://github.com/WhiskeySockets/Baileys) to connect via WhatsApp Web.

**Docker agents (Marketplace install):**

1. Install `whatsapp-bridge` from the Software catalog (Marketplace → Software). The bridge installs and starts automatically via `post_install`.
2. To link your WhatsApp account, open the terminal in the **Workspace** tab and run:
   ```bash
   clawbot-whatsapp-bridge
   ```
3. Scan the QR code with WhatsApp (Linked Devices) on your phone. The session is saved automatically. The bridge daemon picks up credentials on next connect — restart the agent if needed.
4. In agent Channels settings: enable WhatsApp.

**Manual setup:**

1. Install the bridge: `cd bridges/whatsapp && npm install && npm run build`
2. To link your account (first run): run `clawbot-whatsapp-bridge` — QR appears in the terminal, scan it, credentials saved, process exits. No ports opened.
3. To start the daemon: run `clawbot-whatsapp-bridge start`
4. In agent Channels settings: set `bridgeUrl` (default `ws://localhost:3001`), optionally `bridgeToken` if `BRIDGE_TOKEN` is set.

Bridge env vars: `WHATSAPP_BRIDGE_PORT` or `BRIDGE_PORT` (default 3001), `AUTH_DIR` (auth storage), `BRIDGE_TOKEN` (optional auth).

## Zalo

Uses Zalo Official Account (Bot API) with long-polling — no public IP or webhook required.

1. Create a bot at [Zalo Bot Platform](https://bot.zaloplatforms.com) (or [bot.zapps.me](https://bot.zapps.me)).
2. Copy the bot token (format: `12345689:abc-xyz`).
3. In agent Channels settings: set `botToken` to your bot token.
4. Optional: add `allowFrom` (user IDs) to restrict which users can message the bot. Empty = allow all.

Text is chunked to 2000 characters (Zalo API limit). Media (images) supported via URLs.

## Zalo Personal (zalouser)

Uses zca-js via Node.js bridge — requires QR scan to link your personal Zalo account.

1. Install and run the Zalo Personal bridge:
   ```bash
   cd bridges/zalo && npm install && npm run build && npm start
   ```
   Or install via Software catalog: `zalo-personal-bridge`.
2. Scan the QR code with Zalo on your phone (first run only).
3. In agent Channels settings: set `bridgeUrl` (default `ws://localhost:3002`), optionally `bridgeToken` if `BRIDGE_TOKEN` is set on the bridge.

Bridge env vars: `BRIDGE_PORT` (default 3002), `AUTH_DIR`, `BRIDGE_TOKEN` (optional auth).

## Microsoft Teams

Uses Bot Framework. Requires Azure Bot registration and a public URL for the webhook.

1. Create a bot at [Azure Portal](https://portal.azure.com) → Azure Bot.
2. Copy App ID and create an App Password.
3. Set Messaging endpoint to: `https://your-domain/api/webhooks/teams/{agent_id}` (replace `{agent_id}` with your agent's ID).
4. In agent Channels settings: set `appId` and `appPassword`.
5. Start the agent. The webhook receives messages when the agent is running and connected.

## Email

Uses IMAP polling for inbound and SMTP for outbound. Requires explicit user consent.

1. Enable IMAP on your email provider (Gmail, Outlook, etc.).
2. For Gmail: create an [App Password](https://support.google.com/accounts/answer/185833) (2FA required).
3. In agent Channels settings:
   - `consentGranted: true` (required — set only after user permission)
   - `imapHost`, `imapPort` (993), `imapUsername`, `imapPassword`
   - `smtpHost`, `smtpPort` (587), `smtpUsername`, `smtpPassword`
   - `fromAddress` (optional, defaults to imap username)

## Verification

### Zalo Official Account (OA)

1. Create a bot at [Zalo Bot Platform](https://bot.zaloplatforms.com) and get the bot token.
2. In agent Channels: enable Zalo, set `botToken`.
3. Start the agent. Check logs for `Zalo channel enabled` and `Starting Zalo channel (long-polling)...`.
4. Message your bot from the Zalo app (search by bot name or scan QR). The bot should reply.
5. If no reply: check `allowFrom` (empty = allow all), `group_policy` for groups, and `LOGURU_LEVEL=DEBUG` for details.

### Zalo Personal (zalouser)

1. Start the bridge: `cd bridges/zalo && npm run build && npm start`.
2. Scan the QR code with Zalo on your phone (first run only).
3. In agent Channels: enable Zalo Personal, set `bridgeUrl` (default `ws://localhost:3002`).
4. Start the agent. Check logs for `Connected to Zalo Personal bridge`.
5. Send a message to yourself or a group from the linked Zalo account. The bot should reply.
6. If no reply: ensure bridge and agent run on the same host or `bridgeUrl` is reachable; check `allowFrom` and `group_policy`.

### Microsoft Teams

1. Create an Azure Bot and set Messaging endpoint to `https://your-domain/api/webhooks/teams/{agent_id}`.
2. In agent Channels: enable Teams, set `appId` and `appPassword`.
3. Start the agent and ensure it connects to the control plane (gateway).
4. Add the bot to a Teams chat/channel and message it. The webhook receives the Activity only when the agent is running and connected.
5. If no reply: verify the webhook URL is publicly reachable; check agent is enabled and connected; inspect `allowFrom`; use `LOGURU_LEVEL=DEBUG` to see webhook logs.
