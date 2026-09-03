
import os
import json
import time
import logging
import random
import re
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

try:
    import requests
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot==20.7", "requests==2.31.0"])
    import requests
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8841683948:AAFkBeKbIW3S1NQL8eYWdNfgTV946re27Fs"
ADMIN_ID = 6148029159
SUPPORT_USERNAME = "SMSQusai"
WEBHOOK_SECRET = "f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2"
RATE_LIMIT = 0.6
CURL_TIMEOUT = 10

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def read_json(filepath, default=None):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def write_json(filepath, data):
    try:
        ensure_dir(os.path.dirname(filepath))
        temp = f"{filepath}.tmp"
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp, filepath)
        return True
    except:
        return False

def read_text(filepath, default=""):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return default

def write_text(filepath, content):
    try:
        ensure_dir(os.path.dirname(filepath))
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except:
        return False

def append_text(filepath, content):
    try:
        ensure_dir(os.path.dirname(filepath))
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(content)
        return True
    except:
        return False

def bot_api(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        if data:
            response = requests.post(url, data=data, timeout=CURL_TIMEOUT)
        else:
            response = requests.get(url, timeout=CURL_TIMEOUT)
        return response.json()
    except:
        return None

def wallet_log(user_id, action_type, amount, note="", extra=None):
    entry = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': str(user_id),
        'type': action_type,
        'amount': amount,
        'note': note,
        **(extra or {})
    }
    append_text('data/wallet_ledger.log', json.dumps(entry, ensure_ascii=False) + '\n')

def wallet_history(user_id, limit=10):
    try:
        with open('data/wallet_ledger.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        user_id = str(user_id)
        history = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if str(entry.get('user_id')) == user_id:
                    history.append(entry)
                    if len(history) >= limit:
                        break
            except:
                continue
        return history
    except:
        return []

def order_create(order_id, user_id, service_id, link, quantity, coin):
    record = {
        'id': str(order_id),
        'user_id': str(user_id),
        'service': str(service_id),
        'link': link,
        'quantity': quantity,
        'coin': coin,
        'status': 'pending',
        'created_at': int(time.time())
    }
    try:
        append_text('akl/orders.txt', json.dumps(record, ensure_ascii=False) + '\n')
        return True
    except:
        return False

def order_update_status(order_id, status):
    try:
        with open('akl/orders.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        order_id = str(order_id)
        updated = []
        found = False
        for line in lines:
            try:
                order = json.loads(line)
                if str(order.get('id')) == order_id:
                    order['status'] = status
                    found = True
                updated.append(json.dumps(order, ensure_ascii=False))
            except:
                updated.append(line.strip())
        if found:
            write_text('akl/orders.txt', '\n'.join(updated) + '\n')
            return True
        return False
    except:
        return False

def get_user_orders(user_id, limit=10):
    try:
        with open('akl/orders.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        user_id = str(user_id)
        orders = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                order = json.loads(line)
                if str(order.get('user_id')) == user_id:
                    orders.append(order)
                    if len(orders) >= limit:
                        break
            except:
                continue
        return orders
    except:
        return []

def get_all_orders_stats():
    stats = {
        'total': 0,
        'revenue': 0,
        'pending': 0,
        'processing': 0,
        'completed': 0,
        'canceled': 0,
        'today': 0
    }
    try:
        with open('akl/orders.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        today = datetime.now().strftime('%Y-%m-%d')
        for line in lines:
            if not line.strip():
                continue
            try:
                order = json.loads(line)
                stats['total'] += 1
                stats['revenue'] += float(order.get('coin', 0))
                status = order.get('status', 'pending')
                if status in stats:
                    stats[status] += 1
                if datetime.fromtimestamp(order.get('created_at', 0)).strftime('%Y-%m-%d') == today:
                    stats['today'] += 1
            except:
                continue
        return stats
    except:
        return stats

def coupons_read():
    return read_json('data/coupons.json', {})

def coupons_write(coupons):
    return write_json('data/coupons.json', coupons)

def coupon_create(code, coupon_type, value, max_uses=0):
    code = code.upper().strip()
    if not re.match(r'^[A-Z0-9_\-]{2,30}$', code):
        return None
    if coupon_type not in ['charge', 'discount']:
        return None
    if value <= 0 or (coupon_type == 'discount' and value > 100):
        return None
    max_uses = max(0, max_uses)
    coupons = coupons_read()
    coupons[code] = {
        'code': code,
        'type': coupon_type,
        'value': value,
        'max_uses': max_uses,
        'used_by': [],
        'created_at': int(time.time()),
        'active': True
    }
    coupons_write(coupons)
    return coupons[code]

def coupon_redeem(code, user_id):
    code = code.upper().strip()
    user_id = str(user_id)
    coupons = coupons_read()
    if code not in coupons:
        return {'ok': False, 'message': 'الكود غير صحيح ❌', 'coupon': None}
    coupon = coupons[code]
    if not coupon.get('active', False):
        return {'ok': False, 'message': 'هذا الكود غير مفعل حالياً ❌', 'coupon': None}
    if user_id in coupon.get('used_by', []):
        return {'ok': False, 'message': 'لقد استخدمت هذا الكود من قبل ❌', 'coupon': None}
    if coupon.get('max_uses', 0) > 0 and len(coupon.get('used_by', [])) >= coupon['max_uses']:
        return {'ok': False, 'message': 'انتهت عدد مرات استخدام هذا الكود ❌', 'coupon': None}
    coupons[code]['used_by'].append(user_id)
    coupons_write(coupons)
    return {'ok': True, 'message': 'تم استخدام الكود بنجاح ✅', 'coupon': coupons[code]}

def get_user_data(user_id):
    return read_json(f'data/{user_id}.json', {})

def save_user_data(user_id, data):
    return write_json(f'data/{user_id}.json', data)

def get_user_coin(user_id):
    data = get_user_data(user_id)
    return float(data.get('userfild', {}).get(str(user_id), {}).get('coin', 0))

def set_user_coin(user_id, amount):
    data = get_user_data(user_id)
    if 'userfild' not in data:
        data['userfild'] = {}
    if str(user_id) not in data['userfild']:
        data['userfild'][str(user_id)] = {}
    data['userfild'][str(user_id)]['coin'] = str(amount)
    return save_user_data(user_id, data)

def add_user_coin(user_id, amount):
    current = get_user_coin(user_id)
    new_amount = current + amount
    set_user_coin(user_id, new_amount)
    return new_amount

def deduct_user_coin(user_id, amount):
    current = get_user_coin(user_id)
    if current < amount:
        return False
    new_amount = current - amount
    set_user_coin(user_id, new_amount)
    return True

def get_admin_list():
    data = read_json('sudo.json', {})
    return data.get('info', {}).get('admins', [ADMIN_ID])

def is_admin(user_id):
    return user_id == ADMIN_ID or user_id in get_admin_list()

def get_members_count():
    try:
        with open('sudo/member.txt', 'r') as f:
            return len([l for l in f.read().split('\n') if l.strip()])
    except:
        return 0

def get_banned_users():
    try:
        with open('sudo/ban.txt', 'r') as f:
            return [l.strip() for l in f.read().split('\n') if l.strip()]
    except:
        return []

def is_banned(user_id):
    return str(user_id) in get_banned_users()

def get_user_name(user):
    return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or str(user.id)

def get_username_or_id(user):
    return f"@{user.username}" if user.username else str(user.id)

def format_balance_text(user_id, update):
    coin = get_user_coin(user_id)
    currency = read_text('edid/cdiamlaadf.txt', 'نقاط')
    spent = get_user_spent(user_id)
    invite_count = get_user_invite_count(user_id)
    return f"""🎛 <b>رصيدك:</b> {coin} {currency}
💰 <b>المصروف:</b> {spent} {currency}
👥 <b>المدعوون:</b> {invite_count}
🆔 <b>ايديك:</b> <code>{user_id}</code>"""

def get_user_spent(user_id):
    try:
        with open(f'amr/{user_id}/coirlt.txt', 'r') as f:
            return int(f.read())
    except:
        return 0

def get_user_invite_count(user_id):
    data = get_user_data(user_id)
    return int(data.get('userfild', {}).get(str(user_id), {}).get('invite', 0))

def get_users_count():
    data = read_json('data/user.json', {})
    return len(data.get('userlist', []))

def get_today_users():
    today = datetime.now().strftime('%A')
    try:
        with open(f'data/{today}.txt', 'r') as f:
            return len([l for l in f.read().split('\n') if l.strip()])
    except:
        return 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    
    if is_banned(user_id):
        await update.message.reply_text("❌ انت محظور من استخدام البوت")
        return
    
    data = read_json('data/user.json', {})
    if 'userlist' not in data:
        data['userlist'] = []
    if user_id not in data['userlist']:
        data['userlist'].append(user_id)
        write_json('data/user.json', data)
    
    if not os.path.exists(f'data/{user_id}.json'):
        save_user_data(user_id, {'userfild': {str(user_id): {'coin': '0', 'invite': '0'}}})
    
    text = update.message.text
    if text and text.startswith('/start ') and not text.startswith('/start code_'):
        ref_id = text.replace('/start ', '').strip()
        if ref_id.isdigit() and int(ref_id) != user_id:
            ref_id = int(ref_id)
            if ref_id != user_id:
                inviter_data = get_user_data(ref_id)
                if 'userfild' not in inviter_data:
                    inviter_data['userfild'] = {}
                if str(ref_id) not in inviter_data['userfild']:
                    inviter_data['userfild'][str(ref_id)] = {}
                invite_count = int(inviter_data.get('userfild', {}).get(str(ref_id), {}).get('invite', 0))
                inviter_data['userfild'][str(ref_id)]['invite'] = str(invite_count + 1)
                coins_start = int(read_text('edid/coinsstart.txt', '15'))
                current_coin = float(inviter_data.get('userfild', {}).get(str(ref_id), {}).get('coin', 0))
                inviter_data['userfild'][str(ref_id)]['coin'] = str(current_coin + coins_start)
                save_user_data(ref_id, inviter_data)
                wallet_log(ref_id, 'gift', coins_start, f"مكافأة دعوة مستخدم جديد")
                await bot_api('sendMessage', {'chat_id': ref_id, 'text': f"لقد حصلت على {coins_start} نقاط من دعوة مستخدم جديد"})
                
                user_data = get_user_data(user_id)
                if 'userfild' not in user_data:
                    user_data['userfild'] = {}
                if str(user_id) not in user_data['userfild']:
                    user_data['userfild'][str(user_id)] = {}
                user_data['userfild'][str(user_id)]['inviter'] = str(ref_id)
                save_user_data(user_id, user_data)
    
    await show_main_menu(update, context, chat_id, user_id)

async def show_main_menu(update, context, chat_id, user_id):
    coin = get_user_coin(user_id)
    currency = read_text('edid/cdiamlaadf.txt', 'نقاط')
    balance_text = format_balance_text(user_id, update)
    
    buttons = [
        [InlineKeyboardButton("🎬 بدء تلبية رشق جديدة", callback_data="takecoinn")],
        [InlineKeyboardButton("📇 أرقام وهمية", callback_data="ne_fake_numbers"), InlineKeyboardButton("🎁 شحن الألعاب", callback_data="ne_game_topup")],
        [InlineKeyboardButton("⭐ خدماتي المفضلة", callback_data="ne_favorites"), InlineKeyboardButton("📚 خدمات مجانية", callback_data="ne_free_services")],
        [InlineKeyboardButton("💳 شحن كرت", callback_data="amr6"), InlineKeyboardButton("💰 إشحن رصيدك", callback_data="amr2")],
        [InlineKeyboardButton("🔑 مفتاح API 🌐", callback_data="ne_api_key")],
        [InlineKeyboardButton("📋 طلب تعويض", callback_data="ne_compensation"), InlineKeyboardButton("🔄 تغيير العملة", callback_data="ne_currency")],
        [InlineKeyboardButton("🔄 تحويل رصيد", callback_data="sendcoin"), InlineKeyboardButton("➕ رصيد مجاني", callback_data="ne_referral")],
        [InlineKeyboardButton("⚙️ المزيد والاعدادات", callback_data="ne_more")],
        [InlineKeyboardButton("📞 الدعم الفني", callback_data="ne_support")],
    ]
    
    if is_admin(user_id):
        buttons.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="emperor_panel")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            balance_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        start_text = read_text('start.txt', f"✰︙ مرحبا بك في بوت الرشق ✨\n{balance_text}")
        start_text = start_text.replace('#id', str(user_id)).replace('#points', str(coin))
        await update.message.reply_text(
            start_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    await show_main_menu(update, context, chat_id, user_id)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    data = query.data
    
    if is_banned(user_id):
        await query.answer("❌ انت محظور من استخدام البوت", show_alert=True)
        return
    
    if data == "panel":
        await show_main_menu(update, context, chat_id, user_id)
        return
    
    if data == "takecoinn":
        await show_services(update, context, chat_id, user_id)
        return
    
    if data == "accont":
        await show_account(update, context, chat_id, user_id)
        return
    
    if data == "amr1":
        text = read_text('edid/msgasro.txt', "شروط استخدام البوت")
        buttons = [[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "amr2":
        text = read_text('edid/msgasar.txt', "💰 أسعار الشحن\n\nتواصل مع الوكيل للشحن")
        buttons = [[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "amr4":
        await query.edit_message_text("🔢 ارسل ايدي الطلب:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]))
        context.user_data['mode'] = 'check_order'
        return
    
    if data == "amr5":
        orders = get_user_orders(user_id, 10)
        if not orders:
            text = "📭 لا توجد طلبات مسجلة باسمك حتى الآن"
        else:
            status_map = {'pending': '⏳ قيد الانتظار', 'processing': '⚙️ قيد التنفيذ', 'completed': '✅ مكتمل', 'canceled': '❌ ملغي'}
            text = "📮 آخر طلباتك:\n━━━━━━━━━━━━━━━━━\n"
            for order in orders[:10]:
                status = status_map.get(order.get('status', 'pending'), order.get('status', '—'))
                text += f"🔢 #{order.get('id')} | 🛠 {order.get('service')} | {status}\n"
        buttons = [[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "amr6":
        await query.edit_message_text("💳 ارسل الكود:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]))
        context.user_data['mode'] = 'redeem_code'
        return
    
    if data == "sendcoin":
        await query.edit_message_text("🔢 ارسل ايدي الشخص:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]))
        context.user_data['mode'] = 'send_coin_user'
        return
    
    if data == "ne_referral":
        await show_referral(update, context, chat_id, user_id)
        return
    
    if data == "ne_currency":
        await show_currency_menu(update, context, chat_id, user_id)
        return
    
    if data == "ne_support":
        await show_support(update, context, chat_id, user_id)
        return
    
    if data == "ne_more":
        buttons = [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="sec_stats"), InlineKeyboardButton("🙋‍♂️ طلباتي", callback_data="amr5")],
            [InlineKeyboardButton("💬 الشروط والتعليمات", callback_data="amr1")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="panel")]
        ]
        await query.edit_message_text("⚙️ المزيد والإعدادات\n\nاختر الخيار المناسب:", reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "sec_stats":
        stats = get_all_orders_stats()
        users = get_users_count()
        today_users = get_today_users()
        text = f"""📊 <b>إحصائيات البوت</b>
━━━━━━━━━━━━━━━━━
👥 عدد المستخدمين: {users}
🔥 المتفاعلين اليوم: {today_users}
📦 إجمالي الطلبات: {stats['total']}
💰 الأرباح: {stats['revenue']:.2f} نقاط
━━━━━━━━━━━━━━━━━
⏳ قيد الانتظار: {stats['pending']}
⚙️ قيد التنفيذ: {stats['processing']}
✅ مكتملة: {stats['completed']}
❌ ملغية: {stats['canceled']}"""
        buttons = [[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data.startswith("ne_cur_"):
        currencies = {
            'ne_cur_sar': 'ريال سعودي (ر.س)',
            'ne_cur_usd': 'دولار ($)',
            'ne_cur_yer_n': 'ريال يمني قديم (ر.ي.ش)',
            'ne_cur_yer_s': 'ريال يمني/جنوب (ر.ي.ج)',
            'ne_cur_egp': 'جنية مصري (ج.م)',
            'ne_cur_iqd': 'دينار عراقي (د.ع)',
            'ne_cur_p': 'P'
        }
        if data in currencies:
            user_data = get_user_data(user_id)
            if 'userfild' not in user_data:
                user_data['userfild'] = {}
            if str(user_id) not in user_data['userfild']:
                user_data['userfild'][str(user_id)] = {}
            user_data['userfild'][str(user_id)]['currency'] = currencies[data]
            save_user_data(user_id, user_data)
            await query.answer(f"✅ تم تعيين العملة: {currencies[data]}", show_alert=True)
            await show_main_menu(update, context, chat_id, user_id)
        return
    
    if data == "ne_api_key":
        user_data = get_user_data(user_id)
        if 'userfild' not in user_data:
            user_data['userfild'] = {}
        if str(user_id) not in user_data['userfild']:
            user_data['userfild'][str(user_id)] = {}
        api_key = user_data['userfild'][str(user_id)].get('api_key', '')
        if not api_key:
            api_key = f"RQ-{os.urandom(16).hex().upper()}"
            user_data['userfild'][str(user_id)]['api_key'] = api_key
            save_user_data(user_id, user_data)
        buttons = [
            [InlineKeyboardButton("♻️ توليد مفتاح جديد", callback_data="ne_api_key_regen")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="panel")]
        ]
        await query.edit_message_text(f"🔑 <b>مفتاح API الخاص بك:</b>\n<code>{api_key}</code>\n\n⚠️ لا تشارك هذا المفتاح مع أي شخص.", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "ne_api_key_regen":
        user_data = get_user_data(user_id)
        if 'userfild' not in user_data:
            user_data['userfild'] = {}
        if str(user_id) not in user_data['userfild']:
            user_data['userfild'][str(user_id)] = {}
        user_data['userfild'][str(user_id)]['api_key'] = f"RQ-{os.urandom(16).hex().upper()}"
        save_user_data(user_id, user_data)
        await query.answer("✅ تم توليد مفتاح جديد", show_alert=True)
        await handle_callback(update, context)
        return
    
    if data == "ne_compensation":
        await query.edit_message_text("📋 يرجى إرسال رقم الطلب وسبب التعويض في رسالة واحدة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]))
        context.user_data['mode'] = 'compensation'
        return
    
    if data == "emperor_panel" and is_admin(user_id):
        await show_admin_panel(update, context, chat_id, user_id)
        return
    
    if data == "emperor_stats" and is_admin(user_id):
        stats = get_all_orders_stats()
        users = get_users_count()
        banned = len(get_banned_users())
        text = f"""📊 <b>لوحة الإحصائيات المباشرة</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 إجمالي المستخدمين: {users}
📦 إجمالي الطلبات: {stats['total']}
💰 الأرباح: {stats['revenue']:.2f} نقاط
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ قيد الانتظار: {stats['pending']}
⚙️ قيد التنفيذ: {stats['processing']}
✅ مكتملة: {stats['completed']}
❌ ملغية: {stats['canceled']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 المحظورين: {banned}"""
        buttons = [
            [InlineKeyboardButton("🚫 حظر عضو", callback_data="ban"), InlineKeyboardButton("✅ إلغاء حظر", callback_data="unban")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]
        ]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "emperor_coupons" and is_admin(user_id):
        buttons = [
            [InlineKeyboardButton("➕ إنشاء كوبون شحن", callback_data="emperor_cp_new_charge")],
            [InlineKeyboardButton("➕ إنشاء كوبون خصم", callback_data="emperor_cp_new_discount")],
            [InlineKeyboardButton("🔎 بحث عن كوبون", callback_data="emperor_cp_search")],
            [InlineKeyboardButton("📃 عرض الكوبونات", callback_data="emperor_cp_list")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]
        ]
        await query.edit_message_text("🎫 إدارة الكوبونات\n\nاختر العملية:", reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data.startswith("emperor_cp_new_") and is_admin(user_id):
        coupon_type = 'charge' if 'charge' in data else 'discount'
        context.user_data['mode'] = f'create_coupon_{coupon_type}'
        text = "أرسل بيانات الكوبون بالصيغة التالية:\nCODE القيمة الحد_الأقصى\nمثال: WELCOME10 10 0\n(0 = غير محدود)"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_coupons")]]))
        return
    
    if data == "emperor_cp_search" and is_admin(user_id):
        context.user_data['mode'] = 'search_coupon'
        await query.edit_message_text("🔎 أرسل كود الكوبون:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_coupons")]]))
        return
    
    if data == "emperor_cp_list" and is_admin(user_id):
        coupons = coupons_read()
        if not coupons:
            text = "📃 لا توجد كوبونات"
        else:
            text = f"📃 قائمة الكوبونات ({len(coupons)}):\n━━━━━━━━━━━━━━━━━\n"
            for code, coupon in list(coupons.items())[:25]:
                status = '✅' if coupon.get('active') else '❌'
                used = len(coupon.get('used_by', []))
                max_uses = coupon.get('max_uses', 0) or '∞'
                text += f"{status} <code>{code}</code> | {coupon['type']} | {coupon['value']} | {used}/{max_uses}\n"
        buttons = [[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_coupons")]]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data.startswith("emperor_cp_disable_") and is_admin(user_id):
        code = data.replace("emperor_cp_disable_", "")
        coupons = coupons_read()
        if code in coupons:
            coupons[code]['active'] = False
            coupons_write(coupons)
            await query.answer(f"✅ تم تعطيل الكوبون {code}", show_alert=True)
        else:
            await query.answer("❌ الكوبون غير موجود", show_alert=True)
        return
    
    if data in ["ban", "unban"] and is_admin(user_id):
        action = "حظر" if data == "ban" else "الغاء حظر"
        context.user_data['mode'] = data
        await query.edit_message_text(f"🔢 ارسل ايدي العضو ل{action}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "unbanall" and is_admin(user_id):
        write_text('sudo/ban.txt', '')
        await query.answer("✅ تم مسح جميع المحظورين", show_alert=True)
        return
    
    if data.startswith("deletchannel") and is_admin(user_id):
        channel_id = data.replace("deletchannel ", "")
        sudo_data = read_json('sudo.json', {})
        if 'info' in sudo_data and 'channel' in sudo_data['info'] and channel_id in sudo_data['info']['channel']:
            del sudo_data['info']['channel'][channel_id]
            write_json('sudo.json', sudo_data)
            await query.answer("✅ تم حذف القناة", show_alert=True)
        return
    
    if data == "addchannel" and is_admin(user_id):
        context.user_data['mode'] = 'add_channel'
        await query.edit_message_text("ارسل معرف القناة (مثل: @channel) أو قم بتوجيه منشور من القناة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "viwechannel" and is_admin(user_id):
        sudo_data = read_json('sudo.json', {})
        channels = sudo_data.get('info', {}).get('channel', {})
        if not channels:
            text = "📭 لا توجد قنوات اشتراك إجباري"
        else:
            text = "📋 قنوات الاشتراك الإجباري:\n━━━━━━━━━━━━━━━━━\n"
            for id, ch in channels.items():
                text += f"📌 {ch.get('name', 'بدون اسم')}\n🆔 {ch.get('user', 'خاص')}\n━━━━━━━━━━━━━━━━━\n"
        buttons = [[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "delchannel" and is_admin(user_id):
        sudo_data = read_json('sudo.json', {})
        channels = sudo_data.get('info', {}).get('channel', {})
        if not channels:
            await query.answer("❌ لا توجد قنوات لحذفها", show_alert=True)
            return
        buttons = []
        for id, ch in channels.items():
            buttons.append([InlineKeyboardButton(f"🚫 {ch.get('name', 'بدون اسم')}", callback_data=f"deletchannel {id}")])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")])
        await query.edit_message_text("اختر القناة لحذفها:", reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "silk" and is_admin(user_id):
        sudo_data = read_json('sudo.json', {})
        if 'info' not in sudo_data:
            sudo_data['info'] = {}
        current = sudo_data['info'].get('silk', '✅')
        sudo_data['info']['silk'] = '❌' if current == '✅' else '✅'
        write_json('sudo.json', sudo_data)
        await query.answer(f"✅ تم تغيير الحالة إلى {sudo_data['info']['silk']}", show_alert=True)
        return
    
    if data == "tnbih" and is_admin(user_id):
        sudo_data = read_json('sudo.json', {})
        if 'info' not in sudo_data:
            sudo_data['info'] = {}
        current = sudo_data['info'].get('tnbih', '✅')
        sudo_data['info']['tnbih'] = '❌' if current == '✅' else '✅'
        write_json('sudo.json', sudo_data)
        await query.answer(f"✅ تم تغيير الحالة إلى {sudo_data['info']['tnbih']}", show_alert=True)
        return
    
    if data == "fwrmember" and is_admin(user_id):
        sudo_data = read_json('sudo.json', {})
        if 'info' not in sudo_data:
            sudo_data['info'] = {}
        current = sudo_data['info'].get('fwrmember', '❎')
        sudo_data['info']['fwrmember'] = '✅' if current == '❎' else '❎'
        write_json('sudo.json', sudo_data)
        await query.answer(f"✅ تم تغيير الحالة إلى {sudo_data['info']['fwrmember']}", show_alert=True)
        return
    
    if data == "klish_sil" and is_admin(user_id):
        context.user_data['mode'] = 'set_force_sub_text'
        await query.edit_message_text("أرسل نص رسالة الاشتراك الإجباري:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "addadmin" and is_admin(user_id):
        context.user_data['mode'] = 'add_admin'
        await query.edit_message_text("🔢 ارسل ايدي الأدمن الجديد:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "admins" and is_admin(user_id):
        await show_admins_menu(update, context, chat_id, user_id)
        return
    
    if data.startswith("deleteadmin") and is_admin(user_id):
        parts = data.split('#')
        if len(parts) > 1:
            admin_id = int(parts[1])
            sudo_data = read_json('sudo.json', {})
            if 'info' in sudo_data and 'admins' in sudo_data['info']:
                if admin_id in sudo_data['info']['admins']:
                    sudo_data['info']['admins'].remove(admin_id)
                    write_json('sudo.json', sudo_data)
                    await query.answer("✅ تم حذف الأدمن", show_alert=True)
        return
    
    if data == "start" and is_admin(user_id):
        context.user_data['mode'] = 'set_start_text'
        current = read_text('start.txt', 'لم يتم تعيين')
        await query.edit_message_text(f"📝 رسالة الترحيب الحالية:\n{current}\n\nأرسل النص الجديد (استخدم #id, #points, #name, #nambot):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "dcnhrc" and is_admin(user_id):
        if os.path.exists('start.txt'):
            os.remove('start.txt')
        await query.answer("✅ تم مسح رسالة الترحيب", show_alert=True)
        return
    
    if data == "msg_asar" and is_admin(user_id):
        context.user_data['mode'] = 'set_price_text'
        await query.edit_message_text("💰 أرسل نص رسالة الأسعار:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "add_msg_sro" and is_admin(user_id):
        context.user_data['mode'] = 'set_terms_text'
        await query.edit_message_text("📜 أرسل نص الشروط والأحكام:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "msgaspat" and is_admin(user_id):
        context.user_data['mode'] = 'set_notification_text'
        await query.edit_message_text("🔔 أرسل نص إشعار الطلب الجديد (استخدم #id, #nameService, #coinService, #numberall, #Link):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "cdiamlaadf" and is_admin(user_id):
        context.user_data['mode'] = 'set_currency'
        await query.edit_message_text("💰 أرسل اسم العملة الجديدة (مثل: نقاط, ريال, دولار):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "add_nam_bot" and is_admin(user_id):
        context.user_data['mode'] = 'set_bot_name'
        await query.edit_message_text("🤖 أرسل اسم البوت الجديد:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "add_ch_admin" and is_admin(user_id):
        context.user_data['mode'] = 'set_channel'
        await query.edit_message_text("📢 أرسل معرف القناة (مثل: @channel):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "username_admin_twasl" and is_admin(user_id):
        context.user_data['mode'] = 'set_contact'
        await query.edit_message_text("📞 أرسل معرف حساب التواصل (مثل: @username):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "coins_start" and is_admin(user_id):
        context.user_data['mode'] = 'set_referral_reward'
        await query.edit_message_text("🎁 أرسل عدد النقاط لمكافأة الدعوة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "adna_coins" and is_admin(user_id):
        context.user_data['mode'] = 'set_min_balance'
        await query.edit_message_text("💰 أرسل الحد الأدنى للنقاط لطلب التمويل:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "day_coins" and is_admin(user_id):
        context.user_data['mode'] = 'set_daily_reward'
        await query.edit_message_text("🎁 أرسل عدد نقاط الهدية اليومية:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "work_add_day" and is_admin(user_id):
        context.user_data['mode'] = 'set_transfer_min'
        await query.edit_message_text("🔄 أرسل الحد الأدنى للتحويل:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "add_cono_tmwel" and is_admin(user_id):
        context.user_data['mode'] = 'set_subscription_reward'
        await query.edit_message_text("📢 أرسل عدد نقاط الاشتراك في القناة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "add_co_tmwel" and is_admin(user_id):
        context.user_data['mode'] = 'set_member_price'
        await query.edit_message_text("👥 أرسل سعر العضو الواحد بالتمويل:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "opan_ras" and is_admin(user_id):
        write_text('edid/opan.txt', '✅')
        await query.answer("✅ تم فتح الرشق", show_alert=True)
        return
    
    if data == "off_ras" and is_admin(user_id):
        write_text('edid/opan.txt', '❌')
        await query.answer("❌ تم قفل الرشق", show_alert=True)
        return
    
    if data == "opan_tmwel" and is_admin(user_id):
        write_text('edid/tmwel.txt', '✅')
        await query.answer("✅ تم فتح التمويل", show_alert=True)
        return
    
    if data == "off_tmwel" and is_admin(user_id):
        write_text('edid/tmwel.txt', '❌')
        await query.answer("❌ تم قفل التمويل", show_alert=True)
        return
    
    if data == "opan_coadd" and is_admin(user_id):
        write_text('edid/coadd.txt', '✅')
        await query.answer("✅ تم فتح التحويل", show_alert=True)
        return
    
    if data == "off_coadd" and is_admin(user_id):
        write_text('edid/coadd.txt', '❌')
        await query.answer("❌ تم قفل التحويل", show_alert=True)
        return
    
    if data == "opan_add_day" and is_admin(user_id):
        write_text('edid/add_day.txt', '✅')
        await query.answer("✅ تم فتح الهدية اليومية", show_alert=True)
        return
    
    if data == "off_add_day" and is_admin(user_id):
        write_text('edid/add_day.txt', '❌')
        await query.answer("❌ تم قفل الهدية اليومية", show_alert=True)
        return
    
    if data == "opan_asttacbot" and is_admin(user_id):
        write_text('edid/asttacbot.txt', '✅')
        await query.answer("✅ تم فتح الإشعارات", show_alert=True)
        return
    
    if data == "off_asttacbot" and is_admin(user_id):
        write_text('edid/asttacbot.txt', '❌')
        await query.answer("❌ تم قفل الإشعارات", show_alert=True)
        return
    
    if data == "nzambot" and is_admin(user_id):
        current = read_text('edid/nzambot.txt', '❌')
        new = '❌' if current == '✅' else '✅'
        write_text('edid/nzambot.txt', new)
        await query.answer(f"✅ تم تغيير الحالة إلى {new}", show_alert=True)
        return
    
    if data == "admin_addfinance" and is_admin(user_id):
        context.user_data['mode'] = 'add_finance_channel'
        await query.edit_message_text("📢 أرسل معرف القناة (مثل: @channel):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "admin_listfinance" and is_admin(user_id):
        user_data = read_json('data/user.json', {})
        finance = user_data.get('finance', [])
        if not finance:
            text = "📭 لا توجد قنوات تمويل"
        else:
            text = "📋 قنوات التمويل:\n━━━━━━━━━━━━━━━━━\n"
            for i, ch in enumerate(finance):
                text += f"{i+1}. {ch[0]} - {ch[1]} عضو\n"
        buttons = [[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "admin_deletech" and is_admin(user_id):
        context.user_data['mode'] = 'remove_finance_channel'
        await query.edit_message_text("📢 أرسل معرف القناة لحذفها من التمويل:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "admin_sendcon" and is_admin(user_id):
        context.user_data['mode'] = 'admin_add_coins'
        await query.edit_message_text("🔢 أرسل ايدي العضو أو قم بتوجيه رسالة منه:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "admin_deletecon" and is_admin(user_id):
        context.user_data['mode'] = 'admin_remove_coins'
        await query.edit_message_text("🔢 أرسل ايدي العضو أو قم بتوجيه رسالة منه:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "admin_code" and is_admin(user_id):
        code = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=8))
        user_data = read_json('data/user.json', {})
        user_data['codecoin'] = code
        write_json('data/user.json', user_data)
        context.user_data['mode'] = 'create_code_value'
        context.user_data['code'] = code
        await query.edit_message_text(f"💳 تم إنشاء الكود: {code}\nأرسل قيمة النقاط:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "admin_bccon" and is_admin(user_id):
        context.user_data['mode'] = 'broadcast_coins'
        await query.edit_message_text("💰 أرسل عدد النقاط لإرسالها للجميع:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]]))
        return
    
    if data == "VFTGKKCSS" and is_admin(user_id):
        context.user_data['mode'] = 'set_start_text'
        await query.edit_message_text("📝 أرسل نص رسالة الترحيب (استخدم #id, #points, #name, #nambot):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="home")]]))
        return
    
    if data == "azraramr" and is_admin(user_id):
        await show_buttons_menu(update, context, chat_id, user_id)
        return
    
    if data == "zrar" and is_admin(user_id):
        await show_transparent_buttons(update, context, chat_id, user_id)
        return
    
    if data == "serzer" and is_admin(user_id):
        await show_button_names_menu(update, context, chat_id, user_id)
        return
    
    if data.startswith("serzer") and is_admin(user_id):
        button_num = data.replace("serzer", "")
        if button_num.isdigit():
            button_files = {
                '1': 'edid/aklamrnm1.txt',
                '2': 'edid/aklamrnm2.txt',
                '3': 'edid/aklamrnm3.txt',
                '4': 'edid/aklamrnm4.txt',
                '5': 'edid/aklamrnm5.txt',
                '6': 'edid/aklamrnm6.txt',
                '7': 'edid/aklamrnm7.txt',
                '8': 'edid/aklamrnm8.txt',
                '9': 'edid/aklamrnm9.txt',
                '10': 'edid/aklamrnm10.txt',
                '11': 'edid/aklamrnm11.txt'
            }
            if button_num in button_files:
                context.user_data['mode'] = f'set_button_name_{button_num}'
                await query.edit_message_text(f"✏️ أرسل الاسم الجديد للزر {button_num}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="serzer")]]))
        return
    
    if data == "redd" and is_admin(user_id):
        await show_replies_menu(update, context, chat_id, user_id)
        return
    
    if data == "add_red" and is_admin(user_id):
        context.user_data['mode'] = 'add_reply_keyword'
        await query.edit_message_text("✏️ أرسل الكلمة المفتاحية:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="redd")]]))
        return
    
    if data.startswith("add_red|") and is_admin(user_id):
        idx = data.split('|')[1]
        replies = read_json('replies.json', {})
        if 'replies' in replies and idx in replies['replies']:
            del replies['replies'][idx]
            write_json('replies.json', replies)
            await query.answer("✅ تم حذف الرد", show_alert=True)
            await show_replies_menu(update, context, chat_id, user_id)
        return
    
    if data == "addbtn" and is_admin(user_id):
        context.user_data['mode'] = 'add_button'
        await query.edit_message_text("✏️ أرسل اسم الزر:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="zrar")]]))
        return
    
    if data.startswith("delete|") and is_admin(user_id):
        idx = data.split('|')[1]
        buttons = read_json('button.json', {})
        for key in ['buttons', 'links', 'codzer']:
            if key in buttons and idx in buttons[key]:
                del buttons[key][idx]
                write_json('button.json', buttons)
                await query.answer("✅ تم حذف الزر", show_alert=True)
                await show_transparent_buttons(update, context, chat_id, user_id)
                return
    
    if data.startswith("offer|") and is_admin(user_id):
        idx = data.split('|')[1]
        buttons = read_json('button.json', {})
        if 'buttons' in buttons and idx in buttons['buttons']:
            current = buttons['buttons'][idx].get('Type', 'EditMessageText')
            types = ['EditMessageText', 'sendMessage', 'answercallbackquery']
            current_idx = types.index(current) if current in types else 0
            next_type = types[(current_idx + 1) % len(types)]
            buttons['buttons'][idx]['Type'] = next_type
            write_json('button.json', buttons)
            await query.answer(f"✅ تم تغيير النوع إلى {next_type}", show_alert=True)
        return
    
    if data == "addqsm" and is_admin(user_id):
        context.user_data['mode'] = 'add_service_category'
        await query.edit_message_text("✏️ أرسل اسم القسم الجديد:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="xdmat")]]))
        return
    
    if data.startswith("mamrmr|") and is_admin(user_id):
        category_id = data.split('|')[1]
        await show_category_services(update, context, chat_id, user_id, category_id)
        return
    
    if data.startswith("add|") and is_admin(user_id):
        category_id = data.split('|')[1]
        context.user_data['mode'] = 'add_service'
        context.user_data['category_id'] = category_id
        await query.edit_message_text("✏️ أرسل اسم الخدمة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="xdmat")]]))
        return
    
    if data.startswith("edits|") and is_admin(user_id):
        category_id = data.split('|')[1]
        await show_services_menu(update, context, chat_id, user_id, category_id)
        return
    
    if data.startswith("editss|") and is_admin(user_id):
        parts = data.split('|')
        category_id = parts[1]
        service_idx = int(parts[2])
        await show_service_edit_menu(update, context, chat_id, user_id, category_id, service_idx)
        return
    
    if data.startswith("delets|") and is_admin(user_id):
        parts = data.split('|')
        if len(parts) == 2:
            category_id = parts[1]
            akl_data = read_json('akl/akl.json', {})
            if 'IFWORK>' in akl_data:
                akl_data['IFWORK>'][category_id] = 'NOT'
                write_json('akl/akl.json', akl_data)
            await show_services_categories(update, context, chat_id, user_id)
        elif len(parts) == 3:
            category_id = parts[1]
            service_idx = int(parts[2])
            akl_data = read_json('akl/akl.json', {})
            if category_id in akl_data.get('xdmaxs', {}):
                if service_idx < len(akl_data['xdmaxs'][category_id]):
                    del akl_data['xdmaxs'][category_id][service_idx]
                    akl_data['xdmaxs'][category_id] = list(akl_data['xdmaxs'][category_id])
                    write_json('akl/akl.json', akl_data)
            await show_category_services(update, context, chat_id, user_id, category_id)
        return
    
    if data.startswith("delt|") and is_admin(user_id):
        parts = data.split('|')
        category_id = parts[1]
        service_idx = int(parts[2])
        akl_data = read_json('akl/akl.json', {})
        if category_id in akl_data.get('xdmaxs', {}):
            if service_idx < len(akl_data['xdmaxs'][category_id]):
                del akl_data['xdmaxs'][category_id][service_idx]
                akl_data['xdmaxs'][category_id] = list(akl_data['xdmaxs'][category_id])
                write_json('akl/akl.json', akl_data)
        await show_category_services(update, context, chat_id, user_id, category_id)
        return
    
    if data.startswith("setprice|") and is_admin(user_id):
        parts = data.split('|')
        category_id = parts[1]
        service_idx = int(parts[2])
        context.user_data['mode'] = f'set_service_price_{category_id}_{service_idx}'
        await query.edit_message_text("💰 أرسل سعر الخدمة (لكل 1000):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"editss|{category_id}|{service_idx}")]]))
        return
    
    if data.startswith("setid|") and is_admin(user_id):
        parts = data.split('|')
        category_id = parts[1]
        service_idx = int(parts[2])
        context.user_data['mode'] = f'set_service_id_{category_id}_{service_idx}'
        await query.edit_message_text("🔢 أرسل ايدي الخدمة من الموقع:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"editss|{category_id}|{service_idx}")]]))
        return
    
    if data.startswith("setmin|") and is_admin(user_id):
        parts = data.split('|')
        category_id = parts[1]
        service_idx = int(parts[2])
        context.user_data['mode'] = f'set_service_min_{category_id}_{service_idx}'
        await query.edit_message_text("📉 أرسل الحد الأدنى للطلب:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"editss|{category_id}|{service_idx}")]]))
        return
    
    if data.startswith("setmix|") and is_admin(user_id):
        parts = data.split('|')
        category_id = parts[1]
        service_idx = int(parts[2])
        context.user_data['mode'] = f'set_service_max_{category_id}_{service_idx}'
        await query.edit_message_text("📈 أرسل الحد الأقصى للطلب:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"editss|{category_id}|{service_idx}")]]))
        return
    
    if data.startswith("setdes|") and is_admin(user_id):
        parts = data.split('|')
        category_id = parts[1]
        service_idx = int(parts[2])
        context.user_data['mode'] = f'set_service_desc_{category_id}_{service_idx}'
        await query.edit_message_text("📝 أرسل وصف الخدمة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"editss|{category_id}|{service_idx}")]]))
        return
    
    if data.startswith("setkey|") and is_admin(user_id):
        parts = data.split('|')
        category_id = parts[1]
        service_idx = int(parts[2])
        context.user_data['mode'] = f'set_service_key_{category_id}_{service_idx}'
        await query.edit_message_text("🔑 أرسل API KEY للخدمة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"editss|{category_id}|{service_idx}")]]))
        return
    
    if data.startswith("setWeb|") and is_admin(user_id):
        parts = data.split('|')
        category_id = parts[1]
        service_idx = int(parts[2])
        context.user_data['mode'] = f'set_service_web_{category_id}_{service_idx}'
        await query.edit_message_text("🌐 أرسل رابط الموقع:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"editss|{category_id}|{service_idx}")]]))
        return
    
    if data == "home" and is_admin(user_id):
        await show_admin_panel(update, context, chat_id, user_id)
        return
    
    if data == "VISCODEV" and is_admin(user_id):
        context.user_data['mode'] = 'set_api_token'
        await query.edit_message_text("🔑 أرسل توكن API الخاص بالموقع:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="sitingbots")]]))
        return
    
    if data == "SiteDomen" and is_admin(user_id):
        context.user_data['mode'] = 'set_site_domain'
        await query.edit_message_text("🌐 أرسل رابط الموقع (مثل: api.example.com):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="sitingbots")]]))
        return
    
    if data == "sitingbots" and is_admin(user_id):
        await show_admin_panel(update, context, chat_id, user_id)
        return
    
    if data == "agbary" and is_admin(user_id):
        await show_force_sub_menu(update, context, chat_id, user_id)
        return
    
    if data == "bbcybhu" and is_admin(user_id):
        await show_broadcast_menu(update, context, chat_id, user_id)
        return
    
    if data == "sendmgddyessage" and is_admin(user_id):
        await show_stats_menu(update, context, chat_id, user_id)
        return
    
    if data == "AMAlMAL" and is_admin(user_id):
        context.user_data['mode'] = 'broadcast_text'
        await query.edit_message_text("📢 أرسل نص الإذاعة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="bbcybhu")]]))
        return
    
    if data == "AMAMALT1" and is_admin(user_id):
        context.user_data['mode'] = 'broadcast_forward'
        await query.edit_message_text("📢 أرسل الرسالة للإذاعة (سيتم توجيهها):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="bbcybhu")]]))
        return
    
    if data == "AMAMALp" and is_admin(user_id):
        context.user_data['mode'] = 'broadcast_private'
        await query.edit_message_text("📢 أرسل نص الإذاعة (للمستخدمين فقط):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="bbcybhu")]]))
        return
    
    if data == "AMAMALT2" and is_admin(user_id):
        context.user_data['mode'] = 'broadcast_forward_private'
        await query.edit_message_text("📢 أرسل الرسالة للإذاعة (سيتم توجيهها للمستخدمين فقط):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="bbcybhu")]]))
        return
    
    if data == "AMRAZLpm" and is_admin(user_id):
        context.user_data['mode'] = 'broadcast_groups'
        await query.edit_message_text("📢 أرسل نص الإذاعة (للكروبات فقط):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="bbcybhu")]]))
        return
    
    if data == "AMAMALT3" and is_admin(user_id):
        context.user_data['mode'] = 'broadcast_forward_groups'
        await query.edit_message_text("📢 أرسل الرسالة للإذاعة (سيتم توجيهها للكروبات فقط):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="bbcybhu")]]))
        return
    
    if data == "MLpAPK" and is_admin(user_id):
        write_text('gdbyj.txt', 'on')
        await query.answer("✅ تم تفعيل تثبيت الإذاعة", show_alert=True)
        return
    
    if data == "MLAPK" and is_admin(user_id):
        write_text('gdbyj.txt', 'off')
        await query.answer("❌ تم إلغاء تثبيت الإذاعة", show_alert=True)
        return
    
    if data == "xdmat" and is_admin(user_id):
        await show_services_categories(update, context, chat_id, user_id)
        return
    
    if data == "mr1" and is_admin(user_id):
        await show_apps_menu(update, context, chat_id, user_id)
        return
    
    if data == "codyser" and is_admin(user_id):
        buttons = [
            [InlineKeyboardButton("📤 رفع نسخة", callback_data="codoserue"), InlineKeyboardButton("📥 عمل نسخة", callback_data="codyseradd")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="sitingbots")]
        ]
        await query.edit_message_text("📦 نسخ الخدمات\n\nاختر العملية:", reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    if data == "codyseradd" and is_admin(user_id):
        userbot = bot_api('getMe')
        if userbot and userbot.get('ok'):
            username = userbot['result']['username']
            code = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', k=40))
            akl_data = read_json('akl/akl.json', {})
            write_json(f'{username}.tupac', {'code': code, 'data': akl_data})
            await bot_api('sendDocument', {
                'chat_id': chat_id,
                'document': open(f'{username}.tupac', 'rb'),
                'caption': f'📦 نسخة الخدمات\nالبوت: @{username}'
            })
            os.remove(f'{username}.tupac')
        return
    
    if data == "codoserue" and is_admin(user_id):
        context.user_data['mode'] = 'upload_backup'
        await query.edit_message_text("📤 أرسل ملف النسخة (.tupac):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="codyser")]]))
        return
    
    if data.startswith("open_") and is_admin(user_id):
        app = data.replace("open_", "")
        app_files = {
            'insta': ('edid/mr_insta.txt', 'edid/cood_insta.txt'),
            'tektok': ('edid/mr_tektok.txt', 'edid/cood_tektok.txt'),
            'telegram': ('edid/mr_telegram.txt', 'edid/cood_telegram.txt'),
            'yoteop': ('edid/mr_yoteop.txt', 'edid/cood_yoteop.txt'),
            'faesbook': ('edid/mr_faesbook.txt', 'edid/cood_faesbook.txt'),
            'twetr': ('edid/mr_twetr.txt', 'edid/cood_twetr.txt'),
            'free': ('edid/mr_free.txt', 'edid/cood_free.txt')
        }
        if app in app_files:
            status_file, code_file = app_files[app]
            write_text(status_file, '✅')
            code = f"bot{random.randint(0, 999999999999999)}"
            write_text(code_file, code)
            akl_data = read_json('akl/akl.json', {})
            if 'qsm' not in akl_data:
                akl_data['qsm'] = []
            if 'NAMES' not in akl_data:
                akl_data['NAMES'] = {}
            app_names = {
                'insta': 'انستغرام 💜',
                'tektok': 'تيكتوك 🖤',
                'telegram': 'تيليغرام 💙',
                'yoteop': 'يوتيوب ❤',
                'faesbook': 'فيسبوك 🤍',
                'twetr': 'تويتر 💙',
                'free': 'الخدمات المجانية 🎁'
            }
            akl_data['qsm'].append(f"{app_names[app]}-{code}")
            akl_data['NAMES'][code] = app_names[app]
            write_json('akl/akl.json', akl_data)
            await query.answer(f"✅ تم فتح {app_names[app]}", show_alert=True)
        return
    
    if data.startswith("off_") and is_admin(user_id):
        app = data.replace("off_", "")
        app_files = {
            'insta': ('edid/mr_insta.txt', 'edid/cood_insta.txt'),
            'tektok': ('edid/mr_tektok.txt', 'edid/cood_tektok.txt'),
            'telegram': ('edid/mr_telegram.txt', 'edid/cood_telegram.txt'),
            'yoteop': ('edid/mr_yoteop.txt', 'edid/cood_yoteop.txt'),
            'faesbook': ('edid/mr_faesbook.txt', 'edid/cood_faesbook.txt'),
            'twetr': ('edid/mr_twetr.txt', 'edid/cood_twetr.txt'),
            'free': ('edid/mr_free.txt', 'edid/cood_free.txt')
        }
        if app in app_files:
            status_file, code_file = app_files[app]
            write_text(status_file, '❌')
            if os.path.exists(code_file):
                os.remove(code_file)
            await query.answer(f"❌ تم قفل التطبيق", show_alert=True)
        return
    
    if data == "add_day" and is_admin(user_id):
        await daily_reward(update, context, chat_id, user_id)
        return
    
    if data == "kk":
        await daily_reward(update, context, chat_id, user_id)
        return
    
    if data == "takecoin":
        await show_channels_for_points(update, context, chat_id, user_id)
        return
    
    if data == "truechannel":
        await check_channel_subscription(update, context, chat_id, user_id)
        return
    
    if data == "nextchannel":
        await next_channel(update, context, chat_id, user_id)
        return
    
    if data == "mainchannel":
        await check_main_channel(update, context, chat_id, user_id)
        return
    
    if data == "badchannel":
        channel = context.user_data.get('current_channel', '')
        await query.answer("✅ تم إرسال البلاغ للأدمن", show_alert=True)
        await bot_api('sendMessage', {
            'chat_id': ADMIN_ID,
            'text': f"📛 بلاغ عن قناة\nالقناة: {channel}\nالمستخدم: {user_id}"
        })
        return
    
    if data.startswith("finance_"):
        channel_idx = int(data.replace("finance_", ""))
        user_data = read_json('data/user.json', {})
        finance = user_data.get('finance', [])
        if channel_idx < len(finance):
            channel_id = finance[channel_idx][0]
            channel_info = bot_api('getChat', {'chat_id': channel_id})
            if channel_info and channel_info.get('ok'):
                member = bot_api('getChatMember', {'chat_id': channel_id, 'user_id': user_id})
                if member and member.get('ok') and member['result']['status'] not in ['left', 'kicked']:
                    coin = finance[channel_idx][1]
                    add_user_coin(user_id, coin)
                    wallet_log(user_id, 'charge', coin, f"اشتراك في قناة {channel_id}")
                    await query.answer(f"✅ تم إضافة {coin} نقاط", show_alert=True)
                    await show_main_menu(update, context, chat_id, user_id)
                    return
        await query.answer("❌ تأكد من اشتراكك في القناة", show_alert=True)
        return
    
    if data == "amruu" and is_admin(user_id):
        await toggle_bot_status(update, context, chat_id, user_id)
        return
    
    if data == "FAFAF" and is_admin(user_id):
        await show_forward_menu(update, context, chat_id, user_id)
        return
    
    if data == "ppshshsj" and is_admin(user_id):
        await query.answer("📨 يتم توجيه الرسائل للأدمن", show_alert=True)
        return
    
    if data == "bajnobabiab" and is_admin(user_id):
        write_text('bajabiabi.txt', 'no')
        await query.answer("✅ تم تعطيل الرد على الرسائل", show_alert=True)
        return
    
    if data == "bysajabiab" and is_admin(user_id):
        write_text('bajabiabi.txt', 'ys')
        await query.answer("✅ تم تفعيل الرد على الرسائل", show_alert=True)
        return
    
    if data == "comm" and is_admin(user_id):
        await show_commands_menu(update, context, chat_id, user_id)
        return
    
    if data.startswith("dellll×") and is_admin(user_id):
        code = data.replace("dellll×", "")
        comm_data = read_json('comm.json', {})
        if 'com' in comm_data and code in comm_data['com']:
            del comm_data['com'][code]
            write_json('comm.json', comm_data)
            await query.answer("✅ تم حذف الاختصار", show_alert=True)
            await show_commands_menu(update, context, chat_id, user_id)
        return
    
    if data == "adddcd" and is_admin(user_id):
        context.user_data['mode'] = 'add_command'
        await query.edit_message_text("✏️ أرسل الاختصار بالصيغة:\ncommand - الوصف", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="comm")]]))
        return
    
    if data == "deleda" and is_admin(user_id):
        if os.path.exists('comm.json'):
            os.remove('comm.json')
        await bot_api('setMyCommands', {'commands': []})
        await query.answer("✅ تم مسح جميع الاختصارات", show_alert=True)
        return
    
    if data == "amr987" and is_admin(user_id):
        await query.answer("🔧 قيد التطوير", show_alert=True)
        return
    
    if data == "zerasase" and is_admin(user_id):
        current = read_text('edid/zerasase.txt', '✅')
        new = '❌' if current == '✅' else '✅'
        write_text('edid/zerasase.txt', new)
        write_text('edid/zerasaseon.txt', new)
        await query.answer(f"✅ تم تغيير حالة الأزرار الأساسية إلى {new}", show_alert=True)
        return
    
    if data == "deletaspat" and is_admin(user_id):
        if os.path.exists('edid/aspatchid1.txt'):
            os.remove('edid/aspatchid1.txt')
        await query.answer("✅ تم حذف قناة الإشعارات", show_alert=True)
        return
    
    if data == "nzambot" and is_admin(user_id):
        current = read_text('edid/nzambot.txt', '❌')
        new = '❌' if current == '✅' else '✅'
        write_text('edid/nzambot.txt', new)
        await query.answer(f"✅ تم تغيير نظام التمويل إلى {new}", show_alert=True)
        return
    
    if data.startswith("deleteadmin"):
        parts = data.split('#')
        if len(parts) > 1:
            admin_id = int(parts[1])
            sudo_data = read_json('sudo.json', {})
            if 'info' in sudo_data and 'admins' in sudo_data['info']:
                if admin_id in sudo_data['info']['admins']:
                    sudo_data['info']['admins'].remove(admin_id)
                    write_json('sudo.json', sudo_data)
                    await query.answer("✅ تم حذف الأدمن", show_alert=True)
        return
    
    if data.startswith("deletchannel"):
        channel_id = data.replace("deletchannel ", "")
        sudo_data = read_json('sudo.json', {})
        if 'info' in sudo_data and 'channel' in sudo_data['info']:
            if channel_id in sudo_data['info']['channel']:
                del sudo_data['info']['channel'][channel_id]
                write_json('sudo.json', sudo_data)
                await query.answer("✅ تم حذف القناة", show_alert=True)
        return
    
    if data == "home" and is_admin(user_id):
        await show_admin_panel(update, context, chat_id, user_id)
        return
    
    if data == "amruu" and is_admin(user_id):
        await toggle_bot_status(update, context, chat_id, user_id)
        return
    
    if data.startswith("botENT|"):
        category_id = data.split('|')[1]
        await show_category_services(update, context, chat_id, user_id, category_id)
        return
    
    if data.startswith("type|"):
        parts = data.split('|')
        if len(parts) >= 3:
            category_id = parts[1]
            service_idx = int(parts[2])
            await show_service_order(update, context, chat_id, user_id, category_id, service_idx)
        return
    
    if data.startswith("YESS|"):
        await process_order(update, context, chat_id, user_id)
        return
    
    if data.startswith("zh|"):
        button_id = data.split('|')[1]
        await show_button_details(update, context, chat_id, user_id, button_id)
        return
    
    if data.startswith("delete|"):
        button_id = data.split('|')[1]
        buttons = read_json('button.json', {})
        for key in ['buttons', 'links', 'codzer']:
            if key in buttons and button_id in buttons[key]:
                del buttons[key][button_id]
                write_json('button.json', buttons)
                await query.answer("✅ تم حذف الزر", show_alert=True)
                await show_transparent_buttons(update, context, chat_id, user_id)
                return
    
    if data.startswith("offer|"):
        button_id = data.split('|')[1]
        buttons = read_json('button.json', {})
        if 'buttons' in buttons and button_id in buttons['buttons']:
            current = buttons['buttons'][button_id].get('Type', 'EditMessageText')
            types = ['EditMessageText', 'sendMessage', 'answercallbackquery']
            current_idx = types.index(current) if current in types else 0
            next_type = types[(current_idx + 1) % len(types)]
            buttons['buttons'][button_id]['Type'] = next_type
            write_json('button.json', buttons)
            await query.answer(f"✅ تم تغيير النوع إلى {next_type}", show_alert=True)
            await show_button_details(update, context, chat_id, user_id, button_id)
        return
    
    if data == "addbtn" and is_admin(user_id):
        context.user_data['mode'] = 'add_button'
        await query.edit_message_text("✏️ أرسل اسم الزر:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="zrar")]]))
        return
    
    if data == "zrar" and is_admin(user_id):
        await show_transparent_buttons(update, context, chat_id, user_id)
        return
    
    if data.startswith("serzer") and is_admin(user_id):
        button_num = data.replace("serzer", "")
        if button_num.isdigit():
            button_files = {
                '1': 'edid/aklamrnm1.txt',
                '2': 'edid/aklamrnm2.txt',
                '3': 'edid/aklamrnm3.txt',
                '4': 'edid/aklamrnm4.txt',
                '5': 'edid/aklamrnm5.txt',
                '6': 'edid/aklamrnm6.txt',
                '7': 'edid/aklamrnm7.txt',
                '8': 'edid/aklamrnm8.txt',
                '9': 'edid/aklamrnm9.txt',
                '10': 'edid/aklamrnm10.txt',
                '11': 'edid/aklamrnm11.txt'
            }
            if button_num in button_files:
                context.user_data['mode'] = f'set_button_name_{button_num}'
                await query.edit_message_text(f"✏️ أرسل الاسم الجديد للزر {button_num}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="serzer")]]))
        return
    
    if data == "serzer" and is_admin(user_id):
        await show_button_names_menu(update, context, chat_id, user_id)
        return
    
    if data == "redd" and is_admin(user_id):
        await show_replies_menu(update, context, chat_id, user_id)
        return
    
    if data == "add_red" and is_admin(user_id):
        context.user_data['mode'] = 'add_reply_keyword'
        await query.edit_message_text("✏️ أرسل الكلمة المفتاحية:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="redd")]]))
        return
    
    if data.startswith("add_red|") and is_admin(user_id):
        idx = data.split('|')[1]
        replies = read_json('replies.json', {})
        if 'replies' in replies and idx in replies['replies']:
            del replies['replies'][idx]
            write_json('replies.json', replies)
            await query.answer("✅ تم حذف الرد", show_alert=True)
            await show_replies_menu(update, context, chat_id, user_id)
        return

async def show_admin_panel(update, context, chat_id, user_id):
    currency = read_text('edid/cdiamlaadf.txt', 'نقاط')
    bot_name = read_text('edid/nambot.txt', 'البوت')
    text = f"""⚙️ <b>لوحة تحكم الأدمن</b>
━━━━━━━━━━━━━━━━━
🤖 البوت: {bot_name}
💰 العملة: {currency}
👥 المستخدمين: {get_users_count()}
📦 الطلبات: {get_all_orders_stats()['total']}
━━━━━━━━━━━━━━━━━
اختر الإعداد الذي تريد تعديله:"""
    
    buttons = [
        [InlineKeyboardButton("📦 إدارة الخدمات", callback_data="xdmat")],
        [InlineKeyboardButton("💰 إدارة النقاط", callback_data="amruu")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="emperor_stats")],
        [InlineKeyboardButton("🎫 الكوبونات", callback_data="emperor_coupons")],
        [InlineKeyboardButton("📢 الإذاعة", callback_data="bbcybhu")],
        [InlineKeyboardButton("👥 الأدمنية", callback_data="admins")],
        [InlineKeyboardButton("📝 تعديل النصوص", callback_data="emperor_texts")],
        [InlineKeyboardButton("🛡️ الحماية", callback_data="emperor_security")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="panel")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_services(update, context, chat_id, user_id):
    akl_data = read_json('akl/akl.json', {})
    buttons = []
    
    for category in akl_data.get('qsm', []):
        parts = category.split('-')
        if len(parts) == 2:
            name, id = parts[0], parts[1]
            if akl_data.get('IFWORK>', {}).get(id) != 'NOT':
                buttons.append([InlineKeyboardButton(name, callback_data=f"botENT|{id}")])
    
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="panel")])
    
    await update.callback_query.edit_message_text(
        "🎬 اختر الخدمة التي تريدها:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_category_services(update, context, chat_id, user_id, category_id):
    akl_data = read_json('akl/akl.json', {})
    services = akl_data.get('xdmaxs', {}).get(category_id, [])
    buttons = []
    
    for idx, service in enumerate(services):
        buttons.append([InlineKeyboardButton(service, callback_data=f"type|{category_id}|{idx}")])
    
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="takecoinn")])
    
    await update.callback_query.edit_message_text(
        f"✳️ اختر الخدمة من {akl_data.get('NAMES', {}).get(category_id, 'القسم')}:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_service_order(update, context, chat_id, user_id, category_id, service_idx):
    akl_data = read_json('akl/akl.json', {})
    service_name = akl_data.get('xdmaxs', {}).get(category_id, [])[service_idx]
    price = akl_data.get('S3RS', {}).get(category_id, {}).get(str(service_idx), 1)
    min_qty = akl_data.get('min', {}).get(category_id, {}).get(str(service_idx), 100)
    max_qty = akl_data.get('mix', {}).get(category_id, {}).get(str(service_idx), 1000)
    description = akl_data.get('WSF', {}).get(category_id, {}).get(str(service_idx), "")
    
    context.user_data['order'] = {
        'category_id': category_id,
        'service_idx': service_idx,
        'service_name': service_name,
        'price': price,
        'min_qty': min_qty,
        'max_qty': max_qty
    }
    context.user_data['mode'] = 'order_qty'
    
    text = f"""✳️ اسم الخدمة: {service_name}
💰 السعر: {price * 1000} نقاط لكل 1000
📉 الحد الأدنى: {min_qty}
📈 الحد الأقصى: {max_qty}
{description}

🔢 أرسل الكمية المطلوبة:"""
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"botENT|{category_id}")]])
    )

async def process_order(update, context, chat_id, user_id):
    order_data = context.user_data.get('order', {})
    qty = context.user_data.get('order_qty', 0)
    
    if not qty or not order_data:
        await update.callback_query.answer("❌ حدث خطأ، حاول مرة أخرى", show_alert=True)
        return
    
    service_id = order_data.get('service_id', '')
    link = context.user_data.get('order_link', '')
    price = order_data.get('price', 1) * qty
    coin = get_user_coin(user_id)
    
    if coin < price:
        await update.callback_query.answer(f"❌ رصيدك غير كافٍ\nالرصيد: {coin}\nالمطلوب: {price}", show_alert=True)
        return
    
    if not deduct_user_coin(user_id, price):
        await update.callback_query.answer("❌ فشل الخصم، حاول مرة أخرى", show_alert=True)
        return
    
    wallet_log(user_id, 'deduct', price, f"طلب خدمة: {order_data.get('service_name', '')}")
    
    akl_data = read_json('akl/akl.json', {})
    site_domain = akl_data.get('sSite', '')
    api_key = akl_data.get('sVISCODEV', '')
    service_id_api = akl_data.get('IDSSS', {}).get(order_data.get('category_id', ''), {}).get(str(order_data.get('service_idx', 0)), '')
    
    order_id = None
    if site_domain and api_key and service_id_api:
        try:
            response = requests.get(
                f"https://{site_domain}/api/v2",
                params={'key': api_key, 'action': 'add', 'service': service_id_api, 'link': link, 'quantity': qty},
                timeout=CURL_TIMEOUT
            )
            result = response.json()
            if 'order' in result:
                order_id = result['order']
        except:
            pass
    
    if order_id:
        order_create(order_id, user_id, service_id_api, link, qty, price)
        
        notification_text = read_text('edid/msgaspat.txt', 
            f"✅ تم تنفيذ طلب جديد\nخدمة: {order_data.get('service_name', '')}\nالكمية: {qty}\nالسعر: {price}")
        notification_text = notification_text.replace('#id', str(user_id))
        notification_text = notification_text.replace('#nameService', order_data.get('service_name', ''))
        notification_text = notification_text.replace('#coinService', str(price))
        notification_text = notification_text.replace('#numberall', str(order_id))
        notification_text = notification_text.replace('#Link', link)
        notification_text = notification_text.replace('#numberLink', str(qty))
        
        for admin in get_admin_list():
            try:
                await bot_api('sendMessage', {'chat_id': admin, 'text': notification_text, 'parse_mode': 'HTML'})
            except:
                pass
    
    await update.callback_query.edit_message_text(
        f"✅ تم تنفيذ الطلب بنجاح!\n🆔 رقم الطلب: {order_id or 'غير متوفر'}\n📌 الخدمة: {order_data.get('service_name', '')}\n🔢 الكمية: {qty}\n💰 السعر: {price}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]])
    )
    
    context.user_data['order'] = {}
    context.user_data['order_qty'] = 0
    context.user_data['order_link'] = ''

async def show_account(update, context, chat_id, user_id):
    coin = get_user_coin(user_id)
    spent = get_user_spent(user_id)
    invite = get_user_invite_count(user_id)
    currency = read_text('edid/cdiamlaadf.txt', 'نقاط')
    
    text = f"""🗃️ <b>الحساب</b>
━━━━━━━━━━━━━━━━━
💰 الرصيد: {coin} {currency}
💸 المستخدم: {spent} {currency}
👥 المدعوون: {invite}
🆔 ايديك: <code>{user_id}</code>"""
    
    buttons = [
        [InlineKeyboardButton("💰 تجميع نقاط", callback_data="takecoinn"), InlineKeyboardButton("🎁 هدية يومية", callback_data="add_day")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="panel")]
    ]
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_referral(update, context, chat_id, user_id):
    bot_info = bot_api('getMe')
    if not bot_info or not bot_info.get('ok'):
        await update.callback_query.answer("❌ حدث خطأ", show_alert=True)
        return
    
    bot_username = bot_info['result']['username']
    link = f"https://t.me/{bot_username}?start={user_id}"
    invite_count = get_user_invite_count(user_id)
    reward = int(read_text('edid/coinsstart.txt', '15'))
    
    text = f"""👋 <b>رابط الدعوة الخاص بك</b>
━━━━━━━━━━━━━━━━━
📢 الرابط: <code>{link}</code>
🎁 المكافأة: {reward} نقاط لكل مدعو
👥 عدد المدعوين: {invite_count}
━━━━━━━━━━━━━━━━━
شارك الرابط مع أصدقائك واحصل على نقاط مجانية!"""
    
    buttons = [
        [InlineKeyboardButton("📋 نسخ الرابط", callback_data="ne_referral_copy")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="panel")]
    ]
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_currency_menu(update, context, chat_id, user_id):
    buttons = [
        [InlineKeyboardButton("🇸🇦 ريال سعودي", callback_data="ne_cur_sar")],
        [InlineKeyboardButton("🇺🇸 دولار", callback_data="ne_cur_usd")],
        [InlineKeyboardButton("🇾🇪 ريال يمني قديم", callback_data="ne_cur_yer_n")],
        [InlineKeyboardButton("🇾🇪 ريال يمني/جنوب", callback_data="ne_cur_yer_s")],
        [InlineKeyboardButton("🇪🇬 جنية مصري", callback_data="ne_cur_egp")],
        [InlineKeyboardButton("🇮🇶 دينار عراقي", callback_data="ne_cur_iqd")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="panel")]
    ]
    
    await update.callback_query.edit_message_text(
        "💰 <b>اختر العملة:</b>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_support(update, context, chat_id, user_id):
    text = f"""💁‍♂️ <b>الدعم الفني</b>
━━━━━━━━━━━━━━━━━
📌 اختر طريقة المساعدة:

1️⃣ التواصل المباشر مع فريق الدعم
2️⃣ الدعم بالذكاء الاصطناعي

📞 للتواصل المباشر: {SUPPORT_USERNAME}"""
    
    buttons = [
        [InlineKeyboardButton("💬 التواصل المباشر", callback_data="ne_support_direct")],
        [InlineKeyboardButton("🤖 الدعم الذكي", callback_data="ne_support_ai")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="panel")]
    ]
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_force_sub_menu(update, context, chat_id, user_id):
    sudo_data = read_json('sudo.json', {})
    channels = sudo_data.get('info', {}).get('channel', {})
    silk = sudo_data.get('info', {}).get('silk', '✅')
    
    text = f"""📢 <b>الاشتراك الإجباري</b>
━━━━━━━━━━━━━━━━━
📌 عدد القنوات: {len(channels)}
🖼️ وضع الماركداون: {silk}
━━━━━━━━━━━━━━━━━
اختر الإجراء المناسب:"""
    
    buttons = [
        [InlineKeyboardButton("➕ إضافة قناة", callback_data="addchannel"), InlineKeyboardButton("❌ مسح قناة", callback_data="delchannel")],
        [InlineKeyboardButton("📝 تعيين رسالة الاشتراك", callback_data="klish_sil")],
        [InlineKeyboardButton("🖼️ تغيير وضع الماركداون", callback_data="silk")],
        [InlineKeyboardButton("📋 عرض القنوات", callback_data="viwechannel")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]
    ]
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_broadcast_menu(update, context, chat_id, user_id):
    text = f"""📢 <b>الإذاعة</b>
━━━━━━━━━━━━━━━━━
اختر نوع الإذاعة:"""
    
    buttons = [
        [InlineKeyboardButton("📨 إذاعة نصية للكل", callback_data="AMAlMAL"), InlineKeyboardButton("📨 إذاعة توجيه للكل", callback_data="AMAMALT1")],
        [InlineKeyboardButton("📨 إذاعة للمستخدمين فقط", callback_data="AMAMALp"), InlineKeyboardButton("📨 إذاعة توجيه للمستخدمين", callback_data="AMAMALT2")],
        [InlineKeyboardButton("📨 إذاعة للكروبات", callback_data="AMRAZLpm"), InlineKeyboardButton("📨 إذاعة توجيه للكروبات", callback_data="AMAMALT3")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]
    ]
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_stats_menu(update, context, chat_id, user_id):
    stats = get_all_orders_stats()
    users = get_users_count()
    banned = len(get_banned_users())
    today = get_today_users()
    
    text = f"""📊 <b>الإحصائيات</b>
━━━━━━━━━━━━━━━━━
👥 المستخدمين: {users}
🔥 المتفاعلين اليوم: {today}
🚫 المحظورين: {banned}
━━━━━━━━━━━━━━━━━
📦 الطلبات الكلية: {stats['total']}
💰 الأرباح: {stats['revenue']:.2f}
━━━━━━━━━━━━━━━━━
⏳ قيد الانتظار: {stats['pending']}
⚙️ قيد التنفيذ: {stats['processing']}
✅ مكتملة: {stats['completed']}
❌ ملغية: {stats['canceled']}"""
    
    buttons = [
        [InlineKeyboardButton("🚫 حظر عضو", callback_data="ban"), InlineKeyboardButton("✅ إلغاء حظر", callback_data="unban")],
        [InlineKeyboardButton("🧹 مسح المحظورين", callback_data="unbanall")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")]
    ]
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_forward_menu(update, context, chat_id, user_id):
    sudo_data = read_json('sudo.json', {})
    fwrmember = sudo_data.get('info', {}).get('fwrmember', '❎')
    
    buttons = [
        [InlineKeyboardButton(f"📨 نوع التوجيه: {fwrmember}", callback_data="fwrmember")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="home")]
    ]
    
    await update.callback_query.edit_message_text(
        "📨 <b>توجيه الرسائل</b>\n\nجميع الرسائل التي تصل للبوت سيتم توجيهها للأدمن",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_admins_menu(update, context, chat_id, user_id):
    sudo_data = read_json('sudo.json', {})
    admins = sudo_data.get('info', {}).get('admins', [])
    
    text = f"""👮‍♀️ <b>الأدمنية</b>
━━━━━━━━━━━━━━━━━
📌 عدد الأدمنية: {len(admins)}
━━━━━━━━━━━━━━━━━
يمكنك إضافة أو حذف الأدمنية"""
    
    buttons = []
    for admin in admins:
        if admin != ADMIN_ID:
            buttons.append([InlineKeyboardButton(f"👤 {admin}", callback_data=f"deleteadmin {admin}#{admin}")])
    
    buttons.append([InlineKeyboardButton("➕ إضافة أدمن", callback_data="addadmin")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")])
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_services_categories(update, context, chat_id, user_id):
    akl_data = read_json('akl/akl.json', {})
    buttons = []
    
    for category in akl_data.get('qsm', []):
        parts = category.split('-')
        if len(parts) == 2:
            name, id = parts[0], parts[1]
            if akl_data.get('IFWORK>', {}).get(id) != 'NOT':
                buttons.append([InlineKeyboardButton(name, callback_data=f"edits|{id}")])
    
    buttons.append([InlineKeyboardButton("➕ إضافة قسم", callback_data="addqsm")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="xdmat")])
    
    await update.callback_query.edit_message_text(
        "📦 <b>إدارة الخدمات</b>\n\nاختر القسم لإدارته:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_apps_menu(update, context, chat_id, user_id):
    apps = {
        'insta': read_text('edid/mr_insta.txt', '❌'),
        'tektok': read_text('edid/mr_tektok.txt', '❌'),
        'telegram': read_text('edid/mr_telegram.txt', '❌'),
        'yoteop': read_text('edid/mr_yoteop.txt', '❌'),
        'faesbook': read_text('edid/mr_faesbook.txt', '❌'),
        'twetr': read_text('edid/mr_twetr.txt', '❌'),
        'free': read_text('edid/mr_free.txt', '❌')
    }
    
    app_names = {
        'insta': 'انستغرام 💜',
        'tektok': 'تيكتوك 🖤',
        'telegram': 'تيليغرام 💙',
        'yoteop': 'يوتيوب ❤',
        'faesbook': 'فيسبوك 🤍',
        'twetr': 'تويتر 💙',
        'free': 'المجانية 🎁'
    }
    
    buttons = []
    for key, status in apps.items():
        buttons.append([
            InlineKeyboardButton(f"{app_names[key]}: {status}", callback_data="null"),
            InlineKeyboardButton("فتح", callback_data=f"open_{key}"),
            InlineKeyboardButton("قفل", callback_data=f"off_{key}")
        ])
    
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="xdmat")])
    
    await update.callback_query.edit_message_text(
        "📱 <b>إدارة التطبيقات</b>\n\nاختر التطبيق للتحكم به:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_services_menu(update, context, chat_id, user_id, category_id):
    akl_data = read_json('akl/akl.json', {})
    services = akl_data.get('xdmaxs', {}).get(category_id, [])
    category_name = akl_data.get('NAMES', {}).get(category_id, 'القسم')
    
    text = f"📦 <b>خدمات {category_name}</b>\n━━━━━━━━━━━━━━━━━\n"
    for idx, service in enumerate(services):
        text += f"{idx+1}. {service}\n"
    
    buttons = []
    for idx, service in enumerate(services):
        buttons.append([InlineKeyboardButton(f"✏️ {service}", callback_data=f"editss|{category_id}|{idx}")])
    
    buttons.append([InlineKeyboardButton("➕ إضافة خدمة", callback_data=f"add|{category_id}")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="xdmat")])
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_service_edit_menu(update, context, chat_id, user_id, category_id, service_idx):
    akl_data = read_json('akl/akl.json', {})
    service_name = akl_data.get('xdmaxs', {}).get(category_id, [])[service_idx]
    category_name = akl_data.get('NAMES', {}).get(category_id, 'القسم')
    
    text = f"""✏️ <b>تعديل الخدمة</b>
━━━━━━━━━━━━━━━━━
📌 الخدمة: {service_name}
📂 القسم: {category_name}
━━━━━━━━━━━━━━━━━
اختر الخاصية للتعديل:"""
    
    buttons = [
        [InlineKeyboardButton("💰 السعر", callback_data=f"setprice|{category_id}|{service_idx}"), InlineKeyboardButton("🔢 الايدي", callback_data=f"setid|{category_id}|{service_idx}")],
        [InlineKeyboardButton("📉 الحد الأدنى", callback_data=f"setmin|{category_id}|{service_idx}"), InlineKeyboardButton("📈 الحد الأقصى", callback_data=f"setmix|{category_id}|{service_idx}")],
        [InlineKeyboardButton("📝 الوصف", callback_data=f"setdes|{category_id}|{service_idx}")],
        [InlineKeyboardButton("🔑 API KEY", callback_data=f"setkey|{category_id}|{service_idx}"), InlineKeyboardButton("🌐 الموقع", callback_data=f"setWeb|{category_id}|{service_idx}")],
        [InlineKeyboardButton("❌ حذف الخدمة", callback_data=f"delt|{category_id}|{service_idx}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"edits|{category_id}")]
    ]
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

async def show_buttons_menu(update, context, chat_id, user_id):
    buttons = []
    for i in range(1, 12):
        name = read_text(f'edid/aklamrnm{i}.txt', f'زر {i}')
        buttons.append([InlineKeyboardButton(name, callback_data=f"serzer{i}")])
    
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="emperor_panel")])
    
    await update.callback_query.edit_message_text(
        "✏️ <b>تعديل أسماء الأزرار</b>\n\nاختر الزر لتغيير اسمه:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_button_names_menu(update, context, chat_id, user_id):
    buttons = []
    for i in range(1, 12):
        name = read_text(f'edid/aklamrnm{i}.txt', f'زر {i}')
        buttons.append([InlineKeyboardButton(name, callback_data=f"serzer{i}")])
    
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="azraramr")])
    
    await update.callback_query.edit_message_text(
        "✏️ <b>تعديل أسماء الأزرار</b>\n\nاختر الزر لتغيير اسمه:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_transparent_buttons(update, context, chat_id, user_id):
    buttons = read_json('button.json', {})
    reply_markup = []
    
    for idx, btn in buttons.get('buttons', {}).items():
        reply_markup.append([InlineKeyboardButton(btn.get('name', 'زر'), callback_data=f"zh|{idx}")])
    
    for idx, btn in buttons.get('links', {}).items():
        reply_markup.append([InlineKeyboardButton(btn.get('name', 'رابط'), callback_data=f"zh|{idx}")])
    
    for idx, btn in buttons.get('codzer', {}).items():
        reply_markup.append([InlineKeyboardButton(btn.get('name', 'اختصار'), callback_data=f"zh|{idx}")])
    
    reply_markup.append([InlineKeyboardButton("➕ إضافة زر", callback_data="addbtn")])
    reply_markup.append([InlineKeyboardButton("🔙 رجوع", callback_data="azraramr")])
    
    await update.callback_query.edit_message_text(
        "🖼️ <b>الأزرار الشفافة</b>\n\nيمكنك إضافة أو حذف الأزرار:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(reply_markup)
    )

async def show_button_details(update, context, chat_id, user_id, button_id):
    buttons = read_json('button.json', {})
    
    if button_id in buttons.get('buttons', {}):
        btn = buttons['buttons'][button_id]
        text = f"""🔘 <b>{btn.get('name', 'زر')}</b>
━━━━━━━━━━━━━━━━━
📝 النوع: زر نصي
📄 المحتوى: {btn.get('mo', '')[:100]}...
🔄 طريقة العرض: {btn.get('Type', 'EditMessageText')}"""
        
        reply_markup = [
            [InlineKeyboardButton("🔄 تغيير طريقة العرض", callback_data=f"offer|{button_id}")],
            [InlineKeyboardButton("❌ حذف الزر", callback_data=f"delete|{button_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="zrar")]
        ]
        
    elif button_id in buttons.get('links', {}):
        btn = buttons['links'][button_id]
        text = f"""🔗 <b>{btn.get('name', 'رابط')}</b>
━━━━━━━━━━━━━━━━━
📝 النوع: رابط
🌐 الرابط: {btn.get('mo', '')}"""
        
        reply_markup = [
            [InlineKeyboardButton("❌ حذف الزر", callback_data=f"delete|{button_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="zrar")]
        ]
        
    elif button_id in buttons.get('codzer', {}):
        btn = buttons['codzer'][button_id]
        text = f"""🔘 <b>{btn.get('name', 'اختصار')}</b>
━━━━━━━━━━━━━━━━━
📝 النوع: زر مختصر
📌 الإجراء: {btn.get('mo', '')}"""
        
        reply_markup = [
            [InlineKeyboardButton("❌ حذف الزر", callback_data=f"delete|{button_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="zrar")]
        ]
    else:
        return
    
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(reply_markup))

async def show_replies_menu(update, context, chat_id, user_id):
    replies = read_json('replies.json', {})
    reply_markup = []
    
    for idx, reply in replies.get('replies', {}).items():
        reply_markup.append([InlineKeyboardButton(reply.get('name', 'رد'), callback_data=f"add_red|{idx}")])
    
    reply_markup.append([InlineKeyboardButton("➕ إضافة رد", callback_data="add_red")])
    reply_markup.append([InlineKeyboardButton("🔙 رجوع", callback_data="home")])
    
    await update.callback_query.edit_message_text(
        "📝 <b>الردود التلقائية</b>\n\nيمكنك إضافة أو حذف الردود:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(reply_markup)
    )

async def show_commands_menu(update, context, chat_id, user_id):
    comm_data = read_json('comm.json', {})
    reply_markup = []
    
    for code, cmd in comm_data.get('com', {}).items():
        reply_markup.append([InlineKeyboardButton(cmd.get('com1', 'أمر'), callback_data="null"), InlineKeyboardButton("🗑️", callback_data=f"dellll×{code}")])
    
    reply_markup.append([InlineKeyboardButton("🧹 مسح الكل", callback_data="deleda"), InlineKeyboardButton("➕ إضافة أمر", callback_data="adddcd")])
    reply_markup.append([InlineKeyboardButton("🔙 رجوع", callback_data="home")])
    
    await update.callback_query.edit_message_text(
        "⌨️ <b>الأوامر المختصرة</b>\n\nيمكنك إضافة أوامر مختصرة:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(reply_markup)
    )

async def show_channels_for_points(update, context, chat_id, user_id):
    user_data = read_json('data/user.json', {})
    channels = user_data.get('channellist', [])
    rewards = user_data.get('setmemberlist', [])
    
    if not channels:
        await update.callback_query.edit_message_text(
            "📭 لا توجد قنوات في الوقت الحالي",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="takecoinn")]])
        )
        return
    
    for idx, channel in enumerate(channels):
        context.user_data['current_channel'] = channel
        reward = rewards[idx] if idx < len(rewards) else 5
        
        buttons = [
            [InlineKeyboardButton("✅ اشتركت", callback_data="truechannel"), InlineKeyboardButton("⏭️ تخطي", callback_data="nextchannel")],
            [InlineKeyboardButton("📛 إبلاغ", callback_data="badchannel")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="takecoinn")]
        ]
        
        await update.callback_query.edit_message_text(
            f"📢 اشترك في القناة @{channel}\nوستحصل على {reward} نقاط",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

async def check_channel_subscription(update, context, chat_id, user_id):
    channel = context.user_data.get('current_channel', '')
    if not channel:
        await update.callback_query.answer("❌ حدث خطأ", show_alert=True)
        return
    
    member = bot_api('getChatMember', {'chat_id': f'@{channel}', 'user_id': user_id})
    if not member or not member.get('ok') or member['result']['status'] in ['left', 'kicked']:
        await update.callback_query.answer("❌ اشترك في القناة أولاً", show_alert=True)
        return
    
    user_data = read_json('data/user.json', {})
    reward = 5
    for idx, ch in enumerate(user_data.get('channellist', [])):
        if ch == channel:
            reward = user_data.get('setmemberlist', [])[idx] if idx < len(user_data.get('setmemberlist', [])) else 5
            break
    
    add_user_coin(user_id, reward)
    wallet_log(user_id, 'charge', reward, f"اشتراك في قناة @{channel}")
    
    await update.callback_query.answer(f"✅ تم إضافة {reward} نقاط", show_alert=True)
    await show_main_menu(update, context, chat_id, user_id)

async def next_channel(update, context, chat_id, user_id):
    await show_channels_for_points(update, context, chat_id, user_id)

async def check_main_channel(update, context, chat_id, user_id):
    channel = read_text('data/channelyes.txt', '')
    if not channel:
        await update.callback_query.answer("❌ لا توجد قناة رئيسية", show_alert=True)
        return
    
    member = bot_api('getChatMember', {'chat_id': f'@{channel}', 'user_id': user_id})
    if not member or not member.get('ok') or member['result']['status'] in ['left', 'kicked']:
        await update.callback_query.answer("❌ اشترك في القناة أولاً", show_alert=True)
        return
    
    reward = int(read_text('edid/add_aoc.txt', '2'))
    add_user_coin(user_id, reward)
    wallet_log(user_id, 'charge', reward, f"اشتراك في القناة الرئيسية @{channel}")
    
    await update.callback_query.answer(f"✅ تم إضافة {reward} نقاط", show_alert=True)
    await show_main_menu(update, context, chat_id, user_id)

async def toggle_bot_status(update, context, chat_id, user_id):
    current = read_text('baageel.txt', '✅')
    new = '❌' if current == '✅' else '✅'
    write_text('baageel.txt', new)
    await update.callback_query.answer(f"✅ تم تغيير حالة البوت إلى {new}", show_alert=True)
    await show_admin_panel(update, context, chat_id, user_id)

async def daily_reward(update, context, chat_id, user_id):
    add_day = read_text('edid/add_day.txt', '✅')
    if add_day == '❌':
        await update.callback_query.answer("❌ الهدية اليومية معطلة", show_alert=True)
        return
    
    today = datetime.now().strftime('%A')
    day_users = []
    try:
        with open(f'data/{today}.txt', 'r') as f:
            day_users = f.read().split('\n')
    except:
        pass
    
    if str(user_id) in day_users:
        await update.callback_query.answer("⏳ انتظر حتى الغد", show_alert=True)
        return
    
    reward = int(read_text('data/day_coins.txt', '20'))
    add_user_coin(user_id, reward)
    wallet_log(user_id, 'daily', reward, "هدية يومية")
    append_text(f'data/{today}.txt', f'{user_id}\n')
    
    await update.callback_query.answer(f"✅ تم إضافة {reward} نقاط", show_alert=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    text = update.message.text or update.message.caption or ''
    
    if is_banned(user_id):
        await update.message.reply_text("❌ انت محظور من استخدام البوت")
        return
    
    mode = context.user_data.get('mode', '')
    
    if mode == 'check_order':
        order_id = text.strip()
        if order_id.isdigit():
            akl_data = read_json('akl/akl.json', {})
            site = akl_data.get('sSite', '')
            api_key = akl_data.get('sVISCODEV', '')
            
            if site and api_key:
                try:
                    response = requests.get(
                        f"https://{site}/api/v2",
                        params={'key': api_key, 'action': 'status', 'order': order_id},
                        timeout=CURL_TIMEOUT
                    )
                    result = response.json()
                    status = result.get('remains', 0)
                    status_text = '✅ مكتمل' if status == 0 else '⏳ قيد المراجعة'
                    
                    await update.message.reply_text(
                        f"🔢 معلومات الطلب #{order_id}\n━━━━━━━━━━━━━━━━━\n📌 الحالة: {status_text}\n⏳ المتبقي: {status}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]])
                    )
                except:
                    await update.message.reply_text("❌ حدث خطأ في جلب معلومات الطلب")
            else:
                await update.message.reply_text("❌ لم يتم إعداد API الموقع")
            
            context.user_data['mode'] = ''
        return
    
    if mode == 'redeem_code':
        user_data = read_json('data/user.json', {})
        code = text.strip().upper()
        coupon_data = coupons_read()
        
        if code in coupon_data:
            coupon = coupon_data[code]
            if not coupon.get('active', False):
                await update.message.reply_text("❌ الكود غير مفعل")
            elif str(user_id) in coupon.get('used_by', []):
                await update.message.reply_text("❌ لقد استخدمت هذا الكود من قبل")
            elif coupon.get('max_uses', 0) > 0 and len(coupon.get('used_by', [])) >= coupon['max_uses']:
                await update.message.reply_text("❌ انتهت صلاحية الكود")
            else:
                value = coupon['value']
                add_user_coin(user_id, value)
                wallet_log(user_id, 'charge', value, f"كود شحن: {code}")
                coupon_data[code]['used_by'].append(str(user_id))
                coupons_write(coupon_data)
                await update.message.reply_text(f"✅ تم شحن {value} نقاط")
        else:
            await update.message.reply_text("❌ الكود غير صحيح")
        
        context.user_data['mode'] = ''
        return
    
    if mode == 'send_coin_user':
        target_id = text.strip()
        if target_id.isdigit():
            context.user_data['send_target'] = int(target_id)
            context.user_data['mode'] = 'send_coin_amount'
            await update.message.reply_text(f"💰 أرسل كمية النقاط للتحويل إلى {target_id}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]))
        else:
            await update.message.reply_text("❌ ايدي غير صحيح")
        return
    
    if mode == 'send_coin_amount':
        amount = text.strip()
        if amount.isdigit():
            amount = float(amount)
            target_id = context.user_data.get('send_target')
            coin = get_user_coin(user_id)
            
            if coin < amount:
                await update.message.reply_text(f"❌ رصيدك غير كافٍ\nالرصيد: {coin}\nالمطلوب: {amount}")
                return
            
            if amount < int(read_text('edid/work_add_day.txt', '10')):
                await update.message.reply_text(f"❌ الحد الأدنى للتحويل هو {read_text('edid/work_add_day.txt', '10')}")
                return
            
            deduct_user_coin(user_id, amount)
            add_user_coin(target_id, amount)
            wallet_log(user_id, 'deduct', amount, f"تحويل إلى {target_id}")
            wallet_log(target_id, 'charge', amount, f"تحويل من {user_id}")
            
            await update.message.reply_text(f"✅ تم تحويل {amount} نقاط إلى {target_id}")
            await bot_api('sendMessage', {'chat_id': target_id, 'text': f"💰 تم استلام {amount} نقاط من {user_id}"})
            
            context.user_data['mode'] = ''
            context.user_data['send_target'] = None
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        return
    
    if mode == 'compensation':
        await update.message.reply_text("✅ تم استلام طلب التعويض، سيتم مراجعته")
        await bot_api('sendMessage', {'chat_id': ADMIN_ID, 'text': f"📋 طلب تعويض جديد\nمن: {user_id}\nالرسالة: {text}"})
        context.user_data['mode'] = ''
        return
    
    if mode.startswith('create_coupon_'):
        coupon_type = mode.replace('create_coupon_', '')
        parts = text.strip().split()
        if len(parts) >= 2:
            code = parts[0].upper()
            value = float(parts[1])
            max_uses = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            
            result = coupon_create(code, coupon_type, value, max_uses)
            if result:
                await update.message.reply_text(f"✅ تم إنشاء الكوبون\nالكود: {code}\nالقيمة: {value}\nالحد: {max_uses or 'غير محدود'}")
            else:
                await update.message.reply_text("❌ فشل إنشاء الكوبون")
        else:
            await update.message.reply_text("❌ الصيغة غير صحيحة\nمثال: CODE 10 0")
        
        context.user_data['mode'] = ''
        return
    
    if mode == 'search_coupon':
        code = text.strip().upper()
        coupon_data = coupons_read()
        if code in coupon_data:
            coupon = coupon_data[code]
            text = f"""🎫 <b>معلومات الكوبون</b>
━━━━━━━━━━━━━━━━━
📌 الكود: {code}
📝 النوع: {coupon['type']}
💰 القيمة: {coupon['value']}
📊 الاستخدام: {len(coupon.get('used_by', []))}/{coupon.get('max_uses', 0) or '∞'}
📌 الحالة: {'✅ مفعل' if coupon.get('active') else '❌ معطل'}"""
            
            buttons = [[InlineKeyboardButton("🔴 تعطيل", callback_data=f"emperor_cp_disable_{code}")]]
            await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await update.message.reply_text("❌ الكوبون غير موجود")
        
        context.user_data['mode'] = ''
        return
    
    if mode == 'add_admin':
        if text.isdigit():
            admin_id = int(text)
            if admin_id != user_id:
                sudo_data = read_json('sudo.json', {})
                if 'info' not in sudo_data:
                    sudo_data['info'] = {}
                if 'admins' not in sudo_data['info']:
                    sudo_data['info']['admins'] = [ADMIN_ID]
                if admin_id not in sudo_data['info']['admins']:
                    sudo_data['info']['admins'].append(admin_id)
                    write_json('sudo.json', sudo_data)
                    await update.message.reply_text(f"✅ تم إضافة {admin_id} كأدمن")
                else:
                    await update.message.reply_text("❌ هذا العضو أدمن بالفعل")
            else:
                await update.message.reply_text("❌ لا يمكن إضافة نفسك")
        else:
            await update.message.reply_text("❌ ايدي غير صحيح")
        
        context.user_data['mode'] = ''
        return
    
    if mode == 'ban' or mode == 'unban':
        if text.isdigit():
            target_id = int(text)
            banned = get_banned_users()
            
            if mode == 'ban':
                if str(target_id) not in banned:
                    append_text('sudo/ban.txt', f'{target_id}\n')
                    await update.message.reply_text(f"✅ تم حظر {target_id}")
                    await bot_api('sendMessage', {'chat_id': target_id, 'text': "❌ تم حظرك من البوت"})
                else:
                    await update.message.reply_text("❌ العضو محظور بالفعل")
            else:
                if str(target_id) in banned:
                    banned_list = '\n'.join([b for b in banned if b != str(target_id)])
                    write_text('sudo/ban.txt', banned_list)
                    await update.message.reply_text(f"✅ تم إلغاء حظر {target_id}")
                    await bot_api('sendMessage', {'chat_id': target_id, 'text': "✅ تم إلغاء حظرك"})
                else:
                    await update.message.reply_text("❌ العضو غير محظور")
        else:
            await update.message.reply_text("❌ ايدي غير صحيح")
        
        context.user_data['mode'] = ''
        return
    
    if mode == 'add_channel':
        channel = text.strip()
        if channel.startswith('@'):
            channel = channel[1:]
        
        chat_info = bot_api('getChat', {'chat_id': f'@{channel}'})
        if not chat_info or not chat_info.get('ok'):
            await update.message.reply_text("❌ القناة غير موجودة")
            return
        
        admin_check = bot_api('getChatMember', {'chat_id': f'@{channel}', 'user_id': user_id})
        if not admin_check or not admin_check.get('ok'):
            await update.message.reply_text("❌ البوت ليس أدمن في القناة")
            return
        
        sudo_data = read_json('sudo.json', {})
        if 'info' not in sudo_data:
            sudo_data['info'] = {}
        if 'channel' not in sudo_data['info']:
            sudo_data['info']['channel'] = {}
        
        sudo_data['info']['channel'][str(chat_info['result']['id'])] = {
            'name': chat_info['result']['title'],
            'user': f'@{channel}',
            'st': 'عامة'
        }
        write_json('sudo.json', sudo_data)
        
        await update.message.reply_text(f"✅ تم إضافة القناة @{channel}")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_start_text':
        write_text('start.txt', text)
        await update.message.reply_text("✅ تم حفظ رسالة الترحيب")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_price_text':
        write_text('edid/msgasar.txt', text)
        await update.message.reply_text("✅ تم حفظ رسالة الأسعار")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_terms_text':
        write_text('edid/msgasro.txt', text)
        await update.message.reply_text("✅ تم حفظ الشروط")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_notification_text':
        write_text('edid/msgaspat.txt', text)
        await update.message.reply_text("✅ تم حفظ رسالة الإشعار")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_currency':
        write_text('edid/cdiamlaadf.txt', text)
        await update.message.reply_text(f"✅ تم تعيين العملة: {text}")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_bot_name':
        write_text('edid/nambot.txt', text)
        await update.message.reply_text(f"✅ تم تعيين اسم البوت: {text}")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_channel':
        channel = text.strip()
        if channel.startswith('@'):
            channel = channel[1:]
        write_text('edid/chadmin.txt', channel)
        await update.message.reply_text(f"✅ تم تعيين القناة: @{channel}")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_contact':
        contact = text.strip()
        if not contact.startswith('@'):
            contact = f'@{contact}'
        write_text('edid/acont_admin.txt', contact)
        await update.message.reply_text(f"✅ تم تعيين حساب التواصل: {contact}")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_referral_reward':
        if text.isdigit():
            write_text('edid/coinsstart.txt', text)
            await update.message.reply_text(f"✅ تم تعيين مكافأة الدعوة: {text}")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_min_balance':
        if text.isdigit():
            write_text('data/adna_coins.txt', text)
            await update.message.reply_text(f"✅ تم تعيين الحد الأدنى: {text}")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_daily_reward':
        if text.isdigit():
            write_text('data/day_coins.txt', text)
            await update.message.reply_text(f"✅ تم تعيين الهدية اليومية: {text}")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_transfer_min':
        if text.isdigit():
            write_text('edid/work_add_day.txt', text)
            await update.message.reply_text(f"✅ تم تعيين الحد الأدنى للتحويل: {text}")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_subscription_reward':
        if text.isdigit():
            write_text('edid/add_aoc.txt', text)
            await update.message.reply_text(f"✅ تم تعيين نقاط الاشتراك: {text}")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_member_price':
        if text.isdigit():
            write_text('edid/addado.txt', text)
            await update.message.reply_text(f"✅ تم تعيين سعر العضو: {text}")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_api_token':
        akl_data = read_json('akl/akl.json', {})
        akl_data['sVISCODEV'] = text.strip()
        write_json('akl/akl.json', akl_data)
        await update.message.reply_text("✅ تم حفظ توكن API")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_site_domain':
        akl_data = read_json('akl/akl.json', {})
        domain = text.strip().replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
        akl_data['sSite'] = domain
        write_json('akl/akl.json', akl_data)
        await update.message.reply_text(f"✅ تم حفظ الموقع: {domain}")
        context.user_data['mode'] = ''
        return
    
    if mode == 'set_force_sub_text':
        sudo_data = read_json('sudo.json', {})
        if 'info' not in sudo_data:
            sudo_data['info'] = {}
        sudo_data['info']['klish_sil'] = text
        write_json('sudo.json', sudo_data)
        await update.message.reply_text("✅ تم حفظ رسالة الاشتراك الإجباري")
        context.user_data['mode'] = ''
        return
    
    if mode.startswith('set_button_name_'):
        button_num = mode.replace('set_button_name_', '')
        if button_num.isdigit():
            write_text(f'edid/aklamrnm{button_num}.txt', text)
            await update.message.reply_text(f"✅ تم حفظ اسم الزر {button_num}")
        context.user_data['mode'] = ''
        return
    
    if mode == 'add_reply_keyword':
        context.user_data['reply_keyword'] = text
        context.user_data['mode'] = 'add_reply_text'
        await update.message.reply_text("📝 أرسل نص الرد:")
        return
    
    if mode == 'add_reply_text':
        keyword = context.user_data.get('reply_keyword', '')
        replies = read_json('replies.json', {})
        if 'replies' not in replies:
            replies['replies'] = {}
        
        code = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        replies['replies'][code] = {'name': keyword, 'mo': text}
        write_json('replies.json', replies)
        
        await update.message.reply_text(f"✅ تم حفظ الرد\nالكلمة: {keyword}")
        context.user_data['mode'] = ''
        context.user_data['reply_keyword'] = ''
        return
    
    if mode == 'add_button':
        context.user_data['button_name'] = text
        context.user_data['mode'] = 'add_button_content'
        await update.message.reply_text("📝 أرسل محتوى الزر:\n- نص عادي\n- رابط يبدأ بـ http://\n- كود اختصار (co:...)")
        return
    
    if mode == 'add_button_content':
        name = context.user_data.get('button_name', 'زر')
        buttons = read_json('button.json', {})
        
        if 'buttons' not in buttons:
            buttons['buttons'] = {}
        if 'links' not in buttons:
            buttons['links'] = {}
        if 'codzer' not in buttons:
            buttons['codzer'] = {}
        
        code = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        
        if text.startswith('http://') or text.startswith('https://'):
            buttons['links'][code] = {'name': name, 'mo': text, 'Type': 'رابط'}
        elif text.startswith('co:'):
            buttons['codzer'][code] = {'name': name, 'mo': text, 'Type': 'EditMessageText', 'tymyzr': 'زر مختصر'}
        else:
            buttons['buttons'][code] = {'name': name, 'mo': text, 'Type': 'EditMessageText'}
        
        write_json('button.json', buttons)
        await update.message.reply_text(f"✅ تم حفظ الزر: {name}")
        context.user_data['mode'] = ''
        context.user_data['button_name'] = ''
        return
    
    if mode == 'add_service_category':
        akl_data = read_json('akl/akl.json', {})
        if 'qsm' not in akl_data:
            akl_data['qsm'] = []
        if 'NAMES' not in akl_data:
            akl_data['NAMES'] = {}
        
        code = f"bot{random.randint(0, 999999999999999)}"
        akl_data['qsm'].append(f"{text}-{code}")
        akl_data['NAMES'][code] = text
        write_json('akl/akl.json', akl_data)
        
        await update.message.reply_text(f"✅ تم إضافة القسم: {text}")
        context.user_data['mode'] = ''
        return
    
    if mode == 'add_service':
        category_id = context.user_data.get('category_id', '')
        akl_data = read_json('akl/akl.json', {})
        
        if 'xdmaxs' not in akl_data:
            akl_data['xdmaxs'] = {}
        if category_id not in akl_data['xdmaxs']:
            akl_data['xdmaxs'][category_id] = []
        
        akl_data['xdmaxs'][category_id].append(text)
        write_json('akl/akl.json', akl_data)
        
        await update.message.reply_text(f"✅ تم إضافة الخدمة: {text}")
        context.user_data['mode'] = ''
        context.user_data['category_id'] = ''
        return
    
    if mode.startswith('set_service_price_'):
        parts = mode.replace('set_service_price_', '').split('_')
        if len(parts) == 2:
            category_id, service_idx = parts[0], int(parts[1])
            if text.isdigit():
                akl_data = read_json('akl/akl.json', {})
                if 'S3RS' not in akl_data:
                    akl_data['S3RS'] = {}
                if category_id not in akl_data['S3RS']:
                    akl_data['S3RS'][category_id] = {}
                akl_data['S3RS'][category_id][str(service_idx)] = float(text) / 1000
                write_json('akl/akl.json', akl_data)
                await update.message.reply_text(f"✅ تم حفظ السعر: {text}")
            else:
                await update.message.reply_text("❌ أرسل رقماً صحيحاً")
            context.user_data['mode'] = ''
        return
    
    if mode.startswith('set_service_id_'):
        parts = mode.replace('set_service_id_', '').split('_')
        if len(parts) == 2:
            category_id, service_idx = parts[0], int(parts[1])
            if text.isdigit():
                akl_data = read_json('akl/akl.json', {})
                if 'IDSSS' not in akl_data:
                    akl_data['IDSSS'] = {}
                if category_id not in akl_data['IDSSS']:
                    akl_data['IDSSS'][category_id] = {}
                akl_data['IDSSS'][category_id][str(service_idx)] = int(text)
                write_json('akl/akl.json', akl_data)
                await update.message.reply_text(f"✅ تم حفظ ايدي الخدمة: {text}")
            else:
                await update.message.reply_text("❌ أرسل رقماً صحيحاً")
            context.user_data['mode'] = ''
        return
    
    if mode.startswith('set_service_min_'):
        parts = mode.replace('set_service_min_', '').split('_')
        if len(parts) == 2:
            category_id, service_idx = parts[0], int(parts[1])
            if text.isdigit():
                akl_data = read_json('akl/akl.json', {})
                if 'min' not in akl_data:
                    akl_data['min'] = {}
                if category_id not in akl_data['min']:
                    akl_data['min'][category_id] = {}
                akl_data['min'][category_id][str(service_idx)] = int(text)
                write_json('akl/akl.json', akl_data)
                await update.message.reply_text(f"✅ تم حفظ الحد الأدنى: {text}")
            else:
                await update.message.reply_text("❌ أرسل رقماً صحيحاً")
            context.user_data['mode'] = ''
        return
    
    if mode.startswith('set_service_max_'):
        parts = mode.replace('set_service_max_', '').split('_')
        if len(parts) == 2:
            category_id, service_idx = parts[0], int(parts[1])
            if text.isdigit():
                akl_data = read_json('akl/akl.json', {})
                if 'mix' not in akl_data:
                    akl_data['mix'] = {}
                if category_id not in akl_data['mix']:
                    akl_data['mix'][category_id] = {}
                akl_data['mix'][category_id][str(service_idx)] = int(text)
                write_json('akl/akl.json', akl_data)
                await update.message.reply_text(f"✅ تم حفظ الحد الأقصى: {text}")
            else:
                await update.message.reply_text("❌ أرسل رقماً صحيحاً")
            context.user_data['mode'] = ''
        return
    
    if mode.startswith('set_service_desc_'):
        parts = mode.replace('set_service_desc_', '').split('_')
        if len(parts) == 2:
            category_id, service_idx = parts[0], int(parts[1])
            akl_data = read_json('akl/akl.json', {})
            if 'WSF' not in akl_data:
                akl_data['WSF'] = {}
            if category_id not in akl_data['WSF']:
                akl_data['WSF'][category_id] = {}
            akl_data['WSF'][category_id][str(service_idx)] = text
            write_json('akl/akl.json', akl_data)
            await update.message.reply_text("✅ تم حفظ الوصف")
            context.user_data['mode'] = ''
        return
    
    if mode.startswith('set_service_key_'):
        parts = mode.replace('set_service_key_', '').split('_')
        if len(parts) == 2:
            category_id, service_idx = parts[0], int(parts[1])
            akl_data = read_json('akl/akl.json', {})
            if 'key' not in akl_data:
                akl_data['key'] = {}
            if category_id not in akl_data['key']:
                akl_data['key'][category_id] = {}
            akl_data['key'][category_id][str(service_idx)] = text
            write_json('akl/akl.json', akl_data)
            await update.message.reply_text("✅ تم حفظ API KEY")
            context.user_data['mode'] = ''
        return
    
    if mode.startswith('set_service_web_'):
        parts = mode.replace('set_service_web_', '').split('_')
        if len(parts) == 2:
            category_id, service_idx = parts[0], int(parts[1])
            akl_data = read_json('akl/akl.json', {})
            if 'Web' not in akl_data:
                akl_data['Web'] = {}
            if category_id not in akl_data['Web']:
                akl_data['Web'][category_id] = {}
            akl_data['Web'][category_id][str(service_idx)] = text
            write_json('akl/akl.json', akl_data)
            await update.message.reply_text("✅ تم حفظ رابط الموقع")
            context.user_data['mode'] = ''
        return
    
    if mode == 'broadcast_text':
        user_data = read_json('data/user.json', {})
        users = user_data.get('userlist', [])
        success = 0
        
        for user in users:
            try:
                await bot_api('sendMessage', {'chat_id': user, 'text': text, 'parse_mode': 'HTML'})
                success += 1
            except:
                pass
        
        await update.message.reply_text(f"📢 تم الإذاعة لـ {success} مستخدم")
        context.user_data['mode'] = ''
        return
    
    if mode == 'broadcast_forward':
        user_data = read_json('data/user.json', {})
        users = user_data.get('userlist', [])
        success = 0
        
        for user in users:
            try:
                await bot_api('forwardMessage', {'chat_id': user, 'from_chat_id': chat_id, 'message_id': update.message.message_id})
                success += 1
            except:
                pass
        
        await update.message.reply_text(f"📢 تم الإذاعة لـ {success} مستخدم")
        context.user_data['mode'] = ''
        return
    
    if mode == 'broadcast_private':
        user_data = read_json('data/user.json', {})
        users = user_data.get('userlist', [])
        success = 0
        
        for user in users:
            try:
                await bot_api('sendMessage', {'chat_id': user, 'text': text, 'parse_mode': 'HTML'})
                success += 1
            except:
                pass
        
        await update.message.reply_text(f"📢 تم الإذاعة لـ {success} مستخدم")
        context.user_data['mode'] = ''
        return
    
    if mode == 'broadcast_forward_private':
        user_data = read_json('data/user.json', {})
        users = user_data.get('userlist', [])
        success = 0
        
        for user in users:
            try:
                await bot_api('forwardMessage', {'chat_id': user, 'from_chat_id': chat_id, 'message_id': update.message.message_id})
                success += 1
            except:
                pass
        
        await update.message.reply_text(f"📢 تم الإذاعة لـ {success} مستخدم")
        context.user_data['mode'] = ''
        return
    
    if mode == 'broadcast_groups':
        try:
            with open('ViSCo/groups.txt', 'r') as f:
                groups = f.read().split('\n')
        except:
            groups = []
        
        success = 0
        for group in groups:
            if group.strip():
                try:
                    await bot_api('sendMessage', {'chat_id': int(group), 'text': text, 'parse_mode': 'HTML'})
                    success += 1
                except:
                    pass
        
        await update.message.reply_text(f"📢 تم الإذاعة لـ {success} كروب")
        context.user_data['mode'] = ''
        return
    
    if mode == 'broadcast_forward_groups':
        try:
            with open('ViSCo/groups.txt', 'r') as f:
                groups = f.read().split('\n')
        except:
            groups = []
        
        success = 0
        for group in groups:
            if group.strip():
                try:
                    await bot_api('forwardMessage', {'chat_id': int(group), 'from_chat_id': chat_id, 'message_id': update.message.message_id})
                    success += 1
                except:
                    pass
        
        await update.message.reply_text(f"📢 تم الإذاعة لـ {success} كروب")
        context.user_data['mode'] = ''
        return
    
    if mode == 'add_finance_channel':
        channel = text.strip()
        if channel.startswith('@'):
            channel = channel[1:]
        
        chat_info = bot_api('getChat', {'chat_id': f'@{channel}'})
        if not chat_info or not chat_info.get('ok'):
            await update.message.reply_text("❌ القناة غير موجودة")
            return
        
        context.user_data['finance_channel'] = f'@{channel}'
        context.user_data['mode'] = 'add_finance_members'
        await update.message.reply_text(f"📢 أرسل عدد الأعضاء المطلوبة لقناة @{channel}:")
        return
    
    if mode == 'add_finance_members':
        if text.isdigit():
            members = int(text)
            channel = context.user_data.get('finance_channel', '')
            
            user_data = read_json('data/user.json', {})
            if 'finance' not in user_data:
                user_data['finance'] = []
            user_data['finance'].append([channel, members])
            write_json('data/user.json', user_data)
            
            await update.message.reply_text(f"✅ تم إضافة قناة {channel} بـ {members} عضو")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        
        context.user_data['mode'] = ''
        context.user_data['finance_channel'] = ''
        return
    
    if mode == 'remove_finance_channel':
        channel = text.strip()
        if channel.startswith('@'):
            channel = channel[1:]
        channel = f'@{channel}'
        
        user_data = read_json('data/user.json', {})
        if 'finance' in user_data:
            user_data['finance'] = [ch for ch in user_data['finance'] if ch[0] != channel]
            write_json('data/user.json', user_data)
            await update.message.reply_text(f"✅ تم حذف قناة {channel}")
        else:
            await update.message.reply_text("❌ القناة غير موجودة")
        
        context.user_data['mode'] = ''
        return
    
    if mode == 'admin_add_coins':
        target_id = text.strip()
        if target_id.isdigit():
            context.user_data['admin_target'] = int(target_id)
            context.user_data['mode'] = 'admin_add_coins_amount'
            await update.message.reply_text(f"💰 أرسل عدد النقاط لإضافتها لـ {target_id}:")
        else:
            await update.message.reply_text("❌ ايدي غير صحيح")
        return
    
    if mode == 'admin_add_coins_amount':
        if text.isdigit():
            amount = float(text)
            target_id = context.user_data.get('admin_target')
            add_user_coin(target_id, amount)
            wallet_log(target_id, 'charge', amount, "إضافة من الأدمن")
            await update.message.reply_text(f"✅ تم إضافة {amount} نقاط لـ {target_id}")
            await bot_api('sendMessage', {'chat_id': target_id, 'text': f"💰 تم إضافة {amount} نقاط من الأدمن"})
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        
        context.user_data['mode'] = ''
        context.user_data['admin_target'] = None
        return
    
    if mode == 'admin_remove_coins':
        target_id = text.strip()
        if target_id.isdigit():
            context.user_data['admin_target'] = int(target_id)
            context.user_data['mode'] = 'admin_remove_coins_amount'
            await update.message.reply_text(f"💰 أرسل عدد النقاط لخصمها من {target_id}:")
        else:
            await update.message.reply_text("❌ ايدي غير صحيح")
        return
    
    if mode == 'admin_remove_coins_amount':
        if text.isdigit():
            amount = float(text)
            target_id = context.user_data.get('admin_target')
            coin = get_user_coin(target_id)
            
            if coin >= amount:
                deduct_user_coin(target_id, amount)
                wallet_log(target_id, 'deduct', amount, "خصم من الأدمن")
                await update.message.reply_text(f"✅ تم خصم {amount} نقاط من {target_id}")
                await bot_api('sendMessage', {'chat_id': target_id, 'text': f"💰 تم خصم {amount} نقاط من قبل الأدمن"})
            else:
                await update.message.reply_text(f"❌ رصيد العضو غير كافٍ\nالرصيد: {coin}")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        
        context.user_data['mode'] = ''
        context.user_data['admin_target'] = None
        return
    
    if mode == 'create_code_value':
        if text.isdigit():
            value = int(text)
            context.user_data['code_value'] = value
            context.user_data['mode'] = 'create_code_uses'
            await update.message.reply_text("🔢 أرسل عدد مرات الاستخدام (2 فأكثر):")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        return
    
    if mode == 'create_code_uses':
        if text.isdigit():
            uses = int(text)
            if uses < 2:
                await update.message.reply_text("❌ الحد الأدنى 2")
                return
            
            code = context.user_data.get('code', ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=8)))
            value = context.user_data.get('code_value', 10)
            
            user_data = read_json('data/user.json', {})
            user_data['codecoin'] = code
            user_data['howcoincode'] = value
            write_json('data/user.json', user_data)
            
            write_text(f'edid/howcodeadd {code}.txt', str(uses))
            write_text(f'edid/howcode {code}.txt', str(value))
            
            await update.message.reply_text(f"""
✅ تم إنشاء كود هدية
━━━━━━━━━━━━━━━━━
📌 الكود: `{code}`
💰 القيمة: {value} نقاط
👥 عدد المستخدمين: {uses}
⏳ الصلاحية: 30 ساعة
━━━━━━━━━━━━━━━━━
شارك الكود مع المستخدمين
""")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        
        context.user_data['mode'] = ''
        context.user_data['code'] = ''
        context.user_data['code_value'] = None
        return
    
    if mode == 'broadcast_coins':
        if text.isdigit():
            amount = float(text)
            user_data = read_json('data/user.json', {})
            users = user_data.get('userlist', [])
            success = 0
            
            for user in users:
                try:
                    add_user_coin(user, amount)
                    wallet_log(user, 'gift', amount, "هدية من الأدمن للجميع")
                    await bot_api('sendMessage', {'chat_id': user, 'text': f"🎁 تم إضافة {amount} نقاط هدية من البوت"})
                    success += 1
                except:
                    pass
            
            await update.message.reply_text(f"✅ تم إرسال {amount} نقاط لـ {success} مستخدم")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        
        context.user_data['mode'] = ''
        return
    
    if mode == 'order_qty':
        qty = text.strip()
        if qty.isdigit():
            qty = int(qty)
            order_data = context.user_data.get('order', {})
            min_qty = order_data.get('min_qty', 100)
            max_qty = order_data.get('max_qty', 1000)
            
            if qty < min_qty or qty > max_qty:
                await update.message.reply_text(f"⚠️ الكمية يجب أن تكون بين {min_qty} و {max_qty}")
                return
            
            context.user_data['order_qty'] = qty
            context.user_data['mode'] = 'order_link'
            await update.message.reply_text("🔗 أرسل الرابط أو اسم المستخدم:")
        else:
            await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        return
    
    if mode == 'order_link':
        link = text.strip()
        context.user_data['order_link'] = link
        
        order_data = context.user_data.get('order', {})
        qty = context.user_data.get('order_qty', 0)
        price = order_data.get('price', 1) * qty
        
        buttons = [
            [InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"YESS|{user_id}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="panel")]
        ]
        
        await update.message.reply_text(
            f"""📋 <b>مراجعة الطلب</b>
━━━━━━━━━━━━━━━━━
📌 الخدمة: {order_data.get('service_name', '')}
🔢 الكمية: {qty}
🔗 الرابط: {link}
💰 السعر: {price} نقاط
━━━━━━━━━━━━━━━━━
هل أنت متأكد من الطلب؟""",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        context.user_data['mode'] = ''
        return
    
    if mode == 'upload_backup':
        if update.message.document:
            doc = update.message.document
            file_name = doc.file_name
            
            if not file_name.endswith('.tupac'):
                await update.message.reply_text("❌ الملف يجب أن يكون .tupac")
                return
            
            file_info = bot_api('getFile', {'file_id': doc.file_id})
            if not file_info or not file_info.get('ok'):
                await update.message.reply_text("❌ فشل تحميل الملف")
                return
            
            file_path = file_info['result']['file_path']
            file_content = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}").json()
            
            if 'data' in file_content:
                write_json('akl/akl.json', file_content['data'])
                await update.message.reply_text("✅ تم استعادة الخدمات بنجاح")
            else:
                await update.message.reply_text("❌ ملف غير صالح")
        else:
            await update.message.reply_text("❌ أرسل ملف النسخة")
        
        context.user_data['mode'] = ''
        return
    
    if mode == 'add_command':
        if ' - ' in text:
            parts = text.split(' - ', 1)
            command = parts[0].strip()
            description = parts[1].strip()
            
            comm_data = read_json('comm.json', {})
            if 'com' not in comm_data:
                comm_data['com'] = {}
            
            code = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
            comm_data['com'][code] = {'com1': command, 'com2': description}
            write_json('comm.json', comm_data)
            
            await update.message.reply_text(f"✅ تم إضافة الاختصار\nالأمر: {command}\nالوصف: {description}")
        else:
            await update.message.reply_text("❌ الصيغة غير صحيحة\nمثال: command - الوصف")
        
        context.user_data['mode'] = ''
        return
    
    if text.startswith('/'):
        command = text.split()[0].lower()
        if command == '/start':
            await start(update, context)
            return
        
        if command == '/id':
            await update.message.reply_text(str(user_id))
            return
        
        if command == '/wallet':
            history = wallet_history(user_id, 10)
            if not history:
                await update.message.reply_text("📭 لا توجد حركات مسجلة")
                return
            
            currency = read_text('edid/cdiamlaadf.txt', 'نقاط')
            text = f"💼 <b>آخر 10 حركات</b>\n━━━━━━━━━━━━━━━━━\n"
            for entry in history[:10]:
                sign = '+' if entry['type'] not in ['deduct'] else '-'
                text += f"🕐 {entry['time']} | {sign}{entry['amount']} {currency} | {entry['note']}\n"
            
            await update.message.reply_text(text, parse_mode='HTML')
            return
        
        if command == '/orders':
            orders = get_user_orders(user_id, 10)
            if not orders:
                await update.message.reply_text("📭 لا توجد طلبات")
                return
            
            status_map = {'pending': '⏳ قيد الانتظار', 'processing': '⚙️ قيد التنفيذ', 'completed': '✅ مكتمل', 'canceled': '❌ ملغي'}
            text = "📮 <b>آخر طلباتك</b>\n━━━━━━━━━━━━━━━━━\n"
            for order in orders[:10]:
                status = status_map.get(order.get('status', 'pending'), order.get('status', '—'))
                text += f"🔢 #{order.get('id')} | 🛠 {order.get('service')} | {status}\n"
            
            await update.message.reply_text(text, parse_mode='HTML')
            return
        
        if command == '/stats' and is_admin(user_id):
            stats = get_all_orders_stats()
            users = get_users_count()
            banned = len(get_banned_users())
            
            text = f"""📊 <b>إحصائيات البوت</b>
━━━━━━━━━━━━━━━━━
👥 المستخدمين: {users}
🚫 المحظورين: {banned}
📦 الطلبات: {stats['total']}
💰 الأرباح: {stats['revenue']:.2f}
━━━━━━━━━━━━━━━━━
⏳ قيد الانتظار: {stats['pending']}
⚙️ قيد التنفيذ: {stats['processing']}
✅ مكتملة: {stats['completed']}
❌ ملغية: {stats['canceled']}"""
            
            await update.message.reply_text(text, parse_mode='HTML')
            return
        
        if command == '/coupon':
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                await update.message.reply_text("❌ الصيغة: /coupon CODE")
                return
            
            result = coupon_redeem(parts[1], user_id)
            if not result['ok']:
                await update.message.reply_text(result['message'])
                return
            
            coupon = result['coupon']
            if coupon['type'] == 'charge':
                add_user_coin(user_id, coupon['value'])
                wallet_log(user_id, 'charge', coupon['value'], f"كوبون شحن: {parts[1]}")
                await update.message.reply_text(f"✅ تم شحن {coupon['value']} نقاط")
            else:
                await update.message.reply_text(f"✅ تم تفعيل خصم {coupon['value']}%")
            return
        
        if command == '/createcoupon' and is_admin(user_id):
            parts = text.split()
            if len(parts) < 4:
                await update.message.reply_text("❌ الصيغة: /createcoupon CODE charge|discount VALUE [MAX_USES]")
                return
            
            code = parts[1].upper()
            coupon_type = parts[2].lower()
            value = float(parts[3])
            max_uses = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
            
            result = coupon_create(code, coupon_type, value, max_uses)
            if result:
                await update.message.reply_text(f"✅ تم إنشاء الكوبون\nالكود: {code}\nالنوع: {coupon_type}\nالقيمة: {value}")
            else:
                await update.message.reply_text("❌ فشل إنشاء الكوبون")
            return
        
        if command == '/disablecoupon' and is_admin(user_id):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                await update.message.reply_text("❌ الصيغة: /disablecoupon CODE")
                return
            
            coupon_data = coupons_read()
            code = parts[1].upper()
            if code in coupon_data:
                coupon_data[code]['active'] = False
                coupons_write(coupon_data)
                await update.message.reply_text(f"✅ تم تعطيل الكوبون {code}")
            else:
                await update.message.reply_text("❌ الكوبون غير موجود")
            return
    
    if update.message.forward_from_chat:
        mode = context.user_data.get('mode', '')
        if mode == 'add_channel':
            channel_id = update.message.forward_from_chat.id
            chat_info = bot_api('getChat', {'chat_id': channel_id})
            
            if chat_info and chat_info.get('ok'):
                admin_check = bot_api('getChatMember', {'chat_id': channel_id, 'user_id': user_id})
                if admin_check and admin_check.get('ok'):
                    sudo_data = read_json('sudo.json', {})
                    if 'info' not in sudo_data:
                        sudo_data['info'] = {}
                    if 'channel' not in sudo_data['info']:
                        sudo_data['info']['channel'] = {}
                    
                    sudo_data['info']['channel'][str(channel_id)] = {
                        'name': chat_info['result']['title'],
                        'user': 'خاص',
                        'st': 'خاصة'
                    }
                    write_json('sudo.json', sudo_data)
                    
                    await update.message.reply_text(f"✅ تم إضافة القناة: {chat_info['result']['title']}")
                    context.user_data['mode'] = ''
                    return
    
    if update.message.forward_from:
        forward_user_id = update.message.forward_from.id
        mode = context.user_data.get('mode', '')
        
        if mode == 'admin_add_coins':
            context.user_data['admin_target'] = forward_user_id
            context.user_data['mode'] = 'admin_add_coins_amount'
            await update.message.reply_text(f"💰 أرسل عدد النقاط لإضافتها لـ {forward_user_id}:")
            return
        
        if mode == 'admin_remove_coins':
            context.user_data['admin_target'] = forward_user_id
            context.user_data['mode'] = 'admin_remove_coins_amount'
            await update.message.reply_text(f"💰 أرسل عدد النقاط لخصمها من {forward_user_id}:")
            return
        
        if mode == 'send_coin_user':
            context.user_data['send_target'] = forward_user_id
            context.user_data['mode'] = 'send_coin_amount'
            await update.message.reply_text(f"💰 أرسل كمية النقاط للتحويل إلى {forward_user_id}:")
            return

def main():
    ensure_dir('data')
    ensure_dir('akl')
    ensure_dir('edid')
    ensure_dir('sudo')
    ensure_dir('amr')
    ensure_dir('logs')
    ensure_dir('ViSCo')
    
    if not os.path.exists('edid/cdiamlaadf.txt'):
        write_text('edid/cdiamlaadf.txt', 'نقاط')
    
    if not os.path.exists('edid/nambot.txt'):
        write_text('edid/nambot.txt', 'DomKom')
    
    if not os.path.exists('sudo.json'):
        write_json('sudo.json', {'info': {'admins': [ADMIN_ID], 'channel': {}}})
    
    if not os.path.exists('data/user.json'):
        write_json('data/user.json', {'userlist': [], 'finance': []})
    
    if not os.path.exists('akl/akl.json'):
        write_json('akl/akl.json', {})
    
    if not os.path.exists('akl/orders.txt'):
        write_text('akl/orders.txt', '')
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_message))
    application.add_handler(MessageHandler(filters.FORWARDED, handle_message))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()