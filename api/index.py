from flask import Flask, request, jsonify
import os
import json
import urllib.request
import urllib.error
import re

app = Flask(__name__)

# ========== CONFIGURAÇÃO ==========
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ========== PALAVRAS-CHAVE PARA ROUTING ==========
PALAVRAS_CHAVE = {
    "fiscal": [
        "imposto", "impostos", "das", "darf", "gps", "guia", "guias", "sef", "rfb", "sped",
        "efd", "ecd", "ecf", "nota fiscal", "nfe", "cfop", "cst", "icms", "ipi", "pis",
        "cofins", "irpj", "csll", "simples", "presumido", "real", "tributação", "fiscal"
    ],
    "dp_rh": [
        "folha", "pagamento", "esocial", "social", "férias", "ferias", "rescisão", "rescisao",
        "admissão", "admissao", "demissão", "demissao", "inss", "fgts", "trabalhista", "clt",
        "convenção", "dissídio", "dissidio", "ppp", "rais", "dirf", "gfip", "funcionário",
        "funcionario", "empregado", "salário", "salario", "holerite", "contra-cheque"
    ],
    "contabil": [
        "balanço", "balanco", "dre", "livro", "livros", "contábil", "contabil", "escrituração",
        "escrituracao", "conciliação", "conciliacao", "contas", "custo", "custos", "financeiro",
        "indicador", "demonstração", "demonstracao", "patrimonial", "ativo", "passivo"
    ],
    "societario": [
        "abertura", "abrir", "encerramento", "encerrar", "alteração", "alteracao", "baixa",
        "certidão", "certidao", "negativa", "jucesp", "contrato", "sócio", "socio", "cnae",
        "capital social", "regularização", "regularizacao", "inativa", "mei", "empresa"
    ]
}

# ========== PROMPTS DOS AGENTES ==========
AGENTES = {
    "triagem": {
        "nome": "Ana",
        "emoji": "🤖",
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
        "service": "Caio Contábil - Multi-Agente API v4.1",
        "version": "4.1.0",
        "agentes": list(AGENTES.keys())
    })

@app.route('/chat', methods=['GET', 'POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if request.method == 'GET':
        return jsonify({
            "status": "online",
            "service": "Caio Contábil - Multi-Agente API v4.1",
            "version": "4.1.0"
        })

    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip().lower()
        session_id = data.get("session_id", "default")

        if not message:
            return jsonify({"error": "Mensagem vazia"}), 400

        # Inicializa sessão
        if session_id not in sessions:
            sessions[session_id] = {
                "agente_atual": "triagem",
                "historico": [],
                "dados_cliente": {},
                "primeira_msg": True
            }

        sessao = sessions[session_id]

        # 1. ROUTING por palavras-chave (rápido, sem API)
        novo_agente = detectar_agente_por_palavras(message, sessao["agente_atual"])

        # 2. Se for primeira mensagem ou não detectou agente, usa triagem
        if sessao["primeira_msg"] or novo_agente is None:
            sessao["primeira_msg"] = False
            agente_key = "triagem"
        else:
            agente_key = novo_agente

        # 3. Se mudou de agente, avisa
        transferencia = ""
        if agente_key != sessao["agente_atual"] and sessao["agente_atual"] != "triagem":
            transferencia = f"{AGENTES[agente_key]['emoji']} **Transferindo para o {AGENTES[agente_key]['nome']}**...\n\n"

        sessao["agente_atual"] = agente_key

        # 4. Chama Gemini UMA VEZ com o prompt do agente
        reply = call_gemini_agent(message, agente_key, sessao["historico"])

        if transferencia:
            reply = transferencia + reply

        # 5. Salva histórico
        sessao["historico"].append({"role": "user", "text": message})
        sessao["historico"].append({"role": "model", "text": reply})

        # 6. Notifica Telegram
        notify_telegram(session_id, message, reply, agente_key)

        return jsonify({
            "reply": reply,
            "session_id": session_id,
            "agente": agente_key,
            "agente_nome": AGENTES[agente_key]["nome"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== DETECTAR AGENTE POR PALAVRAS-CHAVE ==========
def detectar_agente_por_palavras(message, agente_atual):
    """Detecta o agente correto baseado em palavras-chave na mensagem."""

    # Se está na triagem, deixa o Gemini decidir na primeira resposta
    if agente_atual == "triagem":
        return None

    # Verifica palavras-chave em cada categoria
    pontuacao = {"fiscal": 0, "dp_rh": 0, "contabil": 0, "societario": 0}

    for categoria, palavras in PALAVRAS_CHAVE.items():
        for palavra in palavras:
            if palavra in message:
                pontuacao[categoria] += 1

    # Se detectou palavras de outra categoria, muda
    max_pontos = max(pontuacao.values())
    if max_pontos > 0:
        for cat, pts in pontuacao.items():
            if pts == max_pontos and cat != agente_atual:
                return cat

    # Mantém o agente atual se não detectou mudança
    return agente_atual

# ========== CHAMAR AGENTE ==========
def call_gemini_agent(message, agente_key, historico):
    if not GEMINI_API_KEY:
        return "⚠️ API do Gemini não configurada. Entre em contato pelo Telegram."

    agente = AGENTES[agente_key]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"

    # Monta o contexto
    contents = [{"role": "user", "parts": [{"text": agente["prompt"]}]}]

    for msg in historico[-6:]:  # Mantém últimas 6 mensagens
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["text"]}]})

    contents.append({"role": "user", "parts": [{"text": message}]})

    data = json.dumps({"contents": contents}).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
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
