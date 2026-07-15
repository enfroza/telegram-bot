# Telegram JSONBin Unlock Manager Bot (PocketBase Version)

A powerful Telegram bot to manage dynamic unlock configurations for your video/content platform using **PocketBase** as the backend.

## Features

- Interactive `/create` wizard with step-by-step flow
- Auto-saves your `openLinkUrl` for faster future use
- Beautiful inline buttons (Use saved / Enter new, Private/Public, Confirm, etc.)
- `/list` to view your created bins
- Stores all data in **PocketBase** (self-hosted, unlimited, free)
- Generates shareable frontend links automatically
- Runs 24/7 as a systemd service

## Why PocketBase instead of JSONBin?

- No request limits
- Full database control
- Better performance and structure
- Completely free and self-hosted on your VPS

## Requirements

- Ubuntu VPS (tested on Azure)
- Python 3.10+
- PocketBase running on port 8090
- Telegram Bot Token (from @BotFather)

## Installation

### 1. Install PocketBase

```bash
cd ~
wget https://github.com/pocketbase/pocketbase/releases/latest/download/pocketbase_0.22.10_linux_arm64.zip
unzip pocketbase_0.22.10_linux_arm64.zip
chmod +x pocketbase
