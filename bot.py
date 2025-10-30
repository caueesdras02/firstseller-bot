from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import threading
import time
import random
from datetime import datetime
import os

TOKEN = os.getenv('TELEGRAM_TOKEN', '8133950557:AAFdiOrBBoKnZEf4XbxnMC3c9HGJ7jBWQd0')
FORM_LINK = "https://docs.google.com/forms/d/e/1FAIpQLSf5nxopZF91zBWo7mFsHkpHSKhXvOcez-M0A96fc03JlPjgdQ/viewform?usp=header"

ADMIN_IDS = [5932207916, 1858780722]

bot = TeleBot(TOKEN)

atendentes = [
    {"nome": "Cauê", "telefone": "+55 81 98903-6646", "whatsapp": "https://wa.me/5581989036646"},
    {"nome": "Lucas", "telefone": "+55 11 99999-9999", "whatsapp": "https://wa.me/5511999999999"}
]

class BotDashboard:
    def __init__(self):
        self.start_time = datetime.now()
        self.users_served = 0
        self.forms_sent = 0
        self.contacts_requested = 0
    
    def add_user(self): self.users_served += 1
    def add_form(self): self.forms_sent += 1
    def add_contact(self): self.contacts_requested += 1
    
    def get_stats(self):
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        total = self.users_served + self.forms_sent + self.contacts_requested
        
        def create_bar(value, total, emoji, label):
            if total == 0: return f"{emoji} {label}: ▱▱▱▱▱▱▱▱▱▱ 0 (0%)"
            percent = (value / total) * 100
            filled = int((percent / 100) * 10)
            return f"{emoji} {label}: {'▰' * filled}{'▱' * (10 - filled)} {value} ({int(percent)}%)"
        
        return f"""
🎯 **FIRSTSELLER DASHBOARD**

⏰ *Ativo:* `{int(hours)}h {int(minutes)}m`
📊 *Total:* `{total}`

{create_bar(self.users_served, total, "👥", "Usuários")}
{create_bar(self.forms_sent, total, "📋", "Forms")}
{create_bar(self.contacts_requested, total, "📞", "Contatos")}

🟢 **ONLINE** | 🔄 *Tempo real*
"""

dashboard = BotDashboard()

def is_admin(user_id): return user_id in ADMIN_IDS

@bot.message_handler(commands=['start'])
def send_welcome(message):
    dashboard.add_user()
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_quote = KeyboardButton('📋 Cotação')
    btn_contact = KeyboardButton('💬 Atendente')
    btn_info = KeyboardButton('ℹ️ Serviços')
    
    if is_admin(message.from_user.id):
        markup.add(btn_quote, btn_contact, btn_info, KeyboardButton('📊 Dashboard'))
    else:
        markup.add(btn_quote, btn_contact, btn_info)
    
    bot.send_message(message.chat.id, """
👋 *Olá! FirstSeller aqui!* 🤖

*Como posso ajudar?*
✓ Cotação de produtos/serviços
✓ Fornecedores confiáveis  
✓ Soluções personalizadas

*Escolha abaixo:* 👇
""", parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📋 Cotação')
def send_form(message):
    dashboard.add_form()
    bot.send_message(message.chat.id, f"""
📋 *Vamos te ajudar!*

🔗 *Formulário:*
{FORM_LINK}

⏰ *1 minuto* | ⚡ *15min resposta*
""", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '💬 Atendente')
def send_contact(message):
    dashboard.add_contact()
    atendente = random.choice(atendentes)
    bot.send_message(message.chat.id, f"""
📞 *Atendente {atendente['nome']}*

📱 {atendente['telefone']}
💬 [WhatsApp]({atendente['whatsapp']})

⏰ Seg-Sex: 8h-18h
""", parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(func=lambda message: message.text == '📊 Dashboard')
def show_dashboard(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, dashboard.get_stats(), parse_mode='Markdown')

print("🚀 Bot FirstSeller iniciado!")
try:
    bot.infinity_polling()
except Exception as e:
    print(f"🔴 Erro: {e}")
    time.sleep(10)
