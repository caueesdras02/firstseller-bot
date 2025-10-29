import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import threading
import time
import random
from datetime import datetime
import os
import sqlite3

# 🔐 TOKEN do bot via variável de ambiente
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN não configurado!")

FORM_LINK = "https://docs.google.com/forms/d/e/1FAIpQLSf5nxopZF91zBWo7mFsHkpHSKhXvOcez-M0A96fc03JlPjgdQ/viewform?usp=header"

# 👇 LISTA DE ADMINS 
ADMIN_IDS = [5932207916, 1858780722]  # 👈 Cauê e Lucas como ADMIN

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

# DASHBOARD COM BANCO DE DADOS PERSISTENTE
class BotDashboard:
    def __init__(self):
        self.setup_database()
        self.load_current_stats()
    
    def setup_database(self):
        """Cria o banco de dados se não existir"""
        conn = sqlite3.connect('bot_stats.db')
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS total_stats
                     (id INTEGER PRIMARY KEY, users INTEGER, forms INTEGER, contacts INTEGER)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS daily_stats
                     (date TEXT PRIMARY KEY, users INTEGER, forms INTEGER, contacts INTEGER)''')
        
        c.execute("SELECT * FROM total_stats")
        if not c.fetchone():
            c.execute("INSERT INTO total_stats (id, users, forms, contacts) VALUES (1, 0, 0, 0)")
        
        conn.commit()
        conn.close()
    
    def load_current_stats(self):
        """Carrega as estatísticas atuais da memória"""
        conn = sqlite3.connect('bot_stats.db')
        c = conn.cursor()
        
        c.execute("SELECT users, forms, contacts FROM total_stats WHERE id = 1")
        result = c.fetchone()
        
        if result:
            self.users_served, self.forms_sent, self.contacts_requested = result
        else:
            self.users_served, self.forms_sent, self.contacts_requested = 0, 0, 0
        
        conn.close()
        
        self.start_time = datetime.now()
        self.hourly_stats = self._load_hourly_stats()
    
    def _load_hourly_stats(self):
        return {datetime.now().strftime("%H:%M"): 1}
    
    def add_user(self):
        self.users_served += 1
        self._save_stats()
        self._update_hourly_stats()
    
    def add_form(self):
        self.forms_sent += 1
        self._save_stats()
        self._update_hourly_stats()
    
    def add_contact(self):
        self.contacts_requested += 1
        self._save_stats()
        self._update_hourly_stats()
    
    def _save_stats(self):
        """Salva as estatísticas no banco de dados"""
        conn = sqlite3.connect('bot_stats.db')
        c = conn.cursor()
        
        c.execute('''UPDATE total_stats 
                     SET users = ?, forms = ?, contacts = ? 
                     WHERE id = 1''',
                 (self.users_served, self.forms_sent, self.contacts_requested))
        
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute('''INSERT OR REPLACE INTO daily_stats (date, users, forms, contacts)
                     VALUES (?, ?, ?, ?)''',
                 (today, self.users_served, self.forms_sent, self.contacts_requested))
        
        conn.commit()
        conn.close()
    
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
        
        def create_advanced_bar(value, total, color_emoji, label):
            if total == 0:
                bar = "▱▱▱▱▱▱▱▱▱▱"
                percent = 0
            else:
                percent = (value / total) * 100
                filled = int((percent / 100) * 10)
                bar = "▰" * filled + "▱" * (10 - filled)
            
            return f"{color_emoji} {label}: {bar} {value} ({int(percent)}%)"
        
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
        
        def create_performance_metrics():
            avg_time = uptime.total_seconds() / max(1, total)
            efficiency = (self.forms_sent / max(1, self.users_served)) * 100
            
            return f"""
⚡ *MÉTRICAS DE PERFORMANCE:*
├─ 🚀 *Eficiência:* {int(efficiency)}%
├─ ⏱️ *Tempo médio/action:* {int(avg_time)}s
├─ 📦 *Total ações:* {total}
└─ 🎯 *Taxa conversão:* {int((self.forms_sent/max(1, self.users_served))*100)}%
            """
        
        dashboard_text = f"""
🎯 **FIRSTSELLER DASHBOARD - DADOS PERMANENTES** 🎯

📊 *Estatísticas TOTAIS (desde o início):*
├─ 👥 Usuários atendidos: {self.users_served}
├─ 📋 Formulários enviados: {self.forms_sent}  
├─ 📞 Contatos solicitados: {self.contacts_requested}
└─ 🎯 Total interações: {total}

⏰ *Sessão Ativa:* `{int(hours)}h {int(minutes)}m {int(seconds)}s`

{create_advanced_bar(self.users_served, total, "👥", "Usuários")}
{create_advanced_bar(self.forms_sent, total, "📋", "Formulários")}
{create_advanced_bar(self.contacts_requested, total, "📞", "Contatos")}

{create_pizza_chart()}

{create_trend_chart()}

{create_performance_metrics()}

💾 *Dados salvos permanentemente*
🟢 **STATUS:** `SISTEMA PERSISTENTE ATIVO` 
🔄 *Atualizado em tempo real*
        """
        
        return dashboard_text

# Inicializa dashboard PERSISTENTE
dashboard = BotDashboard()

# Thread para atualizar dashboard
def dashboard_updater():
    while True:
        try:
            time.sleep(5)
        except:
            pass

threading.Thread(target=dashboard_updater, daemon=True).start()

print("🤖 Bot FirstSeller iniciado! Pressione Ctrl+C para parar.")
print("💾 Sistema de banco de dados SQLite ativo!")
print("📊 Dados persistentes habilitados!")

# Função para verificar se é admin
def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.message_handler(commands=['start'])
def send_welcome(message):
    dashboard.add_user()
    
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_quote = KeyboardButton('📋 Quero uma cotação')
    btn_contact = KeyboardButton('💬 Falar com atendente')
    btn_info = KeyboardButton('ℹ️ Conhecer serviços')
    
    if is_admin(message.from_user.id):
        btn_stats = KeyboardButton('📊 Dashboard Admin')
        markup.add(btn_quote, btn_contact, btn_info, btn_stats)
        print(f"✅ Admin acessou: {message.from_user.first_name}")
    else:
        markup.add(btn_quote, btn_contact, btn_info)
        print(f"👤 Cliente acessou: {message.from_user.first_name}")
    
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

@bot.message_handler(func=lambda message: message.text == '💬 Falar com atendente')
def send_contact(message):
    dashboard.add_contact()
    
    atendente = random.choice(atendentes)
    
    contact_info = f"""
📞 *Fale com nosso atendente:*

👨‍💼 *Atendente:* {atendente['nome']}
📱 *Telefone:* {atendente['telefone']}
💬 *WhatsApp:* [Clique aqui]({atendente['whatsapp']})

⏰ *Horário de atendimento:*
Segunda a Sexta: 8h às 18h

✨ *Escolhido aleatoriamente para melhor atendimento!*
    """
    
    bot.send_message(
        message.chat.id, 
        contact_info, 
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

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

# 👇 COMANDO QUE ZERA TUDO - BOT + PLANILHA + FORMS
@bot.message_handler(commands=['zerartudo'])
def reset_everything(message):
    if is_admin(message.from_user.id):
        try:
            # 1. Zera banco de dados do bot
            conn = sqlite3.connect('bot_stats.db')
            c = conn.cursor()
            c.execute("UPDATE total_stats SET users = 0, forms = 0, contacts = 0 WHERE id = 1")
            c.execute("DELETE FROM daily_stats")
            conn.commit()
            conn.close()
            
            # 2. Recarrega dashboard
            global dashboard
            dashboard = BotDashboard()
            
            # 3. Mensagem com GUIA COMPLETO
            response = """
✅ *SISTEMA BOT ZERADO COM SUCESSO!* 🎯

📊 *O que foi ZERADO no Bot:*
├─ 👥 Estatísticas de usuários
├─ 📋 Contador de formulários  
├─ 📞 Contador de contatos
└─ 💾 Banco de dados interno

🔧 *AGORA ZERE MANUALMENTE:*

📝 **PARA ZERAR O GOOGLE FORMS:**
1️⃣ Acesse: https://docs.google.com/forms
2️⃣ Clique no seu formulário
3️⃣ Vá em "RESPOSTAS" (ícone de gráfico)
4️⃣ Clique em "❌ LIMPAR TODAS AS RESPOSTAS"
5️⃣ Confirme a exclusão

📊 **PARA ZERAR A PLANILHA:**
1️⃣ Acesse sua planilha do Google Sheets
2️⃣ Selecione TODAS as linhas com dados (exceto cabeçalho)
3️⃣ Botão direito → "Excluir linhas"
4️⃣ Salve (Ctrl+S)

🎯 *PRONTO! Tudo zerado para nova coleta!*

💡 *Dica:* Compartilhe o bot e acompanhe o dashboard em tempo real!
            """
            
            bot.send_message(message.chat.id, response, parse_mode='Markdown')
            print("🔄 Sistema bot zerado por admin")
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Erro ao zerar sistema: {e}")
    else:
        bot.send_message(message.chat.id, "❌ Acesso restrito aos administradores.")

@bot.message_handler(commands=['testar'])
def generate_test_data(message):
    if is_admin(message.from_user.id):
        for i in range(20):
            dashboard.add_user()
        for i in range(15):
            dashboard.add_form()  
        for i in range(15):
            dashboard.add_contact()
            
        bot.send_message(message.chat.id, "🧪 *50 interações fake geradas!*\nUse /dashboard para ver os resultados!", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Acesso restrito.")

@bot.message_handler(commands=['guia'])
def show_guide(message):
    if is_admin(message.from_user.id):
        guide_text = """
📖 **GUIA COMPLETO DO ADMIN** 🎯

🔧 *COMANDOS DISPONÍVEIS:*
├─ /start - Iniciar bot
├─ /dashboard - Ver estatísticas  
├─ /zerartudo - Zerar TUDO (bot + forms + planilha)
├─ /testar - Gerar dados fake
└─ /guia - Ver este guia

🗂️ *COMO GERENCIAR DADOS:*

📝 **REMOVER RESPOSTA DO FORMS:**
1. Acesse seu Forms
2. Vá em "Respostas" 
3. Encontre a resposta → Delete individual

📊 **REMOVER LINHA DA PLANILHA:**
1. Acesse sua Sheets
2. Clique no número da linha
3. Botão direito → "Excluir linha"

🔄 **ZERAR TUDO (Forms + Planilha):**
1. Use /zerartudo no bot
2. Siga as instruções que aparecerem

🎯 *Dica para Apresentação:*
- Use /zerartudo antes de começar
- Compartilhe o bot com a plateia  
- Mostre o dashboard em tempo real!
        """
        bot.send_message(message.chat.id, guide_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Acesso restrito.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "🤖 Digite /start para ver as opções!")

print("🟢 Bot rodando com dashboard PREMIUM...")
print("👑 Cauê e Lucas configurados como ADMINS")
print("💾 Banco de dados SQLite ativo - Dados PERSISTENTES!")
print("🎯 Comandos secretos ativos: /zerartudo, /testar, /guia")
print("🚀 Preparado para hospedagem 24/7!")

try:
    bot.infinity_polling()
except Exception as e:
    print(f"🔴 Erro: {e}")
    print("🔄 Reiniciando em 10 segundos...")
    time.sleep(10)
