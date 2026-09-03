import os
import json
import time
import logging
import random
import subprocess
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Any, Union
from pathlib import Path

# ===================== التثبيت التلقائي للمكتبات =====================
try:
    import requests
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot==20.7", "requests==2.31.0"])
    import requests
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===================== الإعدادات العامة =====================
BOT_TOKEN = "8841683948:AAFkBeKbIW3S1NQL8eYWdNfgTV946re27Fs"
ADMIN_ID = 6148029159
SUPPORT_USERNAME = "SMSQusai"

# ربط سيرفر الرشق الخارجي (SMM Panel API)
SMM_API_URL = "https://example-smm-panel.com/api/v2"  
SMM_API_KEY = "YOUR_SMM_PANEL_API_KEY"                 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== قائمة الخدمات والأسعار (تعديل الأسعار من هنا) =====================
# السعر المكتوب هو سعر كل 1000 طلب (مثلاً: 10.0 يعني 10 نقاط لكل 1000)
SMM_SERVICES = {
    "tiktok": {
        "name": "🎵 تيك توك (TikTok)",
        "items": {
            "tt_followers": {"name": "👥 متابعين تيك توك", "price_per_1000": 15.0, "min": 100, "max": 50000, "api_service_id": 101},
            "tt_likes": {"name": "❤️ إعجابات تيك توك", "price_per_1000": 5.0, "min": 100, "max": 100000, "api_service_id": 102},
            "tt_views": {"name": "👁 مشاهدات فيديو تيك توك", "price_per_1000": 1.0, "min": 1000, "max": 1000000, "api_service_id": 103},
            "tt_shares": {"name": "🔄 اكسبلور ومشاركات", "price_per_1000": 3.0, "min": 500, "max": 50000, "api_service_id": 104}
        }
    },
    "facebook": {
        "name": "📘 فيسبوك (Facebook)",
        "items": {
            "fb_page_likes": {"name": "👍 لايكات ومتابعين صفحات", "price_per_1000": 20.0, "min": 100, "max": 20000, "api_service_id": 201},
            "fb_post_likes": {"name": "❤️ تفاعلات منشورات فيسبوك", "price_per_1000": 6.0, "min": 100, "max": 50000, "api_service_id": 202},
            "fb_profile_followers": {"name": "👤 متابعين حسابات شخصية", "price_per_1000": 18.0, "min": 100, "max": 30000, "api_service_id": 203},
            "fb_video_views": {"name": "👁 مشاهدات فيديو فيسبوك", "price_per_1000": 2.5, "min": 1000, "max": 500000, "api_service_id": 204}
        }
    },
    "twitter": {
        "name": "🐦 تويتر / X",
        "items": {
            "tw_followers": {"name": "👤 متابعين تويتر / X", "price_per_1000": 25.0, "min": 100, "max": 20000, "api_service_id": 301},
            "tw_likes": {"name": "❤️ إعجابات تغريدات", "price_per_1000": 8.0, "min": 100, "max": 50000, "api_service_id": 302},
            "tw_retweets": {"name": "🔄 إعادة تغريد (Retweet)", "price_per_1000": 12.0, "min": 50, "max": 10000, "api_service_id": 303},
            "tw_views": {"name": "👁 مشاهدات تغريدات", "price_per_1000": 1.5, "min": 1000, "max": 1000000, "api_service_id": 304}
        }
    },
    "instagram": {
        "name": "📸 انستغرام (Instagram)",
        "items": {
            "ig_followers": {"name": "👥 متابعين انستغرام", "price_per_1000": 12.0, "min": 100, "max": 50000, "api_service_id": 401},
            "ig_likes": {"name": "❤️ لايكات منشورات وريلز", "price_per_1000": 4.0, "min": 100, "max": 100000, "api_service_id": 402},
            "ig_views": {"name": "👁 مشاهدات ريلز وانستغرام", "price_per_1000": 1.0, "min": 1000, "max": 1000000, "api_service_id": 403}
        }
    },
    "telegram": {
        "name": "✈️ تيليجرام (Telegram)",
        "items": {
            "tg_members": {"name": "👥 اعضاء قنوات ومجموعات", "price_per_1000": 14.0, "min": 100, "max": 50000, "api_service_id": 501},
            "tg_views": {"name": "👁 مشاهدات منشورات القنوات", "price_per_1000": 0.8, "min": 500, "max": 500000, "api_service_id": 502},
            "tg_reactions": {"name": "🔥 تفاعلات وإيموجي منشورات", "price_per_1000": 3.0, "min": 100, "max": 20000, "api_service_id": 503}
        }
    },
    "youtube": {
        "name": "▶️ يوتيوب (YouTube)",
        "items": {
            "yt_subscribers": {"name": "🔴 مشتركين يوتيوب", "price_per_1000": 40.0, "min": 100, "max": 10000, "api_service_id": 601},
            "yt_views": {"name": "👁 مشاهدات يوتيوب", "price_per_1000": 8.0, "min": 1000, "max": 200000, "api_service_id": 602},
            "yt_likes": {"name": "👍 لايكات فيديو يوتيوب", "price_per_1000": 10.0, "min": 100, "max": 50000, "api_service_id": 603}
        }
    }
}

# ===================== محرك قواعد البيانات والملفات =====================
def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)

def read_json(filepath: str, default: Any = None) -> Any:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def write_json(filepath: str, data: Any) -> bool:
    try:
        ensure_dir(os.path.dirname(filepath))
        temp = f"{filepath}.tmp"
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp, filepath)
        return True
    except Exception:
        return False

def read_text(filepath: str, default: str = "") -> str:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return default

def write_text(filepath: str, content: str) -> bool:
    try:
        ensure_dir(os.path.dirname(filepath))
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False

def append_text(filepath: str, content: str) -> bool:
    try:
        ensure_dir(os.path.dirname(filepath))
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False

# ===================== إدارة الحسابات والمحفظة =====================
def get_user_data(user_id: Union[int, str]) -> dict:
    return read_json(f'data/users/{user_id}.json', {'coin': 0.0, 'invite': 0, 'spent': 0.0})

def save_user_data(user_id: Union[int, str], data: dict) -> bool:
    return write_json(f'data/users/{user_id}.json', data)

def get_user_coin(user_id: Union[int, str]) -> float:
    return float(get_user_data(user_id).get('coin', 0.0))

def add_user_coin(user_id: Union[int, str], amount: float) -> float:
    data = get_user_data(user_id)
    current = float(data.get('coin', 0.0))
    data['coin'] = current + float(amount)
    save_user_data(user_id, data)
    return data['coin']

def deduct_user_coin(user_id: Union[int, str], amount: float) -> bool:
    data = get_user_data(user_id)
    current = float(data.get('coin', 0.0))
    if current < amount:
        return False
    data['coin'] = current - amount
    data['spent'] = float(data.get('spent', 0.0)) + amount
    save_user_data(user_id, data)
    return True

def wallet_log(user_id: Union[int, str], action_type: str, amount: float, note: str = ""):
    entry = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': str(user_id),
        'type': action_type,
        'amount': amount,
        'note': note
    }
    append_text('data/wallet_ledger.log', json.dumps(entry, ensure_ascii=False) + '\n')

def get_users_list() -> List[int]:
    return read_json('data/users_list.json', {'users': []}).get('users', [])

def register_user(user_id: int):
    data = read_json('data/users_list.json', {'users': []})
    if user_id not in data['users']:
        data['users'].append(user_id)
        write_json('data/users_list.json', data)
    if not os.path.exists(f'data/users/{user_id}.json'):
        save_user_data(user_id, {'coin': 0.0, 'invite': 0, 'spent': 0.0})

def is_banned(user_id: Union[int, str]) -> bool:
    content = read_text('data/ban.txt', '')
    return str(user_id) in [l.strip() for l in content.split('\n') if l.strip()]

def is_admin(user_id: int) -> bool:
    admins = read_json('data/admins.json', {'admins': [ADMIN_ID]}).get('admins', [ADMIN_ID])
    return user_id == ADMIN_ID or user_id in admins

# ===================== نظام الطلبات والكوبونات =====================
def order_create(order_id: Any, user_id: Union[int, str], service_name: str, link: str, quantity: int, coin: float) -> bool:
    record = {
        'id': str(order_id),
        'user_id': str(user_id),
        'service': str(service_name),
        'link': link,
        'quantity': quantity,
        'coin': coin,
        'status': 'processing',
        'created_at': int(time.time())
    }
    return append_text('data/orders.txt', json.dumps(record, ensure_ascii=False) + '\n')

def get_user_orders(user_id: Union[int, str], limit: int = 8) -> List[dict]:
    lines = read_text('data/orders.txt', '').splitlines()
    user_id_str = str(user_id)
    orders = []
    for line in reversed(lines):
        if not line.strip(): continue
        try:
            order = json.loads(line)
            if str(order.get('user_id')) == user_id_str:
                orders.append(order)
                if len(orders) >= limit: break
        except Exception: continue
    return orders

def coupon_redeem(code: str, user_id: Union[int, str]) -> dict:
    code = code.upper().strip()
    user_id_str = str(user_id)
    coupons = read_json('data/coupons.json', {})
    if code not in coupons:
        return {'ok': False, 'msg': '❌ الكود غير صحيح أو غير موجود.'}
    coupon = coupons[code]
    if not coupon.get('active', True):
        return {'ok': False, 'msg': '❌ هذا الكوبون معطل حالياً.'}
    if user_id_str in coupon.get('used_by', []):
        return {'ok': False, 'msg': '❌ لقد قمت باستخدام هذا الكوبون مسبقاً.'}
    if coupon.get('max_uses', 1) > 0 and len(coupon.get('used_by', [])) >= coupon['max_uses']:
        return {'ok': False, 'msg': '❌ انتهت عدد مرات استخدام هذا الكوبون.'}
    
    coupons[code]['used_by'].append(user_id_str)
    write_json('data/coupons.json', coupons)
    add_user_coin(user_id, coupon['value'])
    wallet_log(user_id, 'coupon', coupon['value'], f"شحن كوبون: {code}")
    return {'ok': True, 'msg': f"✅ <b>تم شحن الكوبون بنجاح!</b>\n💰 أُضيفت <code>{coupon['value']}</code> نقطة إلى رصيدك."}

# ===================== الواجهة الرئيسية =====================
def format_balance_text(user_id: int) -> str:
    coin = get_user_coin(user_id)
    data = get_user_data(user_id)
    spent = data.get('spent', 0.0)
    invites = data.get('invite', 0)
    
    return f"""✨ <b>مرحباً بك في بوت الخدمات الذكي</b>
━━━━━━━━━━━━━━━━━
🎛 <b>رصيدك الحالي:</b> <code>{coin:.2f}</code> نقطة
💰 <b>إجمالي المصروف:</b> <code>{spent:.2f}</code> نقطة
👥 <b>عدد المدعوين:</b> <code>{invites}</code>
🆔 <b>معرفك (ID):</b> <code>{user_id}</code>
━━━━━━━━━━━━━━━━━"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if is_banned(user_id):
        await update.message.reply_text("❌ أنت محظور من استخدام هذا البوت.")
        return

    register_user(user_id)
    
    # معالجة رابط الإحالة
    text = update.message.text or ""
    if text.startswith('/start ') and not text.startswith('/start code_'):
        ref_id = text.replace('/start ', '').strip()
        if ref_id.isdigit() and int(ref_id) != user_id:
            ref_id_int = int(ref_id)
            user_data = get_user_data(user_id)
            if 'invited_by' not in user_data:
                user_data['invited_by'] = ref_id_int
                save_user_data(user_id, user_data)
                
                bonus = float(read_text('data/invite_bonus.txt', '5.0'))
                add_user_coin(ref_id_int, bonus)
                inv_data = get_user_data(ref_id_int)
                inv_data['invite'] = inv_data.get('invite', 0) + 1
                save_user_data(ref_id_int, inv_data)
                
                wallet_log(ref_id_int, 'invite_bonus', bonus, f"دعوة العضو {user_id}")
                try:
                    await context.bot.send_message(
                        chat_id=ref_id_int,
                        text=f"🎁 <b>مبروك!</b> قام مستخدم جديد بالدخول عبر رابطك.\n💰 أضيفت <code>{bonus}</code> نقاط إلى رصيدك.",
                        parse_mode='HTML'
                    )
                except Exception: pass

    await show_main_menu(update, context, chat_id, user_id)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    context.user_data['mode'] = None
    balance_text = format_balance_text(user_id)
    
    buttons = [
        [InlineKeyboardButton("🎬 قسم خدمات الرشق والدعم", callback_data="smm_main")],
        [InlineKeyboardButton("💳 شحن كارت", callback_data="redeem_coupon"), InlineKeyboardButton("💰 طرق الشحن", callback_data="recharge_info")],
        [InlineKeyboardButton("📊 طلباتي وحسابي", callback_data="my_orders"), InlineKeyboardButton("🔄 تحويل رصيد", callback_data="transfer_balance")],
        [InlineKeyboardButton("➕ رصيد مجاني (دعوة)", callback_data="referral_menu"), InlineKeyboardButton("📞 الدعم الفني", callback_data="support_info")]
    ]
    
    if is_admin(user_id):
        buttons.append([InlineKeyboardButton("⚙️ لوحة الإدارة العليا", callback_data="admin_panel")])
        
    markup = InlineKeyboardMarkup(buttons)
    if update.callback_query:
        await update.callback_query.edit_message_text(balance_text, parse_mode='HTML', reply_markup=markup)
    else:
        await update.message.reply_text(balance_text, parse_mode='HTML', reply_markup=markup)

# ===================== معالج التفاعلات (Callback Handler) =====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    data = query.data
    
    await query.answer()
    
    if is_banned(user_id):
        await query.answer("❌ أنت محظور.", show_alert=True)
        return

    if data in ["main_menu", "panel"]:
        await show_main_menu(update, context, chat_id, user_id)
        return

    # --- قوائم التفاعل ورشق المنصات ---
    elif data == "smm_main":
        text = "🎬 <b>اختر المنصة التي تريد زيادة التفاعل بها:</b>\n━━━━━━━━━━━━━━━━━"
        buttons = []
        row = []
        for key, platform in SMM_SERVICES.items():
            row.append(InlineKeyboardButton(platform["name"], callback_data=f"smm_platform_{key}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")])
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("smm_platform_"):
        platform_key = data.replace("smm_platform_", "")
        if platform_key in SMM_SERVICES:
            platform = SMM_SERVICES[platform_key]
            text = f"📌 <b>خدمات {platform['name']}</b>\n━━━━━━━━━━━━━━━━━\nاختر نوع الخدمة التي ترغب بها:"
            buttons = []
            for item_key, item in platform["items"].items():
                price_text = f"{item['price_per_1000']} نقطة/1000"
                buttons.append([InlineKeyboardButton(f"{item['name']} - [{price_text}]", callback_data=f"smm_item_{item_key}")])
            buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="smm_main")])
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("smm_item_"):
        item_key = data.replace("smm_item_", "")
        selected_item = None
        for p in SMM_SERVICES.values():
            if item_key in p["items"]:
                selected_item = p["items"][item_key]
                break
                
        if selected_item:
            context.user_data['selected_service'] = selected_item
            context.user_data['mode'] = 'awaiting_smm_link'
            text = f"""📦 <b>خدمة: {selected_item['name']}</b>
━━━━━━━━━━━━━━━━━
💰 <b>السعر لكل 1000:</b> <code>{selected_item['price_per_1000']}</code> نقطة
📉 <b>الحد الأدنى:</b> {selected_item['min']}
📈 <b>الحد الأقصى:</b> {selected_item['max']}

🔗 <b>يرجى إرسال رابط الحساب أو المنشور الآن:</b>"""
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data="smm_main")]]))

    # --- إدارة الكروت والتحويلات ---
    elif data == "redeem_coupon":
        await query.edit_message_text("💳 <b>أرسل كود الكارت/الكوبون الخاص بك الآن:</b>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data="main_menu")]]))
        context.user_data['mode'] = 'awaiting_coupon'

    elif data == "transfer_balance":
        await query.edit_message_text("🔢 <b>أرسل آيدي (ID) الشخص المراد تحويل الرصيد إليه:</b>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data="main_menu")]]))
        context.user_data['mode'] = 'awaiting_transfer_id'

    elif data == "my_orders":
        orders = get_user_orders(user_id)
        if not orders:
            text = "📭 <b>لا توجد لديك طلبات مسجلة حالياً.</b>"
        else:
            text = "📋 <b>أحدث طلباتك المسجلة:</b>\n━━━━━━━━━━━━━━━━━\n"
            for o in orders:
                text += f"🔹 <code>#{o.get('id')}</code> | {o.get('service')} | الكمية: {o.get('quantity')}\n"
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))

    elif data == "referral_menu":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        invites = get_user_data(user_id).get('invite', 0)
        text = f"🎁 <b>نظام كسب الرصيد المجاني عبر الإحالة</b>\n━━━━━━━━━━━━━━━━━\nشارك رابط الدعوة وحصل على نقاط عند انضمام أي شخص:\n\n<code>{ref_link}</code>\n\n👥 <b>عدد مدعويك:</b> {invites}"
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))

    elif data == "recharge_info":
        info = read_text('data/recharge_info.txt', '💰 لشحن الرصيد تواصل مع الدعم الفني المباشر.')
        await query.edit_message_text(f"💳 <b>معلومات الشحن</b>\n━━━━━━━━━━━━━━━━━\n{info}", parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))

    elif data == "support_info":
        await query.edit_message_text(f"📞 <b>الدعم الفني والخدمة</b>\n━━━━━━━━━━━━━━━━━\nللاستفسارات والخدمات:\n👤 @{SUPPORT_USERNAME}", parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))

    elif data == "admin_panel" and is_admin(user_id):
        users_count = len(get_users_list())
        text = f"⚙️ <b>لوحة الإدارة العليا</b>\n━━━━━━━━━━━━━━━━━\n👥 عدد المستخدمين: {users_count}"
        buttons = [
            [InlineKeyboardButton("📢 إذاعة عامة", callback_data="admin_broadcast")],
            [InlineKeyboardButton("➕ إنشاء كوبون", callback_data="admin_add_coupon")],
            [InlineKeyboardButton("🔙 رجوع للبوت", callback_data="main_menu")]
        ]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "admin_add_coupon" and is_admin(user
