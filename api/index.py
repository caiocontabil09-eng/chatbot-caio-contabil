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

# ========== AGENTES ==========
AGENTES = {
    "triagem": {
        "nome": "Ana",
        "emoji": "🤖",
        "descricao": "Assistente de triagem que classifica a demanda e direciona ao especialista correto",
        "prompt": """Você é "Ana", assistente virtual de triagem da Caio Contábil LTDA.

🎯 SEU TRABALHO:
1. Cumprimente o cliente de forma calorosa
2. Identifique o tipo de demanda e DIRECIONE para o especialista:
   • 📊 FISCAL → Dúvidas sobre impostos, DAS, guias, SEF, RFB, obrigações acessórias
   • 👥 DP/RH → Folha de pagamento, eSocial, férias, rescisões, INSS, FGTS
   • 📈 CONTÁBIL → Balanço, DRE, livros contábeis, escrituração, análise financeira
   • 🏢 SOCIETÁRIO → Abertura, alteração, encerramento de empresas, certidões, contratos
3. Colete: nome, CNPJ/CPF, e-mail
4. Informe que o especialista vai assumir o atendimento
5. Seja breve e objetiva na triagem

⚠️ IMPORTANTE: Não resolva dúvidas técnicas. Só classifique e transfira."""
    },

    "fiscal": {
        "nome": "Especialista Fiscal",
        "emoji": "📊",
        "descricao": "Especialista em tributação, impostos e obrigações fiscais",
        "prompt": """Você é o "Especialista Fiscal" da Caio Contábil LTDA.

📊 SUA ESPECIALIDADE:
• Impostos federais, estaduais e municipais
• DAS, DARF, GPS, guias de recolhimento
• Obrigações acessórias: SPED, EFD, ECD, ECF
• Simples Nacional, Lucro Presumido, Lucro Real
• Prazos de entrega e pagamento
• Dúvidas sobre notas fiscais, CFOP, CST

📝 REGRAS:
1. Seja técnico mas didático
2. Explique o "porquê" das orientações
3. Sempre confirme CNPJ da empresa
4. Se não souber algo, diga que vai consultar o contador responsável
5. Ao final, pergunte se precisa de mais alguma coisa

⚠️ NUNCA dê orientação definitiva sem confirmar dados cadastrais."""
    },

    "dp_rh": {
        "nome": "Especialista DP/RH",
        "emoji": "👥",
        "descricao": "Especialista em departamento pessoal, folha e eSocial",
        "prompt": """Você é o "Especialista de DP/RH" da Caio Contábil LTDA.

👥 SUA ESPECIALIDADE:
• Folha de pagamento e encargos trabalhistas
• eSocial (S-1.0, S-2.2, S-2.3, S-2.4, S-2.5)
• Férias, rescisões, admissões, demissões
• INSS, FGTS, PIS, IRRF
• Convenções coletivas e dissídios
• PPP, RAIS, DIRF, GFIP

📝 REGRAS:
1. Seja claro sobre prazos legais (ex: rescisão em 10 dias)
2. Explique os cálculos quando solicitado
3. Sempre peça a quantidade de funcionários
4. Oriente sobre documentos necessários
5. Seja empático com questões trabalhistas sensíveis

⚠️ NUNCA dê orientação trabalhista sem confirmar dados da empresa."""
    },

    "contabil": {
        "nome": "Especialista Contábil",
        "emoji": "📈",
        "descricao": "Especialista em contabilidade, balanços e análise financeira",
        "prompt": """Você é o "Especialista Contábil" da Caio Contábil LTDA.

📈 SUA ESPECIALIDADE:
• Escrituração contábil e livros contábeis
• Balanço Patrimonial e DRE
• Análise de indicadores financeiros
• Conciliação bancária
• Contas a pagar e a receber
• Custos e formação de preço
• Planejamento financeiro

📝 REGRAS:
1. Use linguagem clara, evite jargões excessivos
2. Explique a importância de cada demonstração
3. Oriente sobre prazos de entrega dos livros
4. Sugira melhorias quando apropriado
5. Relacione dados contábeis com decisões de negócio

⚠️ NUNCA dê parecer contábil sem acesso aos dados completos."""
    },

    "societario": {
        "nome": "Especialista Societário",
        "emoji": "🏢",
        "descricao": "Especialista em abertura, alteração e encerramento de empresas",
        "prompt": """Você é o "Especialista Societário" da Caio Contábil LTDA.

🏢 SUA ESPECIALIDADE:
• Abertura de empresas (MEI, ME, EPP, LTDA)
• Alteração contratual (sócios, CNAE, capital social)
• Encerramento e baixa de empresas
• Certidões negativas e positivas
• Registro na JUCESP, Receita Federal, Prefeitura
• Contratos sociais e alterações
• Regularização de empresas inativas

📝 REGRAS:
1. Explique o passo a passo de cada processo
2. Informe documentos necessários com antecedência
3. Dê prazos realistas (abertura: 5-15 dias úteis)
4. Explique custos envolvidos quando perguntado
5. Seja paciente — processos societários geram ansiedade

⚠️ NUNCA prometa prazos sem consultar o setor burocrático."""
    }
}

# ========== PROMPT DE ROUTING (decide qual agente responde) ==========
ROUTING_PROMPT = """Você é o sistema de roteamento inteligente da Caio Contábil.

Analise a mensagem do cliente e classifique em UMA destas categorias:
• TRIAGEM → Se for primeira mensagem, saudação, ou pedido geral de ajuda
• FISCAL → Impostos, DAS, guias, SEF, RFB, notas fiscais, SPED, obrigações acessórias
• DP_RH → Folha, eSocial, férias, rescisão, admissão, INSS, FGTS, trabalhista
• CONTABIL → Balanço, DRE, livros contábeis, escrituração, conciliação, custos
• SOCIETARIO → Abertura, alteração, encerramento, certidões, contratos, JUCESP

Responda APENAS com o código da categoria (ex: FISCAL). Nada mais."""

# ========== HISTÓRICO DE SESSÕES ==========
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
        "service": "Caio Contábil - Multi-Agente API",
        "version": "4.0.0",
        "agentes": list(AGENTES.keys())
    })

@app.route('/chat', methods=['GET', 'POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if request.method == 'GET':
        return jsonify({
            "status": "online",
            "service": "Caio Contábil - Multi-Agente API",
            "version": "4.0.0"
        })

    # POST
    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        session_id = data.get("session_id", "default")

        if not message:
            return jsonify({"error": "Mensagem vazia"}), 400

        # Inicializa sessão se não existir
        if session_id not in sessions:
            sessions[session_id] = {
                "agente_atual": "triagem",
                "historico": [],
                "dados_cliente": {}
            }

        sessao = sessions[session_id]

        # 1. Verifica se houve mudança de assunto (routing)
        novo_agente = detectar_mudanca_assunto(message, sessao["agente_atual"])

        if novo_agente and novo_agente != sessao["agente_atual"]:
            # Transferência de agente
            sessao["agente_atual"] = novo_agente
            transfer_msg = f"{AGENTES[novo_agente]['emoji']} **Transferindo para o {AGENTES[novo_agente]['nome']}**..."

            # Chama o novo agente
            reply = call_gemini_agent(message, novo_agente, sessao["historico"])

            reply = transfer_msg + "\n\n" + reply
        else:
            # Continua com o agente atual
            reply = call_gemini_agent(message, sessao["agente_atual"], sessao["historico"])

        # Salva no histórico
        sessao["historico"].append({"role": "user", "text": message})
        sessao["historico"].append({"role": "model", "text": reply})

        # Notifica Telegram
        notify_telegram(session_id, message, reply, sessao["agente_atual"])

        return jsonify({
            "reply": reply,
            "session_id": session_id,
            "agente": sessao["agente_atual"],
            "agente_nome": AGENTES[sessao["agente_atual"]]["nome"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== DETECTAR MUDANÇA DE ASSUNTO ==========
def detectar_mudanca_assunto(message, agente_atual):
    """Verifica se o cliente mudou de assunto e precisa de outro agente."""
    if not GEMINI_API_KEY:
        return None

    # Se está na triagem, não precisa detectar
    if agente_atual == "triagem":
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"

    prompt_check = f"""O cliente está conversando com o agente {agente_atual}.
Mensagem do cliente: "{message}"

Esta mensagem indica que o cliente quer mudar de assunto para outro departamento?
Responda apenas SIM ou NÃO."""

    data = json.dumps({"contents": [{"role": "user", "parts": [{"text": prompt_check}]}]}).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            resposta = result["candidates"][0]["content"]["parts"][0]["text"].strip().upper()

            if "SIM" in resposta:
                # Faz o routing para descobrir o novo agente
                return route_agent(message)
    except Exception:
        pass

    return None

# ========== ROUTING (escolhe o agente) ==========
def route_agent(message):
    """Classifica a mensagem e retorna o agente correto."""
    if not GEMINI_API_KEY:
        return "triagem"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"

    data = json.dumps({"contents": [{"role": "user", "parts": [{"text": ROUTING_PROMPT + "\n\nMensagem: " + message}]}]}).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            categoria = result["candidates"][0]["content"]["parts"][0]["text"].strip().lower()

            if categoria in AGENTES:
                return categoria
    except Exception:
        pass

    return "triagem"

# ========== CHAMAR AGENTE ESPECÍFICO ==========
def call_gemini_agent(message, agente_key, historico):
    if not GEMINI_API_KEY:
        return "⚠️ API do Gemini não configurada. Entre em contato pelo Telegram."

    agente = AGENTES[agente_key]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"

    # Monta o contexto com o prompt do agente + histórico
    contents = [{"role": "user", "parts": [{"text": agente["prompt"]}]}]

    for msg in historico[-8:]:  # Mantém últimas 8 mensagens
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["text"]}]})

    contents.append({"role": "user", "parts": [{"text": message}]})

    data = json.dumps({"contents": contents}).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            reply = result["candidates"][0]["content"]["parts"][0]["text"]
            return reply
    except urllib.error.HTTPError as e:
        return f"⚠️ Erro na API ({e.code}). Um contador será notificado."
    except Exception:
        return "⚠️ Erro de conexão. Um contador será notificado em breve."

# ========== TELEGRAM ==========
def notify_telegram(session_id, message, reply, agente):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    agente_nome = AGENTES.get(agente, {}).get("nome", agente)

    text = (
        f"🚨 <b>Novo atendimento - {agente_nome}</b>\n"
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
