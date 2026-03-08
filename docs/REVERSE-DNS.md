# Reverse DNS (PTR) for Jamming Bot

To reduce abuse reports and identify the bot server in logs, configure **reverse DNS (PTR)** so that the server IP resolves to your hostname.

## IP: 80.74.27.74 → jamming-bot.arthew0.online

### Clodo (CLODO CLOUD SERVICE CO. L.L.C)

1. Log in to the **Clodo** control panel (or contact support).
2. Find the section for **Reverse DNS** / **PTR record** (often under "Network", "IP", or "Server settings").
3. For IP **80.74.27.74** set the PTR record to:
   ```text
   jamming-bot.arthew0.online
   ```
4. Ensure **forward DNS** is already set: `jamming-bot.arthew0.online` → A record → `80.74.27.74` (so that the hostname points to this IP). Many providers require this before allowing PTR.
5. Wait for propagation (from a few minutes up to 24–48 hours). Check with:
   ```bash
   dig -x 80.74.27.74 +short
   ```
   Expected: `jamming-bot.arthew0.online.`

If the control panel does not expose PTR, open a ticket to Clodo support and ask to set reverse DNS for **80.74.27.74** to **jamming-bot.arthew0.online**.
