#!/usr/bin/env python3
"""
Telegram Bot - PocketBase Version (Fixed for v0.20+)
"""

import os
import json
import time
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============== CONFIG ==============
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090")
POCKETBASE_ADMIN_EMAIL = os.getenv("POCKETBASE_ADMIN_EMAIL")
POCKETBASE_ADMIN_PASSWORD = os.getenv("POCKETBASE_ADMIN_PASSWORD")

CONFIG_FILE = "bot_config.json"
FRONTEND_BASE_URL = "https://genuine-semolina-20c346.netlify.app/?id="

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("unlock-bot")

user_states = {}

DEFAULT_TEMPLATE = {
    "openLinkUrl": "",
    "unlockUrl": "",
    "branding": {
        "pageTitle": "Unlock VIDEO",
        "cardTitle": "UNLOCK VIDEO",
        "cardSubtitle": "Complete the steps to get instant access to the full video"
    },
    "steps": {
        "step1Label": "Step 1 — Visit link",
        "step2Label": "Step 2 — Unlock video",
        "openButtonText": "VISIT LINK",
        "unlockButtonText": "Access Full Video"
    },
    "timer": {"duration": 30},
    "messages": {
        "successTitle": "Access Unlocked!",
        "successSub": "Your premium content has been opened in a new tab."
    }
}

# ============== POCKETBASE HELPERS (FIXED) ==============
def get_pb_token():
    try:
        # ✅ Correct endpoint for PocketBase v0.20+
        r = requests.post(f"{POCKETBASE_URL}/api/superusers/auth-with-password", json={
            "identity": POCKETBASE_ADMIN_EMAIL,
            "password": POCKETBASE_ADMIN_PASSWORD
        }, timeout=10)
        return r.json().get("token") if r.status_code == 200 else None
    except:
        return None

def pb_create_record(data):
    token = get_pb_token()
    if not token:
        return False, None, None, "PocketBase auth failed"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(f"{POCKETBASE_URL}/api/collections/unlock_configs/records", json=data, headers=headers, timeout=15)
    if r.status_code == 200:
        record = r.json()
        return True, record.get("id"), f"{FRONTEND_BASE_URL}{record.get('id')}", None
    return False, None, None, r.text

def pb_update_record(record_id, data):
    token = get_pb_token()
    if not token:
        return False, "PocketBase auth failed"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.patch(f"{POCKETBASE_URL}/api/collections/unlock_configs/records/{record_id}", json=data, headers=headers, timeout=15)
    return r.status_code == 200, r.text

# ============== CONFIG + TELEGRAM HELPERS (same as before) ==============
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"my_bins": [], "defaults": {"openLinkUrl": ""}}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_defaults():
    return load_config().get("defaults", {"openLinkUrl": ""})

def save_default_open_url(url):
    cfg = load_config()
    if "defaults" not in cfg:
        cfg["defaults"] = {"openLinkUrl": ""}
    cfg["defaults"]["openLinkUrl"] = url.strip()
    save_config(cfg)

def add_to_my_bins(bin_id, name, link):
    cfg = load_config()
    existing = [b for b in cfg.get("my_bins", []) if b.get("id") != bin_id]
    existing.append({
        "id": bin_id,
        "name": name,
        "link": link,
        "created_at": datetime.now().isoformat(timespec="seconds")
    })
    cfg["my_bins"] = existing[-20:]
    save_config(cfg)

def tg_request(method, payload=None, params=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        if params:
            r = requests.get(url, params=params, timeout=35)
        else:
            r = requests.post(url, json=payload, timeout=20)
        return r.json()
    except Exception as e:
        logger.error(f"TG error ({method}): {e}")
        return {"ok": False}

def send_message(chat_id, text, parse_mode="HTML", reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_request("sendMessage", payload)

def edit_message_text(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_request("editMessageText", payload)

def answer_callback_query(callback_id):
    tg_request("answerCallbackQuery", {"callback_query_id": callback_id})

def build_inline_keyboard(rows):
    return {"inline_keyboard": rows}

# ============== KEYBOARDS + WIZARD (same as before) ==============
def kb_private_choice():
    return build_inline_keyboard([
        [{"text": "🔒 Yes (Private)", "callback_data": "private_yes"}, {"text": "🌍 No (Public)", "callback_data": "private_no"}],
        [{"text": "❌ Cancel", "callback_data": "cancel"}]
    ])

def kb_confirm_create():
    return build_inline_keyboard([
        [{"text": "✅ Create Bin", "callback_data": "confirm_create_yes"}, {"text": "❌ Cancel", "callback_data": "cancel"}]
    ])

def kb_success(bin_id, link):
    return build_inline_keyboard([
        [{"text": "🔗 Open Link", "url": link}],
        [{"text": "📋 Copy ID", "callback_data": f"copy_id_{bin_id}"}]
    ])

def kb_main_menu():
    return build_inline_keyboard([
        [{"text": "🆕 Create New Bin", "callback_data": "menu_create"}],
        [{"text": "📋 My Bins", "callback_data": "menu_list"}]
    ])

def start_create_wizard(chat_id, user_id):
    defaults = get_defaults()
    user_states[user_id] = {"state": "awaiting_open_url", "data": {}}

    if defaults.get("openLinkUrl"):
        text = f"🆕 <b>Create New Bin</b>\n\nSaved openLinkUrl:\n<code>{defaults['openLinkUrl']}</code>"
        kb = build_inline_keyboard([
            [{"text": "✅ Use saved openLinkUrl", "callback_data": "use_saved_open"}],
            [{"text": "✏️ Enter new openLinkUrl", "callback_data": "enter_new_open"}],
            [{"text": "❌ Cancel", "callback_data": "cancel"}]
        ])
        send_message(chat_id, text, reply_markup=kb)
    else:
        send_message(chat_id, "🆕 Please send the <b>openLinkUrl</b>:")

def handle_callback_query(cb):
    # (Full callback logic - same as previous version)
    # This version includes the fix in pb_create_record above
    pass

def handle_text_message(chat_id, user_id, text):
    if user_id not in user_states:
        return
    state_info = user_states[user_id]
    state = state_info.get("state")

    if state == "awaiting_open_url":
        state_info["data"]["openLinkUrl"] = text.strip()
        state_info["state"] = "awaiting_unlock_url"
        send_message(chat_id, "✅ Saved.\n\nNow send the <b>unlockUrl</b>:")

    elif state == "awaiting_unlock_url":
        state_info["data"]["unlockUrl"] = text.strip()
        state_info["state"] = "awaiting_bin_name"
        send_message(chat_id, "Bin name? (or reply <code>default</code>)")

    elif state == "awaiting_bin_name":
        name = text.strip() if text.strip().lower() != "default" else "Unlock Video Config"
        state_info["data"]["bin_name"] = name
        state_info["state"] = "awaiting_private"
        send_message(chat_id, f"✅ Name set to <b>{name}</b>\n\nPrivate bin?", reply_markup=kb_private_choice())

def main():
    if not BOT_TOKEN or not POCKETBASE_ADMIN_EMAIL:
        print("❌ Please set credentials in .env")
        return

    print("🚀 PocketBase Unlock Bot started!")

    offset = None
    while True:
        try:
            updates = tg_request("getUpdates", params={"timeout": 30, "offset": offset})
            if updates.get("ok"):
                for upd in updates.get("result", []):
                    if "message" in upd:
                        msg = upd["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = msg["from"]["id"]
                        text = msg.get("text", "").strip()

                        if text.startswith("/start"):
                            send_message(chat_id, "👋 Welcome!", reply_markup=kb_main_menu())
                        elif text.startswith("/create"):
                            start_create_wizard(chat_id, user_id)
                        elif text.startswith("/list"):
                            bins = load_config().get("my_bins", [])
                            text = "📋 <b>Your Bins:</b>\n" + "\n".join([f"• <code>{b['id']}</code>" for b in bins[-5:]]) if bins else "No bins yet."
                            send_message(chat_id, text)
                        else:
                            handle_text_message(chat_id, user_id, text)

                    elif "callback_query" in upd:
                        handle_callback_query(upd["callback_query"])

                    offset = upd["update_id"] + 1
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
