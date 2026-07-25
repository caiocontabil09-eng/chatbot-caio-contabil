"""
Backend de Chatbot Inteligente para Escritório de Contabilidade
Hospedado no Vercel (Serverless) - 100% Gratuito
Conecta: Widget do Calima Site → Gemini API → Notificação Telegram
"""

import os
import json
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# ========== CONFIGURAÇÃO DAS APIs ==========
# Configure estas variáveis no painel do Vercel (Environment Variables)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")  # ID do grupo/canal do escritório

# ========== PROMPT DO AGENTE DE TRIAGEM ==========
SYSTEM_PROMPT = """Você é "Ana", assistente virtual de triagem do escritório de contabilidade Caio Contábil LTDA.

🎯 SEU OBJETIVO:
Classificar o atendimento, coletar informações e encaminhar ao contador certo.

📋 REGRAS OBRIGATÓRIAS:
1. Sempre seja cordial, profissional e use português brasileiro
2. Use emojis com moderação para tornar a conversa amigável
3. Identifique o tipo de demanda:
   • 📊 DÚVIDA FISCAL/TRIBUTÁRIA (DAS, impostos, obrigações)
   • 📁 ENTREGA DE DOCUMENTOS (notas, extratos, contratos, holerites)
   • 📅 AGENDAMENTO DE REUNIÃO
   • 🚨 URGÊNCIA (prazo de entrega, multa, problema imediato)
   • 💼 OUTROS
4. Colete gradualmente: nome completo, CNPJ/CPF, e-mail
5. Informe prazos de retorno:
   • Urgência: até 2 horas
   • Demais: até 24 horas úteis
6. NUNCA dê orientação fiscal definitiva — sempre diga que o contador confirmará
7. NUNCA peça senhas, dados bancários ou informações sigilosas demais
8. Ao final, confirme os dados coletados e agradeça

📝 EXEMPLO DE RESPOSTA INICIAL:
"Olá! 😊 Seja bem-vindo ao atendimento da Caio Contábil. Sou a Ana, sua assistente virtual.

Para que eu possa te direcionar ao contador certo, me conta: você precisa de ajuda com alguma dúvida fiscal, entregar documentos, agendar uma reunião ou trata-se de algo urgente?"

⚠️ IMPORTANTE: Se o cliente pedir para falar com um humano, ofereça imediatamente o link do Telegram do escritório.
"""

# ========== HISTÓRICO DE SESSÕES (em memória — para produção use Redis/DB) ==========
sessions = {}

# ========== FUNÇÃO: CHAMAR GEMINI ==========
def call_gemini(message, session_id):
    """Envia mensagem para a API do Gemini e retorna a resposta."""
    import urllib.request

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    # Monta histórico da sessão
    history = sessions.get(session_id, [])
    contents = [{"role": "user", "parts": [{"text": SYSTEM_PROMPT}]}]

    for msg in history[-10:]:  # Mantém últimas 10 mensagens
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["text"]}]})

    contents.append({"role": "user", "parts": [{"text": message}]})

    data = json.dumps({"contents": contents}).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            reply = result["candidates"][0]["content"]["parts"][0]["text"]

            # Salva no histórico
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append({"role": "user", "text": message})
            sessions[session_id].append({"role": "model", "text": reply})

            return reply
    except Exception as e:
        print(f"Erro Gemini: {e}")
        return "Desculpe, estou com dificuldades técnicas no momento. Um contador será notificado para te atender em breve. 🙏"

# ========== FUNÇÃO: NOTIFICAR TELEGRAM ==========
def notify_telegram(session_id, message, reply):
    """Envia notificação para o grupo do escritório no Telegram."""
    import urllib.request

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    text = (
        f"🚨 <b>Novo atendimento no site</b>\n"
        f"🆔 Sessão: <code>{session_id}</code>\n"
        f"👤 Cliente: {message[:100]}\n"
        f"🤖 Bot: {reply[:200]}\n\n"
        f"<a href='https://t.me/{TELEGRAM_BOT_TOKEN.split(":")[0]}'>Ver bot</a>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Erro Telegram: {e}")

# ========== HANDLER HTTP (Serverless Vercel) ==========
class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "online",
            "service": "Caio Contábil - Chatbot API",
            "version": "1.0.0"
        }).encode())

    def do_POST(self):
        parsed_path = urlparse(self.path)

        # ROTA: /chat
        if parsed_path.path == "/chat":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body)
                message = data.get("message", "").strip()
                session_id = data.get("session_id", "default")

                if not message:
                    self._send_json({"error": "Mensagem vazia"}, 400)
                    return

                # Chama Gemini
                reply = call_gemini(message, session_id)

                # Notifica Telegram do escritório
                notify_telegram(session_id, message, reply)

                self._send_json({"reply": reply, "session_id": session_id})

            except json.JSONDecodeError:
                self._send_json({"error": "JSON inválido"}, 400)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        else:
            self._send_json({"error": "Rota não encontrada"}, 404)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
