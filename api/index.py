from flask import Flask, request, jsonify
import os
import json
import urllib.request
import urllib.error

app = Flask(__name__)

# ========== CONFIGURAÇÃO ==========
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ========== PROMPT DO AGENTE ==========
SYSTEM_PROMPT = """Você é "Ana", assistente virtual de triagem do escritório de contabilidade Caio Contábil LTDA.

SEU OBJETIVO: Classificar o atendimento, coletar informações e encaminhar ao contador certo.

REGRAS:
1. Seja cordial, profissional e use português brasileiro
2. Use emojis com moderação
3. Identifique a demanda: Dúvida fiscal, Documentos, Reunião, Urgência, Outros
4. Colete gradualmente: nome, CNPJ/CPF, e-mail
5. Prazos: Urgência até 2h, demais até 24h
6. NUNCA dê orientação fiscal definitiva
7. NUNCA peça senhas ou dados bancários
8. Ao final, confirme os dados e agradeça

EXEMPLO DE RESPOSTA INICIAL:
"Olá! 😊 Bem-vindo ao atendimento da Caio Contábil. Sou a Ana, sua assistente virtual.

Para te direcionar ao contador certo, me conta: você precisa de ajuda com dúvida fiscal, entregar documentos, agendar reunião ou é algo urgente?"
"""

# ========== HISTÓRICO ==========
sessions = {}

# ========== CORS ==========
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

# ========== ROTAS ==========
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Caio Contábil - Chatbot API",
        "version": "3.0.0"
    })

@app.route('/chat', methods=['GET', 'POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if request.method == 'GET':
        return jsonify({
            "status": "online",
            "service": "Caio Contábil - Chatbot API",
            "version": "3.0.0"
        })

    # POST
    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        session_id = data.get("session_id", "default")

        if not message:
            return jsonify({"error": "Mensagem vazia"}), 400

        # Chama Gemini
        reply = call_gemini(message, session_id)

        # Notifica Telegram
        notify_telegram(session_id, message, reply)

        return jsonify({"reply": reply, "session_id": session_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== GEMINI ==========
def call_gemini(message, session_id):
    if not GEMINI_API_KEY:
        return "⚠️ API do Gemini não configurada. Entre em contato pelo Telegram."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    history = sessions.get(session_id, [])
    contents = [{"role": "user", "parts": [{"text": SYSTEM_PROMPT}]}]

    for msg in history[-10:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["text"]}]})

    contents.append({"role": "user", "parts": [{"text": message}]})

    data = json.dumps({"contents": contents}).encode('utf-8')

    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            reply = result["candidates"][0]["content"]["parts"][0]["text"]

            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append({"role": "user", "text": message})
            sessions[session_id].append({"role": "model", "text": reply})

            return reply
    except urllib.error.HTTPError as e:
        return f"⚠️ Erro na API do Gemini ({e.code}). Um contador será notificado."
    except Exception:
        return "⚠️ Erro de conexão. Um contador será notificado em breve."

# ========== TELEGRAM ==========
def notify_telegram(session_id, message, reply):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    text = (
        f"🚨 <b>Novo atendimento no site</b>\n"
        f"🆔 Sessão: <code>{session_id}</code>\n"
        f"👤 Cliente: {message[:100]}\n"
        f"🤖 Bot: {reply[:200]}"
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
    except Exception:
        pass
