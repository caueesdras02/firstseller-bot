import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import time
import random
from datetime import datetime
import os
import sqlite3
import logging

# 🔧 Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 🔐 TOKEN do bot via variável de ambiente
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    logger.error("❌ BOT_TOKEN não configurado!")
    raise ValueError("❌ BOT_TOKEN não configurado!")

FORM_LINK = "https://docs.google.com/forms/d/e/1FAIpQLSf5nxopZF91zBWo7mFsHkpHSKhXvOcez-M0A96fc03JlPjgdQ/viewform?usp=header"

# 👇 LISTA DE ADMINS 
ADMIN_IDS = [5932207916, 1858780722]

bot = telebot.TeleBot(TOKEN)

# LISTA DE ATENDENTES
atendentes = [
    {
        "nome": "Cauê",
        "telefone": "+55 81 98903-6646",
        "whatsapp": "https://wa.me/5581989036646"
    },
    {
        "nome": "Lucas", 
        "telefone": "+55 11 99999-9999", 
        "whatsapp": "https://wa.me/5511999999999"
    }
]

# DASHBOARD COM BANCO EM MEMÓRIA PARA CLOUD
class BotDashboard:
    def __init__(self):
        logger.info("📊 Inicializando dashboard...")
        # Usar memória ao invés de arquivo para cloud
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.setup_database()
        self.load_current_stats()
    
    def setup_database(self):
        """Cria o banco de dados em memória"""
        c = self.conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS total_stats
                     (id INTEGER PRIMARY KEY, users INTEGER, forms INTEGER, contacts INTEGER)''')
        
        c.execute("INSERT OR IGNORE INTO total_stats (id, users, forms, contacts) VALUES (1, 0, 0, 0)")
        
        self.conn.commit()
        logger.info("✅ Banco de dados em memória configurado")
    
    def load_current_stats(self):
        """Carrega as estatísticas atuais"""
        c = self.conn.cursor()
        c.execute("SELECT users, forms, contacts FROM total_stats WHERE id = 1")
        result = c.fetchone()
        
        if result:
            self.users_served, self.forms_sent, self.contacts_requested = result
        else:
            self.users_served, self.forms_sent, self.contacts_requested = 0, 0, 0
        
        self.start_time = datetime.now()
        self.hourly_stats = {}
        logger.info(f"📈 Estatísticas carregadas: Users={self.users_served}, Forms={self.forms_sent}, Contacts={self.contacts_requested}")
    
    def add_user(self):
        self.users_served += 1
        self._save_stats()
        logger.info(f"👤 Usuário adicionado. Total: {self.users_served}")
    
    def add_form(self):
        self.forms_sent += 1
        self._save_stats()
        logger.info(f"📋 Formulário adicionado. Total: {self.forms_sent}")
    
    def add_contact(self):
        self.contacts_requested += 1
        self._save_stats()
        logger.info(f"📞 Contato adicionado. Total: {self.contacts_requested}")
    
    def _save_stats(self):
        """Salva as estatísticas no banco"""
        c = self.conn.cursor()
        c.execute('''UPDATE total_stats 
                     SET users = ?, forms = ?, contacts = ? 
                     WHERE id = 1''',
                 (self.users_served, self.forms_sent, self.contacts_requested))
        self.conn.commit()

    # ... (mantenha o resto dos métodos get_stats, etc)

# Inicializa dashboard
logger.info("🚀 Iniciando bot...")
dashboard = BotDashboard()

# Função para verificar se é admin
def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.message_handler(commands=['start'])
def send_welcome(message):
    logger.info(f"🎯 Comando /start recebido de {message.from_user.first_name} (ID: {message.from_user.id})")
    
    try:
        dashboard.add_user()
        
        markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn_quote = KeyboardButton('📋 Quero uma cotação')
        btn_contact = KeyboardButton('💬 Falar com atendente')
        btn_info = KeyboardButton('ℹ️ Conhecer serviços')
        
        if is_admin(message.from_user.id):
            btn_stats = KeyboardButton('📊 Dashboard Admin')
            markup.add(btn_quote, btn_contact, btn_info, btn_stats)
            logger.info(f"✅ Admin acessou: {message.from_user.first_name}")
        else:
            markup.add(btn_quote, btn_contact, btn_info)
            logger.info(f"👤 Cliente acessou: {message.from_user.first_name}")
        
        welcome_text = """
👋 *Olá! Que bom te ver aqui!*

Eu sou o *FirstSeller* - seu **assistente comercial inteligente**! 🤖

🎯 *Como posso te ajudar hoje?*
*Escolha como posso te ajudar abaixo:* 👇
        """
        
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=markup
        )
        logger.info(f"✅ Mensagem de boas-vindas enviada para {message.from_user.first_name}")
        
    except Exception as e:
        logger.error(f"❌ Erro em /start: {e}")
        bot.send_message(message.chat.id, "❌ Ops! Algo deu errado. Tente novamente.")

# ... (mantenha os outros handlers, mas adicione logs em cada um)

@bot.message_handler(func=lambda message: message.text == '📋 Quero uma cotação')
def send_form(message):
    logger.info(f"📋 Solicitação de formulário de {message.from_user.first_name}")
    try:
        dashboard.add_form()
        form_text = f"""
📋 *Perfeito! Vamos te ajudar com uma cotação personalizada!*

🔗 *Formulário de Cotação:*
{FORM_LINK}

⏰ *Leva menos de 1 minuto!*
        """
        bot.send_message(message.chat.id, form_text, parse_mode='Markdown')
        logger.info(f"✅ Formulário enviado para {message.from_user.first_name}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar formulário: {e}")

# ... (adicione tratamento similar nos outros handlers)

def main():
    logger.info("🤖 Iniciando Bot FirstSeller...")
    logger.info("💾 Sistema em memória ativo para cloud")
    logger.info("👑 Admins configurados")
    
    while True:
        try:
            logger.info("🔄 Iniciando polling...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"🔴 Erro no polling: {e}")
            logger.info("🔄 Reiniciando em 10 segundos...")
            time.sleep(10)

if __name__ == "__main__":
    main()
