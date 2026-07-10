#!/usr/bin/env python3
"""
Telegram Bot for JSONBin Manager - Unlock Video Config (with Inline Buttons)
Alternative to the web UI (index.html) — now with beautiful inline keyboards.

Features:
- /create wizard with saved openLinkUrl support
- Inline buttons for faster workflow
- /createfull, /update, /get, /list
- Auto-saves openLinkUrl after successful creation
"""

import os
import json
import time
import logging
import requests
from datetime import datetime

# ============== CONFIG ==============
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8755429728:AAFFr8--kOp7S1QDlQKrGz0w6Dp-zFenB40")
CONFIG_FILE = "bot_config.json"
FRONTEND_BASE_URL = "https://genuine-semolina-20c346.netlify.app/?id="
JSONBIN_API = "https://api.jsonbin.io/v3/b"

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("unlock-bot")

user_states = {}

# ============== CONFIG HELPERS ==============
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    return {"master_key": None, "my_bins": []}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


def get_master_key():
    env_key = os.getenv("JSONBIN_MASTER_KEY") or os.getenv("MASTER_KEY")
    if env_key:
        return env_key.strip()
    return load_config().get("master_key")


def get_defaults():
    cfg = load_config()
    return cfg.get("defaults", {"openLinkUrl": ""})


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


# ============== JSONBIN API ==============
def create_bin_on_jsonbin(json_data, bin_name, is_private, master_key):
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": master_key,
        "X-Bin-Name": (bin_name or "Unlock Video Config")[:128],
        "X-Bin-Private": str(bool(is_private)).lower()
    }
    try:
        resp = requests.post(JSONBIN_API, headers=headers, json=json_data, timeout=20)
        result = resp.json()
        if resp.status_code == 200 and "metadata" in result:
            bin_id = result["metadata"].get("id")
            if bin_id:
                return True, bin_id, f"{FRONTEND_BASE_URL}{bin_id}", None
        return False, None, None, result.get("message", str(result)) if isinstance(result, dict) else str(result)
    except Exception as e:
        return False, None, None, str(e)


def update_bin_on_jsonbin(bin_id, json_data, master_key):
    headers = {"Content-Type": "application/json", "X-Master-Key": master_key}
    try:
        resp = requests.put(f"{JSONBIN_API}/{bin_id}", headers=headers, json=json_data, timeout=20)
        result = resp.json()
        if resp.status_code == 200 and "metadata" in result:
            return True, f"{FRONTEND_BASE_URL}{bin_id}", None
        return False, None, result.get("message", "Update failed") if isinstance(result, dict) else str(result)
    except Exception as e:
        return False, None, str(e)


def get_bin_from_jsonbin(bin_id, master_key):
    headers = {"X-Master-Key": master_key}
    try:
        resp = requests.get(f"{JSONBIN_API}/{bin_id}", headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            actual = data.get("record", data) if isinstance(data, dict) else data
            return True, actual, None
        return False, None, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, None, str(e)


# ============== TELEGRAM HELPERS ==============
def tg_request(method, payload=None, params=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        if params:
            r = requests.get(url, params=params, timeout=35)
        else:
            r = requests.post(url, json=payload, timeout=20)
        return r.json()
    except Exception as e:
        logger.error(f"TG API error ({method}): {e}")
        return {"ok": False, "error": str(e)}


def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    return tg_request("getUpdates", params=params)


def send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_request("sendMessage", payload=payload)


def edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_request("editMessageText", payload=payload)


def answer_callback_query(callback_id, text="", show_alert=False):
    return tg_request("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text,
        "show_alert": show_alert
    })


def build_inline_keyboard(rows):
    return {"inline_keyboard": rows}


def send_typing(chat_id):
    tg_request("sendChatAction", {"chat_id": chat_id, "action": "typing"})


# ============== INLINE KEYBOARDS ==============
def kb_private_choice():
    return build_inline_keyboard([
        [
            {"text": "🔒 Yes (Private)", "callback_data": "private_yes"},
            {"text": "🌍 No (Public)", "callback_data": "private_no"}
        ],
        [{"text": "❌ Cancel", "callback_data": "cancel"}]
    ])


def kb_confirm_create():
    return build_inline_keyboard([
        [
            {"text": "✅ Create Bin", "callback_data": "confirm_create_yes"},
            {"text": "❌ Cancel", "callback_data": "cancel"}
        ]
    ])


def kb_confirm_update():
    return build_inline_keyboard([
        [
            {"text": "✅ Update Bin", "callback_data": "confirm_update_yes"},
            {"text": "❌ Cancel", "callback_data": "cancel"}
        ]
    ])


def kb_success(bin_id, link):
    return build_inline_keyboard([
        [{"text": "🔗 Open Frontend Link", "url": link}],
        [{"text": "📋 Copy Bin ID", "callback_data": f"copy_id_{bin_id}"}]
    ])


def kb_main_menu():
    return build_inline_keyboard([
        [
            {"text": "🆕 Create New Bin", "callback_data": "menu_create"},
            {"text": "📝 Create Full JSON", "callback_data": "menu_createfull"}
        ],
        [
            {"text": "📋 My Bins", "callback_data": "menu_list"},
            {"text": "❓ Help", "callback_data": "menu_help"}
        ]
    ])


# ============== STATE HANDLERS ==============
def start_create_wizard(chat_id, user_id):
    master = get_master_key()
    if not master:
        send_message(chat_id, "❌ Please set your Master Key first with <code>/setkey YOUR_KEY</code>")
        return

    defaults = get_defaults()
    user_states[user_id] = {"state": "awaiting_open_url", "data": {}}

    if defaults.get("openLinkUrl"):
        text = (
            f"🆕 <b>Create New Unlock Bin</b>\n\n"
            f"Saved <b>openLinkUrl</b>:\n<code>{defaults['openLinkUrl']}</code>\n\n"
            "What would you like to do?"
        )
        kb = build_inline_keyboard([
            [{"text": "✅ Use saved openLinkUrl", "callback_data": "use_saved_open"}],
            [{"text": "✏️ Enter new openLinkUrl", "callback_data": "enter_new_open"}],
            [{"text": "❌ Cancel", "callback_data": "cancel"}]
        ])
        send_message(chat_id, text, reply_markup=kb)
    else:
        send_message(chat_id,
            "🆕 <b>Create New Unlock Bin</b>\n\n"
            "Please send the <b>openLinkUrl</b> (Step 1 link users will visit):")


def start_createfull_wizard(chat_id, user_id):
    master = get_master_key()
    if not master:
        send_message(chat_id, "❌ /setkey first")
        return
    user_states[user_id] = {"state": "awaiting_full_json", "data": {}}
    send_message(chat_id,
        "📝 <b>Create with Full Custom JSON</b>\n\n"
        "Paste the complete JSON you want to store:")


def handle_update_command(chat_id, user_id, bin_id):
    master = get_master_key()
    if not master:
        send_message(chat_id, "❌ /setkey first")
        return
    user_states[user_id] = {"state": "awaiting_update_json", "data": {"bin_id": bin_id}}
    send_message(chat_id, f"✏️ Ready to update <code>{bin_id}</code>\n\nSend the new full JSON:")


def handle_get_command(chat_id, user_id, bin_id):
    master = get_master_key()
    if not master:
        send_message(chat_id, "❌ /setkey first")
        return
    send_typing(chat_id)
    ok, data, err = get_bin_from_jsonbin(bin_id, master)
    if ok:
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        msg = f"📦 <b>Bin</b> <code>{bin_id}</code>:\n\n<pre><code>{pretty[:3800]}</code></pre>"
        send_message(chat_id, msg)
    else:
        send_message(chat_id, f"❌ Failed to get bin: {err}")


def handle_list_command(chat_id):
    bins = load_config().get("my_bins", [])
    if not bins:
        send_message(chat_id, "You haven't created any bins yet with this bot.")
        return
    lines = ["📋 <b>Your Tracked Bins</b>\n"]
    for b in reversed(bins):
        lines.append(f"• <b>{b.get('name')}</b>\n  ID: <code>{b['id']}</code>\n  <a href=\"{b['link']}\">Open Link</a>")
    send_message(chat_id, "\n".join(lines))


def handle_cancel(chat_id, user_id, message_id=None):
    if user_id in user_states:
        user_states.pop(user_id)
    text = "✅ Operation cancelled."
    if message_id:
        edit_message_text(chat_id, message_id, text, reply_markup={"inline_keyboard": []})
    else:
        send_message(chat_id, text)


# ============== CALLBACK HANDLER ==============
def handle_callback_query(cb):
    user_id = cb["from"]["id"]
    chat_id = cb["message"]["chat"]["id"]
    message_id = cb["message"]["message_id"]
    data = cb.get("data", "")

    answer_callback_query(cb["id"])

    state_info = user_states.get(user_id, {})
    state = state_info.get("state")

    if data == "cancel":
        handle_cancel(chat_id, user_id, message_id)
        return

    if data == "menu_create":
        start_create_wizard(chat_id, user_id)
        return
    if data == "menu_createfull":
        start_createfull_wizard(chat_id, user_id)
        return
    if data == "menu_list":
        handle_list_command(chat_id)
        return
    if data == "menu_help":
        send_message(chat_id, "Use /help or the buttons above.")
        return

    if data.startswith("copy_id_"):
        bin_id = data.replace("copy_id_", "")
        send_message(chat_id, f"Bin ID: <code>{bin_id}</code>\n(Long-press the ID to copy)")
        return

    # === Saved openLinkUrl ===
    if data == "use_saved_open":
        defaults = get_defaults()
        if defaults.get("openLinkUrl"):
            state_info["data"]["openLinkUrl"] = defaults["openLinkUrl"]
            state_info["state"] = "awaiting_unlock_url"
            edit_message_text(chat_id, message_id,
                "✅ Using saved <b>openLinkUrl</b>\n\nPlease send the <b>unlockUrl</b>:")
        return

    if data == "enter_new_open":
        edit_message_text(chat_id, message_id, "Please send the new <b>openLinkUrl</b>:")
        return

    # === Wizard-specific callbacks ===
    if state == "awaiting_private":
        if data in ["private_yes", "private_no"]:
            is_private = data == "private_yes"
            state_info["data"]["is_private"] = is_private

            d = state_info["data"]
            final_json = DEFAULT_TEMPLATE.copy()
            final_json["openLinkUrl"] = d.get("openLinkUrl", "")
            final_json["unlockUrl"] = d.get("unlockUrl", "")

            state_info["preview_json"] = final_json
            state_info["state"] = "confirm_create"

            pretty = json.dumps(final_json, indent=2, ensure_ascii=False)
            text = (
                f"👀 <b>Preview JSON to create:</b>\n\n"
                f"<pre><code>{pretty}</code></pre>\n\n"
                f"<b>Name:</b> {d.get('bin_name')}\n"
                f"<b>Private:</b> {'Yes 🔒' if is_private else 'No 🌍'}\n\n"
                "Tap a button below to continue:"
            )
            edit_message_text(chat_id, message_id, text, reply_markup=kb_confirm_create())

    elif state == "confirm_create":
        if data == "confirm_create_yes":
            d = state_info["data"]
            master = get_master_key()
            send_typing(chat_id)
            ok, bin_id, link, err = create_bin_on_jsonbin(
                state_info["preview_json"], d.get("bin_name"), d.get("is_private", True), master
            )
            if ok:
                add_to_my_bins(bin_id, d.get("bin_name"), link)

                # Auto-save openLinkUrl
                if d.get("openLinkUrl"):
                    save_default_open_url(d["openLinkUrl"])

                success_text = (
                    f"✅ <b>Bin Created!</b>\n\n"
                    f"<b>ID:</b> <code>{bin_id}</code>\n\n"
                    f"🔗 <b>Share this link:</b>\n{link}"
                )
                edit_message_text(chat_id, message_id, success_text, reply_markup=kb_success(bin_id, link))
            else:
                edit_message_text(chat_id, message_id, f"❌ Creation failed: {err}", reply_markup={"inline_keyboard": []})
            user_states.pop(user_id, None)

    elif state == "awaiting_full_private":
        if data in ["private_yes", "private_no"]:
            is_private = data == "private_yes"
            state_info["data"]["is_private"] = is_private
            d = state_info["data"]
            pretty = json.dumps(d["full_json"], indent=2, ensure_ascii=False)[:3200]
            state_info["state"] = "confirm_full_create"
            text = (
                f"👀 <b>Preview — Create with this JSON?</b>\n\n"
                f"<pre><code>{pretty}</code></pre>\n\n"
                f"<b>Name:</b> {d['bin_name']}\n<b>Private:</b> {'Yes' if is_private else 'No'}"
            )
            edit_message_text(chat_id, message_id, text, reply_markup=kb_confirm_create())

    elif state == "confirm_full_create":
        if data == "confirm_create_yes":
            d = state_info["data"]
            master = get_master_key()
            ok, bin_id, link, err = create_bin_on_jsonbin(d["full_json"], d["bin_name"], d["is_private"], master)
            if ok:
                add_to_my_bins(bin_id, d["bin_name"], link)
                edit_message_text(chat_id, message_id,
                    f"✅ <b>Custom Bin Created!</b>\n\nID: <code>{bin_id}</code>\n🔗 {link}",
                    reply_markup=kb_success(bin_id, link))
            else:
                edit_message_text(chat_id, message_id, f"❌ Failed: {err}", reply_markup={"inline_keyboard": []})
            user_states.pop(user_id, None)

    elif state == "confirm_update":
        if data == "confirm_update_yes":
            d = state_info["data"]
            master = get_master_key()
            ok, link, err = update_bin_on_jsonbin(d["bin_id"], d["new_json"], master)
            if ok:
                edit_message_text(chat_id, message_id,
                    f"✅ <b>Bin Updated!</b>\n\n🔗 {link}",
                    reply_markup=kb_success(d["bin_id"], link))
            else:
                edit_message_text(chat_id, message_id, f"❌ Update failed: {err}", reply_markup={"inline_keyboard": []})
            user_states.pop(user_id, None)


# ============== TEXT MESSAGE HANDLER ==============
def handle_text_message(chat_id, user_id, text):
    if user_id not in user_states:
        send_message(chat_id, "Unknown command. Use the buttons or /help")
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
        send_message(chat_id, "✅ Saved.\n\nBin name? (or reply <code>default</code>)")

    elif state == "awaiting_bin_name":
        name = text.strip()
        if name.lower() in ["default", "d", ""]:
            name = "Unlock Video Config"
        state_info["data"]["bin_name"] = name
        state_info["state"] = "awaiting_private"
        send_message(chat_id,
            f"✅ Name set to <b>{name}</b>\n\nShould this bin be <b>Private</b>?",
            reply_markup=kb_private_choice())

    elif state == "awaiting_full_json":
        try:
            full_json = json.loads(text)
            if not isinstance(full_json, dict):
                raise ValueError("Must be JSON object")
            state_info["data"]["full_json"] = full_json
            state_info["state"] = "awaiting_full_bin_name"
            send_message(chat_id, "✅ JSON parsed.\n\nBin name? (or <code>default</code>)")
        except Exception as e:
            send_message(chat_id, f"❌ Invalid JSON: {e}")

    elif state == "awaiting_full_bin_name":
        name = text.strip()
        if name.lower() in ["default", "d", ""]:
            name = "Unlock Video Config"
        state_info["data"]["bin_name"] = name
        state_info["state"] = "awaiting_full_private"
        send_message(chat_id, "Private bin?", reply_markup=kb_private_choice())

    elif state == "awaiting_update_json":
        try:
            new_json = json.loads(text)
            if not isinstance(new_json, dict):
                raise ValueError("Must be object")
            state_info["data"]["new_json"] = new_json
            state_info["state"] = "confirm_update"
            pretty = json.dumps(new_json, indent=2, ensure_ascii=False)[:2800]
            send_message(chat_id,
                f"👀 <b>Preview — Update bin</b> <code>{state_info['data']['bin_id']}</code> with this?\n\n"
                f"<pre><code>{pretty}</code></pre>",
                reply_markup=kb_confirm_update())
        except Exception as e:
            send_message(chat_id, f"❌ Invalid JSON: {e}")


# ============== MAIN PROCESSING ==============
def process_update(update):
    if "callback_query" in update:
        handle_callback_query(update["callback_query"])
        return

    if "message" not in update:
        return

    msg = update["message"]
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    first_name = msg["from"].get("first_name", "")
    text = (msg.get("text") or "").strip()

    if not text:
        return

    if text.startswith("/start"):
        send_message(chat_id,
            f"👋 <b>Hello {first_name}!</b>\n\n"
            "JSONBin Unlock Manager Bot\n\nQuick actions:",
            reply_markup=kb_main_menu())
    elif text.startswith("/help"):
        send_message(chat_id,
            "<b>Commands:</b>\n"
            "/create — Interactive create\n"
            "/createfull — Full custom JSON\n"
            "/update BIN_ID\n"
            "/get BIN_ID\n"
            "/list\n"
            "/setopen <url> — Save default openLinkUrl\n"
            "/cancel")
    elif text.startswith("/setkey "):
        key = text.split(maxsplit=1)[1].strip()
        cfg = load_config()
        cfg["master_key"] = key
        save_config(cfg)
        send_message(chat_id, "✅ Master Key saved!")
    elif text.startswith("/setopen "):
        url = text.split(maxsplit=1)[1].strip()
        save_default_open_url(url)
        send_message(chat_id, f"✅ Saved as default <b>openLinkUrl</b>:\n<code>{url}</code>")
    elif text == "/create":
        start_create_wizard(chat_id, user_id)
    elif text == "/createfull":
        start_createfull_wizard(chat_id, user_id)
    elif text.startswith("/update "):
        bin_id = text.split(maxsplit=1)[1].strip()
        handle_update_command(chat_id, user_id, bin_id)
    elif text.startswith("/get "):
        bin_id = text.split(maxsplit=1)[1].strip()
        handle_get_command(chat_id, user_id, bin_id)
    elif text == "/list":
        handle_list_command(chat_id)
    elif text == "/cancel":
        handle_cancel(chat_id, user_id)
    else:
        handle_text_message(chat_id, user_id, text)


# ============== MAIN LOOP ==============
def main():
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE_FROM_BOTFATHER":
        print("❌ Set your Telegram Bot Token first")
        return

    logger.info("🚀 Starting JSONBin Unlock Bot...")
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            if updates.get("ok"):
                for upd in updates.get("result", []):
                    try:
                        process_update(upd)
                    except Exception as e:
                        logger.error(f"Process error: {e}")
                    offset = upd["update_id"] + 1
            else:
                time.sleep(3)
        except KeyboardInterrupt:
            logger.info("Bot stopped.")
            break
        except Exception as e:
            logger.error(f"Loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()