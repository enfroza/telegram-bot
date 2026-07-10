# JSONBin Unlock Manager - Telegram Bot

A powerful Telegram bot to manage JSONBin configurations for the Unlock Video frontend.

## Features

- Interactive `/create` wizard with **saved `openLinkUrl`** support
- Inline buttons for fast workflow
- `/createfull` for pasting complete custom JSON
- `/update`, `/get`, `/list` commands
- Auto-saves your `openLinkUrl` after successful creation
- Works great on Azure VM, Railway, Oracle Cloud, etc.

## Commands

| Command              | Description                              |
|----------------------|------------------------------------------|
| `/start`             | Show main menu                           |
| `/create`            | Create new bin (uses saved openLinkUrl)  |
| `/createfull`        | Create using full custom JSON            |
| `/setopen <url>`     | Save default `openLinkUrl`               |
| `/update <bin_id>`   | Update existing bin                      |
| `/get <bin_id>`      | View current JSON of a bin               |
| `/list`              | Show your created bins                   |
| `/cancel`            | Cancel current operation                 |

## Quick Start (Local)

1. Get your bot token from [@BotFather](https://t.me/BotFather)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables (recommended):
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export JSONBIN_MASTER_KEY="your_jsonbin_master_key"
   ```
4. Run the bot:
   ```bash
   python3 telegram_jsonbin_unlock_bot.py
   ```

## Deployment on Azure VM (Recommended)

### 1. Create Ubuntu VM
- **Image**: Ubuntu 24.04 LTS
- **Size**: `Standard_B1s` (enough for this bot)
- Allow SSH (port 22)

### 2. Connect via SSH and setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python & Git
sudo apt install python3 python3-pip git -y

# Clone your repo (or upload files manually)
git clone https://github.com/YOUR_USERNAME/your-bot-repo.git
cd your-bot-repo

# Install dependencies
pip3 install -r requirements.txt

# Create environment file
nano ~/.env
```

Add this to `~/.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
JSONBIN_MASTER_KEY=your_jsonbin_master_key_here
```

### 3. Run as systemd service (Recommended)

Create service file:

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Paste:

```ini
[Unit]
Description=JSONBin Unlock Telegram Bot
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/your-bot-repo
EnvironmentFile=/home/azureuser/.env
ExecStart=/usr/bin/python3 /home/azureuser/your-bot-repo/telegram_jsonbin_unlock_bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

# Check status
sudo systemctl status telegram-bot

# View live logs
sudo journalctl -u telegram-bot -f
```

## Environment Variables

| Variable                | Required | Description                          |
|-------------------------|----------|--------------------------------------|
| `TELEGRAM_BOT_TOKEN`    | Yes      | Your Telegram bot token              |
| `JSONBIN_MASTER_KEY`    | Yes      | Your JSONBin X-Master-Key            |

## Notes

- The bot only saves `openLinkUrl` as default (as requested)
- `unlockUrl` must be entered every time (it usually changes)
- All created bins are tracked locally in `bot_config.json`
- Works with both public and private JSONBin bins

## Support

For issues or feature requests, contact the developer.

---

**Made for managing Unlock Video configurations easily from Telegram.**
