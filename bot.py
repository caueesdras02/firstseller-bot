import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import threading
import time
import random
from datetime import datetime
import os
import sqlite3
import json
from flask import Flask

# 🔐 TOKEN do bot
TOKEN = os.getenv('TELEGRAM_TOKEN', '8133950557:AAFdiOrBBoKnZEf4XbxnMC3c9HGJ7jBWQd0')
FORM_LINK = "https://docs.google.com/forms/d/e/1FAIpQLSf5nxopZF91zBWo7mFsHkpHSKhXvOcez-M0A96fc03JlPjgdQ/viewform?usp=header"

# 👇 LISTA DE ADMINS 
ADMIN_IDS = [5932207916, 1858780722]  # 👈 Cauê e Lucas como ADMIN

# 👥 ATENDENTES COM USERNAME DO TELEGRAM
atendentes = [
    {
        "nome": "Cauê",
        "username": "@cauefirstseller",  # 👈 SEU USERNAME AQUI
        "user_id": 5932207916
    },
    {
        "nome": "Lucas", 
        "username": "@lucasfirstseller",  # 👈 USERNAME DO LUCAS AQUI
        "user_id": 1858780722
    }
]

bot = telebot.TeleBot(TOKEN)

# SERVIDOR WEB PARA O RENDER
app = Flask(__name__)

@app.route('/')
def home():
    return '🤖 FirstSeller Bot is running!'

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Inicia servidor web em thread separada
threading.Thread(target=run_web_server, daemon=True).start()

# BANCO DE DADOS SQLite
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Tabela de estatísticas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_stats (
                id INTEGER PRIMARY KEY,
                start_time TEXT,
                users_served INTEGER,
                forms_sent INTEGER,
                contacts_requested INTEGER,
                hourly_stats TEXT
            )
        ''')
        
        # Tabela de usuários (para histórico completo)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                first_seen TEXT,
                last_seen TEXT,
                message_count INTEGER
            )
        ''')
        
        self.conn.commit()
    
    def load_stats(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM bot_stats WHERE id = 1')
        result = cursor.fetchone()
        
        if result:
            return {
                'start_time': datetime.fromisoformat(result[1]),
                'users_served': result[2],
                'forms_sent': result[3],
                'contacts_requested': result[4],
                'hourly_stats': json.loads(result[5]) if result[5] else {}
            }
        else:
            # Primeira execução
            default_stats = {
                'start_time': datetime.now(),
                'users_served': 0,
                'forms_sent': 0,
                'contacts_requested': 0,
                'hourly_stats': {}
            }
            self.save_stats(default_stats)
            return default_stats
    
    def save_stats(self, stats):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO bot_stats 
            (id, start_time, users_served, forms_sent, contacts_requested, hourly_stats)
            VALUES (1, ?, ?, ?, ?, ?)
        ''', (
            stats['start_time'].isoformat(),
            stats['users_served'],
            stats['forms_sent'],
            stats['contacts_requested'],
            json.dumps(stats['hourly_stats'])
        ))
        self.conn.commit()
    
    def save_user(self, user_id, username, first_name, last_name):
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, first_seen, last_seen, message_count)
            VALUES (?, ?, ?, ?, COALESCE((SELECT first_seen FROM users WHERE user_id = ?), ?), ?, 
                   COALESCE((SELECT message_count FROM users WHERE user_id = ?), 0) + 1)
        ''', (user_id, username, first_name, last_name, user_id, now, now, user_id))
        
        self.conn.commit()

# DASHBOARD PREMIUM COM SQLite
class BotDashboard:
    def __init__(self):
        self.db = Database()
        self.load_stats()
    
    def load_stats(self):
        stats = self.db.load_stats()
        self.start_time = stats['start_time']
        self.users_served = stats['users_served']
        self.forms_sent = stats['forms_sent']
        self.contacts_requested = stats['contacts_requested']
        self.hourly_stats = stats['hourly_stats']
        print("📊 Estatísticas carregadas do SQLite!")
    
    def save_stats(self):
        stats = {
            'start_time': self.start_time,
            'users_served': self.users_served,
            'forms_sent': self.forms_sent,
            'contacts_requested': self.contacts_requested,
            'hourly_stats': self.hourly_stats
        }
        self.db.save_stats(stats)
    
    def add_user(self, user_id, username, first_name, last_name):
        self.users_served += 1
        self.db.save_user(user_id, username, first_name, last_name)
        self._update_hourly_stats()
        self.save_stats()
    
    def add_form(self):
        self.forms_sent += 1
        self._update_hourly_stats()
        self.save_stats()
    
    def add_contact(self):
        self.contacts_requested += 1
        self._update_hourly_stats()
        self.save_stats()
    
    def _update_hourly_stats(self):
        current_hour = datetime.now().strftime("%H:%M")
        if current_hour in self.hourly_stats:
            self.hourly_stats[current_hour] += 1
        else:
            self.hourly_stats[current_hour] = 1
    
    def get_stats(self):
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        total = self.users_served + self.forms_sent + self.contacts_requested
        
        # GRÁFICO DE BARRAS HORIZONTAL AVANÇADO
        def create_advanced_bar(value, total, color_emoji, label):
            if total == 0:
                bar = "▱▱▱▱▱▱▱▱▱▱"
                percent = 0
            else:
                percent = (value / total) * 100
                filled = int((percent / 100) * 10)
                bar = "▰" * filled + "▱" * (10 - filled)
            
            return f"{color_emoji} {label}: {bar} {value} ({int(percent)}%)"
        
        # GRÁFICO DE PIZZA VISUAL
        def create_pizza_chart():
            if total == 0:
                return """
🍰 *GRÁFICO DE PIZZA:*
╭─────────────╮
│   📊 0%    │
│   SEM      │
│   DADOS    │
╰─────────────╯
                """
            
            users_pct = (self.users_served / total) * 100
            forms_pct = (self.forms_sent / total) * 100
            contacts_pct = (self.contacts_requested / total) * 100
            
            return f"""
🍰 *GRÁFICO DE PIZZA:*
┌─────────────┐
│  🎯 {total} TOTAL  │
├─────────────┤
│ 🟢 Users: {int(users_pct)}%   │
│ 🔵 Forms: {int(forms_pct)}%   │
│ 🟡 Cont: {int(contacts_pct)}%   │
└─────────────┘
            """
        
        # GRÁFICO DE LINHA (tendência)
        def create_trend_chart():
            if len(self.hourly_stats) < 2:
                return "📈 *Tendência:* Dados insuficientes"
            
            last_5_hours = dict(list(self.hourly_stats.items())[-5:])
            max_value = max(last_5_hours.values()) if last_5_hours else 1
            
            chart = "📈 *ATIVIDADE POR HORA:*\n"
            for hour, count in last_5_hours.items():
                height = int((count / max_value) * 5) if max_value > 0 else 0
                bar = "█" * height + "░" * (5 - height)
                chart += f"`{hour}` {bar} {count}\n"
            
            return chart
        
        # CONSTRUINDO O DASHBOARD COMPLETO
        dashboard_text = f"""
🎯 **FIRSTSELLER DASHBOARD PREMIUM** 🎯
💾 *Dados salvos em SQLite*

⏰ *Sessão Ativa:* `{int(hours)}h {int(minutes)}m {int(seconds)}s`
📊 *Total de Interações:* `{total}`

{create_advanced_bar(self.users_served, total, "👥", "Usuários")}
{create_advanced_bar(self.forms_sent, total, "📋", "Formulários")}
{create_advanced_bar(self.contacts_requested, total, "📞", "Contatos")}

{create_pizza_chart()}

{create_trend_chart()}

🟢 **STATUS:** `SISTEMA OPERACIONAL + SQLite` 
🔄 *Dados permanentes - Não perde ao reiniciar*
💽 *Arquivo: bot_data.db*
        """
        
        return dashboard_text

# Inicializa dashboard COM SQLite
dashboard = BotDashboard()

print("🤖 Bot FirstSeller iniciado com SQLite! Pressione Ctrl+C para parar.")

# Função para verificar se é admin
def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    dashboard.add_user(user.id, user.username, user.first_name, user.last_name)
    
    # TECLADO - Abordagem mais conversacional
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_quote = KeyboardButton('📋 Quero uma cotação')
    btn_contact = KeyboardButton('💬 Falar com atendente')
    btn_info = KeyboardButton('ℹ️ Conhecer serviços')
    
    # Se for ADMIN, adiciona botão de dashboard
    if is_admin(user.id):
        btn_stats = KeyboardButton('📊 Dashboard Admin')
        markup.add(btn_quote, btn_contact, btn_info, btn_stats)
        print(f"✅ Admin acessou: {user.first_name}")
    else:
        markup.add(btn_quote, btn_contact, btn_info)
        print(f"👤 Cliente acessou: {user.first_name}")
    
    # MENSAGEM DE BOAS-VINDAS
    welcome_text = """
👋 *Olá! Que bom te ver aqui!*

Eu sou o *FirstSeller* - seu **assistente comercial inteligente**! 🤖

🎯 *Como posso te ajudar hoje?*

Sou especializado em conectar você com as *melhores soluções e fornecedores* do mercado, de forma *rápida e sem complicação*.

💡 *Posso te auxiliar com:*
✓ Cotação de produtos e serviços
✓ Encontrar fornecedores confiáveis  
✓ Soluções personalizadas para sua necessidade
✓ Atendimento especializado

*Escolha como posso te ajudar abaixo:* 👇
    """
    
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=markup
    )

# Botão "Quero uma cotação"
@bot.message_handler(func=lambda message: message.text == '📋 Quero uma cotação')
def send_form(message):
    dashboard.add_form()
    form_text = """
📋 *Perfeito! Vamos te ajudar com uma cotação personalizada!*

Para entendermos exatamente o que você precisa e encontrarmos as *melhores opções*, preencha nosso formulário rápido:

🔗 *Formulário de Cotação:*
{form_link}

⏰ *Leva menos de 1 minuto!*
⚡ *Retornamos com opções em até 15 minutos!*

*FirstSeller - Encontrando a solução perfeita para você!* 💼
    """.format(form_link=FORM_LINK)
    
    bot.send_message(message.chat.id, form_text, parse_mode='Markdown')

# Botão "Conhecer serviços"
@bot.message_handler(func=lambda message: message.text == 'ℹ️ Conhecer serviços')
def send_services_info(message):
    services_text = """
🏢 *FirstSeller - Sua Ponte para Soluções Comerciais!*

🎯 *O que fazemos:*
Conectamos empresas com os *melhores fornecedores e soluções* do mercado, otimizando tempo e recursos.

💼 *Nossos serviços:*
• 📊 *Consultoria Comercial* - Análise de necessidades
• 🤝 *Intermediação Qualificada* - Fornecedores verificados  
• ⚡ *Cotações Rápidas* - Resposta em até 15 minutos
• 🎯 *Soluções Personalizadas* - Sob medida para seu negócio

📈 *Vantagens:*
✓ Economia de tempo na busca por fornecedores
✓ Acesso a parceiros qualificados e confiáveis
✓ Processo simplificado e sem burocracia
✓ Atendimento especializado e humano

*Pronto para transformar sua busca por soluções?*
Clique em *"📋 Quero uma cotação"* para começarmos!
    """
    bot.send_message(message.chat.id, services_text, parse_mode='Markdown')

# Botão "Falar com atendente" - AGORA COM LINK DIRETO
@bot.message_handler(func=lambda message: message.text == '💬 Falar com atendente')
def send_contact(message):
    dashboard.add_contact()
    
    # Escolhe atendente aleatório
    atendente = random.choice(atendentes)
    
    # Teclado inline para abrir conversa direta
    markup = InlineKeyboardMarkup()
    btn_chat = InlineKeyboardButton(
        f"💬 Conversar com {atendente['nome']}", 
        url=f"https://t.me/{atendente['username'].replace('@', '')}"
    )
    markup.add(btn_chat)
    
    contact_info = f"""
📞 *Conectando você com nosso atendente...*

👨‍💼 *Atendente:* {atendente['nome']}
⭐ *Escolhido aleatoriamente para melhor atendimento!*

Clique no botão abaixo para iniciar uma conversa direta no Telegram:
    """
    
    bot.send_message(
        message.chat.id, 
        contact_info, 
        parse_mode='Markdown',
        reply_markup=markup
    )

# 👇 DASHBOARD APENAS PARA ADMINS
@bot.message_handler(func=lambda message: message.text == '📊 Dashboard Admin')
def show_dashboard(message):
    if is_admin(message.from_user.id):
        stats = dashboard.get_stats()
        bot.send_message(message.chat.id, stats, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Acesso restrito aos administradores.")

@bot.message_handler(commands=['dashboard'])
def show_dashboard_command(message):
    if is_admin(message.from_user.id):
        stats = dashboard.get_stats()
        bot.send_message(message.chat.id, stats, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Acesso restrito aos administradores.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "🤖 Digite /start para ver as opções!")

print("🟢 Bot rodando com SQLite!")
print("💾 Dados sendo salvos permanentemente em bot_data.db!")
print("🌐 Servidor web ativo na porta 10000!")
print("👑 Cauê e Lucas configurados como ADMINS")
print("💬 Atendimento direto no Telegram implementado!")
print("🚀 Preparado para hospedagem 24/7 com dados persistentes!")

# Configuração otimizada para hospedagem
try:
    bot.infinity_polling()
except Exception as e:
    print(f"🔴 Erro: {e}")
    print("🔄 Reiniciando em 10 segundos...")
    time.sleep(10)

