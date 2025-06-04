import telebot
from telebot import types
import requests
import logging
import json
import matplotlib.pyplot as plt
import io
import os
from datetime import datetime, timedelta
from PIL import Image
import threading
import time

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

import telebot
from telebot import types
import requests
import logging
import json
import os
from datetime import datetime, timedelta
import threading
import time
from collections import defaultdict

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Bot token va API URL
BOT_TOKEN = "7091384260:AAHE0ojG7jyxu1jF73QAeDKkZfsdl0PrCFY"
API_BASE_URL = "http://127.0.0.1:8000/api"

# Bot obyektini yaratish
bot = telebot.TeleBot(BOT_TOKEN)

# Autentifikatsiya qilingan foydalanuvchilar
authenticated_users = set()
user_requests = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 30

def rate_limit_check(user_id):
    """Rate limiting tekshiruvi"""
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    
    # Eski so'rovlarni tozalash
    user_requests[user_id] = [
        req_time for req_time in user_requests[user_id] 
        if req_time > minute_ago
    ]
    
    # Yangi so'rovni qo'shish
    user_requests[user_id].append(now)
    
    return len(user_requests[user_id]) <= MAX_REQUESTS_PER_MINUTE

def is_authenticated(chat_id):
    """Foydalanuvchi autentifikatsiya qilinganmi tekshirish"""
    try:
        response = requests.get(f"{API_BASE_URL}/auth/check/{chat_id}/")
        return response.json().get('authenticated', False)
    except:
        return False

def authenticate_user(username, password, chat_id):
    """API orqali foydalanuvchini autentifikatsiya qilish"""
    try:
        response = requests.post(f"{API_BASE_URL}/auth/login/", {
            'username': username,
            'password': password,
            'chat_id': chat_id
        })
        return response.json()
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return {'success': False}

def create_main_menu():
    """Asosiy menyu tugmalarini yaratish"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn1 = types.InlineKeyboardButton("📊 Bugungi statistika", callback_data="stats_today")
    btn2 = types.InlineKeyboardButton("📈 Haftalik", callback_data="stats_week")
    btn3 = types.InlineKeyboardButton("📅 Oylik", callback_data="stats_month")
    btn4 = types.InlineKeyboardButton("📆 Yillik", callback_data="stats_year")
    btn5 = types.InlineKeyboardButton("🛍️ Sotuvlar", callback_data="sales_report")
    btn6 = types.InlineKeyboardButton("📦 Mahsulotlar", callback_data="products_report")
    btn7 = types.InlineKeyboardButton("💰 Daromad", callback_data="revenue_report")
    btn8 = types.InlineKeyboardButton("📋 Batafsil hisobot", callback_data="detailed_report")
    btn9 = types.InlineKeyboardButton("🔄 Yangilash", callback_data="refresh")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.add(btn7, btn8)
    markup.add(btn9)
    
    return markup

def create_back_button():
    """Orqaga tugmasini yaratish"""
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")
    markup.add(btn_back)
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    """Bot start komandasi"""
    if not rate_limit_check(message.from_user.id):
        bot.reply_to(message, "❌ Juda ko'p so'rov! Biroz kuting.")
        return
        
    chat_id = str(message.chat.id)
    
    if is_authenticated(chat_id):
        authenticated_users.add(chat_id)
        show_main_menu(message)
    else:
        welcome_text = """
🔐 **Admin Statistika Paneli**

Xush kelibsiz! Bu bot orqali siz do'koningiz statistikasini ko'rishingiz mumkin.

📊 **Mavjud imkoniyatlar:**
• Real-time statistika
• Sotuvlar hisoboti  
• Mahsulotlar tahlili
• Daromad hisoboti
• Excel eksport

🔑 **Kirish uchun:**
`/login username password`

❓ **Yordam:** /help
        """
        bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['login'])
def login_command(message):
    """Login komandasi"""
    if not rate_limit_check(message.from_user.id):
        bot.reply_to(message, "❌ Juda ko'p so'rov! Biroz kuting.")
        return
        
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message,
                "❌ Noto'g'ri format!\n"
                "To'g'ri format: `/login username password`",
                parse_mode='Markdown'
            )
            return
        
        _, username, password = parts
        chat_id = str(message.chat.id)
        
        # Xavfsizlik uchun asl xabarni o'chirish
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        
        # API orqali autentifikatsiya
        auth_result = authenticate_user(username, password, chat_id)
        
        if auth_result['success']:
            authenticated_users.add(chat_id)
            
            success_msg = bot.send_message(
                message.chat.id,
                f"✅ Muvaffaqiyatli kirdingiz!\n"
                f"Xush kelibsiz, {auth_result['user']['first_name']}!"
            )
            
            # 3 soniyadan keyin xabarni o'chirish
            threading.Timer(3.0, lambda: safe_delete_message(
                message.chat.id, success_msg.message_id
            )).start()
            
            show_main_menu(message)
        else:
            error_msg = bot.send_message(
                message.chat.id,
                "❌ Login yoki parol noto'g'ri!\n"
                "Qaytadan urinib ko'ring: `/login username password`",
                parse_mode='Markdown'
            )
            
            # 5 soniyadan keyin xabarni o'chirish
            threading.Timer(5.0, lambda: safe_delete_message(
                message.chat.id, error_msg.message_id
            )).start()
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        bot.reply_to(message, "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")

def safe_delete_message(chat_id, message_id):
    """Xavfsiz xabar o'chirish"""
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

def show_main_menu(message):
    """Asosiy menyuni ko'rsatish"""
    markup = create_main_menu()
    
    current_time = datetime.now().strftime('%d.%m.%Y %H:%M')
    
    text = f"📊 **Statistika Dashboard**\n\n"
    text += f"🕐 Vaqt: {current_time}\n"
    text += f"👤 Chat ID: {message.chat.id}\n\n"
    text += "Quyidagi tugmalardan birini tanlang:"
    
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Callback query handler"""
    if not rate_limit_check(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Juda ko'p so'rov!")
        return
        
    chat_id = str(call.message.chat.id)
    
    if not is_authenticated(chat_id):
        bot.answer_callback_query(call.id, "❌ Autentifikatsiya talab qilinadi!")
        bot.edit_message_text(
            "❌ Autentifikatsiya talab qilinadi. /start ni bosing.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        return
    
    bot.answer_callback_query(call.id)
    
    try:
        if call.data == "refresh" or call.data == "back_to_menu":
            markup = create_main_menu()
            current_time = datetime.now().strftime('%d.%m.%Y %H:%M')
            
            text = f"📊 **Statistika Dashboard**\n\n"
            text += f"🕐 Vaqt: {current_time}\n"
            text += f"👤 Chat ID: {call.message.chat.id}\n\n"
            text += "Quyidagi tugmalardan birini tanlang:"
            
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        
        elif call.data.startswith("stats_"):
            period = call.data.split("_")[1]
            show_statistics(call, period)
        
        elif call.data == "sales_report":
            show_sales_report(call)
        
        elif call.data == "products_report":
            show_products_report(call)
        
        elif call.data == "revenue_report":
            show_revenue_report(call)
        
        elif call.data == "detailed_report":
            show_detailed_report(call)
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Xatolik yuz berdi!")

def show_statistics(call, period):
    """Statistika ko'rsatish"""
    try:
        response = requests.get(f"{API_BASE_URL}/statistics/{period}/")
        data = response.json()
        
        if response.status_code == 200:
            stats = data['statistics']
            
            # Period nomini o'zbek tilida
            period_names = {
                'today': 'Bugungi',
                'week': 'Haftalik', 
                'month': 'Oylik',
                'year': 'Yillik'
            }
            
            period_name = period_names.get(period, period.title())
            
            text = f"📊 **{period_name} Statistika**\n\n"
            text += f"💰 **Umumiy daromad:** {stats['total_revenue']:,.0f} so'm\n"
            text += f"🛍️ **Sotuvlar soni:** {stats['total_sales']:,.0f} ta\n"
            text += f"📦 **Sotilgan mahsulotlar:** {stats['products_sold']:,.0f} dona\n"
            text += f"📈 **O'rtacha sotuv:** {stats['average_sale']:,.0f} so'm\n\n"
            
            if 'top_products' in stats and stats['top_products']:
                text += f"🏆 **Eng ko'p sotilgan mahsulotlar:**\n"
                for i, product in enumerate(stats['top_products'][:5], 1):
                    text += f"{i}. {product['name']} - {product['sold']:,.0f} dona\n"
                text += "\n"
            
            # Kunlik ma'lumotlar (agar mavjud bo'lsa)
            if 'daily_revenue' in stats and stats['daily_revenue']:
                text += f"📅 **Kunlik taqsimot:**\n"
                for day_data in stats['daily_revenue'][-7:]:  # Oxirgi 7 kun
                    text += f"• {day_data['date']}: {day_data['revenue']:,.0f} so'm\n"
                text += "\n"
            
            text += f"🕐 **Yangilangan:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            
            markup = create_back_button()
            
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        else:
            bot.edit_message_text(
                "❌ Ma'lumotlarni olishda xatolik yuz berdi.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        bot.edit_message_text(
            "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

def show_sales_report(call):
    """Sotuvlar hisoboti"""
    try:
        response = requests.get(f"{API_BASE_URL}/reports/sales/")
        data = response.json()
        
        text = "🛍️ **Sotuvlar Hisoboti**\n\n"
        
        if 'recent_sales' in data and data['recent_sales']:
            text += "📋 **So'nggi sotuvlar:**\n\n"
            for i, sale in enumerate(data['recent_sales'][:10], 1):
                text += f"**{i}. {sale['product_name']}**\n"
                text += f"   📦 Miqdor: {sale['quantity']} {sale['unit_type']}\n"
                text += f"   💰 Narx: {sale['sale_price']:,.0f} so'm\n"
                text += f"   👤 Sotuvchi: {sale['user']}\n"
                text += f"   🕐 Sana: {sale['date']}\n\n"
        else:
            text += "Ma'lumot topilmadi."
        
        text += f"🕐 **Yangilangan:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        markup = create_back_button()
        
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Sales report error: {e}")
        bot.edit_message_text(
            "❌ Sotuvlar hisobotini olishda xatolik yuz berdi.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

def show_products_report(call):
    """Mahsulotlar hisoboti"""
    try:
        response = requests.get(f"{API_BASE_URL}/reports/products/")
        data = response.json()
        
        text = "📦 **Mahsulotlar Hisoboti**\n\n"
        
        text += f"📊 **Umumiy ma'lumotlar:**\n"
        text += f"• Jami mahsulotlar: {data['total_products']} ta\n"
        text += f"• Zaxirada mavjud: {data['in_stock']} ta\n"
        text += f"• Tugagan mahsulotlar: {data['out_of_stock']} ta\n\n"
        
        if 'low_stock' in data and data['low_stock']:
            text += "⚠️ **Kam qolgan mahsulotlar:**\n"
            for i, product in enumerate(data['low_stock'][:10], 1):
                text += f"{i}. **{product['name']}**\n"
                text += f"   📦 Qolgan: {product['stock']} {product['unit_type']}\n\n"
        else:
            text += "✅ Barcha mahsulotlar yetarli miqdorda mavjud.\n\n"
        
        text += f"🕐 **Yangilangan:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        markup = create_back_button()
        
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Products report error: {e}")
        bot.edit_message_text(
            "❌ Mahsulotlar hisobotini olishda xatolik yuz berdi.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

def show_revenue_report(call):
    """Daromad hisoboti"""
    try:
        response = requests.get(f"{API_BASE_URL}/reports/revenue/")
        data = response.json()
        
        text = "💰 **Daromad Hisoboti**\n\n"
        
        text += f"📊 **Daromad taqsimoti:**\n"
        text += f"• Bugungi daromad: {data['today_revenue']:,.0f} so'm\n"
        text += f"• Haftalik daromad: {data['week_revenue']:,.0f} so'm\n"
        text += f"• Oylik daromad: {data['month_revenue']:,.0f} so'm\n"
        text += f"• Yillik daromad: {data['year_revenue']:,.0f} so'm\n\n"
        
        text += f"💸 **Moliyaviy tahlil:**\n"
        text += f"• Umumiy xarid narxi: {data['total_cost']:,.0f} so'm\n"
        text += f"• Sof foyda: {data['net_profit']:,.0f} so'm\n"
        text += f"• Foyda foizi: {data['profit_margin']:.1f}%\n\n"
        
        # Foydalilik tahlili
        if data['profit_margin'] > 30:
            text += "📈 **Holat:** Juda yaxshi foyda darajasi!\n"
        elif data['profit_margin'] > 20:
            text += "📊 **Holat:** Yaxshi foyda darajasi\n"
        elif data['profit_margin'] > 10:
            text += "📉 **Holat:** O'rtacha foyda darajasi\n"
        else:
            text += "⚠️ **Holat:** Past foyda darajasi\n"
        
        text += f"\n🕐 **Yangilangan:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        markup = create_back_button()
        
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Revenue report error: {e}")
        bot.edit_message_text(
            "❌ Daromad hisobotini olishda xatolik yuz berdi.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

def show_detailed_report(call):
    """Batafsil hisobot"""
    try:
        response = requests.get(f"{API_BASE_URL}/reports/detailed/")
        data = response.json()
        
        # Excel fayl yuborish
        file_url = data.get('file_url')
        if file_url:
            try:
                # Faylni yuklab olish va yuborish
                file_response = requests.get(file_url)
                if file_response.status_code == 200:
                    file_data = file_response.content
                    filename = data.get('filename', 'hisobot.xlsx')
                    
                    bot.send_document(
                        call.message.chat.id,
                        file_data,
                        visible_file_name=filename,
                        caption="📋 Batafsil hisobot Excel formatida"
                    )
            except Exception as file_error:
                logger.error(f"File sending error: {file_error}")
                bot.send_message(
                    call.message.chat.id,
                    f"📋 Batafsil hisobot tayyorlandi.\n"
                    f"📎 Fayl URL: {file_url}"
                )
        
        text = "📋 **Batafsil Hisobot**\n\n"
        text += "✅ Hisobot muvaffaqiyatli yaratildi va yuborildi.\n\n"
        text += f"📊 **Hisobot tarkibi:**\n"
        text += f"• Sotuvlar ma'lumotlari\n"
        text += f"• Mahsulotlar ro'yxati\n"
        text += f"• Moliyaviy hisobot\n"
        text += f"• Statistik tahlil\n\n"
        text += f"📅 **Hisobot sanasi:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        text += f"📁 **Fayl formati:** Excel (.xlsx)"
        
        markup = create_back_button()
        
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Detailed report error: {e}")
        bot.edit_message_text(
            "❌ Batafsil hisobotni olishda xatolik yuz berdi.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

@bot.message_handler(commands=['help'])
def help_command(message):
    """Yordam komandasi"""
    help_text = """
🤖 **Bot Komandalar:**

/start - Botni ishga tushirish
/login username password - Tizimga kirish
/logout - Tizimdan chiqish
/status - Holat tekshirish
/help - Yordam

📊 **Mavjud hisobotlar:**
• Kunlik, haftalik, oylik, yillik statistika
• Sotuvlar hisoboti
• Mahsulotlar holati
• Daromad tahlili
• Batafsil Excel hisobot

🔐 **Xavfsizlik:**
• Login xabarlari avtomatik o'chiriladi
• Rate limiting (30 so'rov/daqiqa)
• Faqat admin foydalanuvchilar kirishi mumkin

❓ **Yordam kerakmi?**
Admin bilan bog'laning: @your_admin_username
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def status_command(message):
    """Bot holati"""
    chat_id = str(message.chat.id)
    
    if is_authenticated(chat_id):
        status_text = "✅ **Siz tizimga kirgansiz**\n\n"
        status_text += f"📅 Vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        status_text += f"👤 Chat ID: {chat_id}\n"
        status_text += f"🔄 Bot holati: Faol\n"
        status_text += f"📊 API holati: Ulangan"
    else:
        status_text = "❌ **Siz tizimga kirmagansiz**\n\n"
        status_text += "Kirish uchun: `/login username password`\n"
        status_text += "Yordam uchun: /help"
    
    bot.reply_to(message, status_text, parse_mode='Markdown')

@bot.message_handler(commands=['logout'])
def logout_command(message):
    """Logout komandasi"""
    chat_id = str(message.chat.id)
    
    if chat_id in authenticated_users:
        authenticated_users.remove(chat_id)
    
    # API ga logout so'rovi
    try:
        requests.post(f"{API_BASE_URL}/auth/logout/", {'chat_id': chat_id})
    except:
        pass
    
    bot.reply_to(message, "👋 Tizimdan muvaffaqiyatli chiqdingiz!")

@bot.message_handler(func=lambda message: True)
def default_handler(message):
    """Standart xabar handler"""
    chat_id = str(message.chat.id)
    
    if not is_authenticated(chat_id):
        bot.reply_to(message,
            "❌ Avval tizimga kiring!\n"
            "Format: `/login username password`\n"
            "Yordam uchun: /help",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message,
            "📊 Statistika menyusini ko'rish uchun /start ni bosing\n"
            "Yordam uchun: /help"
        )

def keep_alive():
    """Botni faol saqlash"""
    while True:
        try:
            time.sleep(300)  # 5 daqiqa
            logger.info("Bot is alive...")
        except Exception as e:
            logger.error(f"Keep alive error: {e}")

if __name__ == '__main__':
    try:
        # Keep alive thread
        alive_thread = threading.Thread(target=keep_alive)
        alive_thread.daemon = True
        alive_thread.start()
        
        logger.info("Simple Statistics Bot ishga tushdi...")
        print("🤖 Simple Statistics Bot ishga tushdi! Ctrl+C bilan to'xtatish mumkin.")
        print("📊 Grafik funksiyasi o'chirilgan - faqat matn ma'lumotlari")
        
        # Botni ishga tushirish
        bot.infinity_polling(none_stop=True, interval=0, timeout=20)
        
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")
        print("\n👋 Bot to'xtatildi!")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"❌ Xatolik: {e}")