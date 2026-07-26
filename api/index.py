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

# ========== PALAVRAS-CHAVE PARA ROUTING ==========
PALAVRAS_CHAVE = {
    "fiscal": [
        "imposto", "impostos", "das", "darf", "gps", "guia", "guias", "sef", "rfb", "sped",
        "efd", "ecd", "ecf", "nota fiscal", "nfe", "cfop", "cst", "icms", "ipi", "pis",
        "cofins", "irpj", "csll", "simples", "presumido", "real", "tributação", "tributacao",
        "fiscal", "obrigação", "obrigacao", "acessória", "acessoria", "declaração", "declaracao",
        "pagamento", "recolhimento", "aliquota", "alíquota", "base de calculo", "base de cálculo"
    ],
    "dp_rh": [
        "folha", "pagamento", "esocial", "social", "férias", "ferias", "rescisão", "rescisao",
        "admissão", "admissao", "demissão", "demissao", "inss", "fgts", "trabalhista", "clt",
        "convenção", "convencao", "dissídio", "dissidio", "ppp", "rais", "dirf", "gfip",
        "funcionário", "funcionario", "empregado", "salário", "salario", "holerite", "contra-cheque",
        "trabalhador", "empregador", "férias", "ferias", "13º", "decimo", "decimo terceiro",
        "hora extra", "adicional", "insalubridade", "periculosidade", "vt", "vr", "va"
    ],
    "contabil": [
        "balanço", "balanco", "dre", "livro", "livros", "contábil", "contabil", "escrituração",
        "escrituracao", "conciliação", "conciliacao", "contas", "custo", "custos", "financeiro",
        "indicador", "demonstração", "demonstracao", "patrimonial", "ativo", "passivo",
        "receita", "despesa", "lucro", "prejuízo", "prejuizo", "caixa", "bancário", "bancario",
        "depreciação", "depreciacao", "estoque", "inventário", "inventario", "razão", "razao"
    ],
    "societario": [
        "abertura", "abrir", "encerramento", "encerrar", "alteração", "alteracao", "baixa",
        "certidão", "certidao", "negativa", "jucesp", "contrato", "sócio", "socio", "cnae",
        "capital social", "regularização", "regularizacao", "inativa", "mei", "empresa",
        "constituição", "constituicao", "sociedade", "ltDA", "eireli", "me", "epp",
        "enquadramento", "enquadramento", "simples", "lucro presumido", "lucro real",
        "registro", "junta comercial", "receita federal", "prefeitura", "alvará", "alvara"
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
2. Identifique o tipo de demanda:
   • 📊 FISCAL → Dúvidas sobre impostos, DAS, guias, SEF, RFB, obrigações acessórias
   • 👥 DP/RH → Folha de pagamento, eSocial, férias, rescisões, INSS, FGTS
   • 📈 CONTÁBIL → Balanço, DRE, livros contábeis, escrituração, análise financeira
   • 🏢 SOCIETÁRIO → Abertura, alteração, encerramento de empresas, certidões, contratos
3. Colete: nome, CNPJ/CPF, e-mail
4. Informe que o especialista vai assumir o atendimento
5. Seja breve e objetiva

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
1. SEMPRE dê as boas-vindas ao assumir o atendimento
2. Pergunte "Em que posso ajudá-lo?" ou "Qual é a sua dúvida?"
3. Seja técnico mas didático
4. Explique o "porquê" das orientações
5. Sempre confirme CNPJ da empresa
6. Se não souber algo, diga que vai consultar o contador responsável
7. Ao final, pergunte se precisa de mais alguma coisa

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
1. SEMPRE dê as boas-vindas ao assumir o atendimento
2. Pergunte "Em que posso ajudá-lo?" ou "Qual é a sua dúvida?"
3. Seja claro sobre prazos legais (ex: rescisão em 10 dias)
4. Explique os cálculos quando solicitado
5. Sempre peça a quantidade de funcionários
6. Oriente sobre documentos necessários
7. Seja empático com questões trabalhistas sensíveis

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
1. SEMPRE dê as boas-vindas ao assumir o atendimento
2. Pergunte "Em que posso ajudá-lo?" ou "Qual é a sua dúvida?"
3. Use linguagem clara, evite jargões excessivos
4. Explique a importância de cada demonstração
5. Oriente sobre prazos de entrega dos livros
6. Sugira melhorias quando apropriado
7. Relacione dados contábeis com decisões de negócio

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
1. SEMPRE dê as boas-vindas ao assumir o atendimento
2. Pergunte "Em que posso ajudá-lo?" ou "Qual é a sua dúvida?"
3. Explique o passo a passo de cada processo
4. Informe documentos necessários com antecedência
5. Dê prazos realistas (abertura: 5-15 dias úteis)
6. Explique custos envolvidos quando perguntado
7. Seja paciente — processos societários geram ansiedade

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
        "service": "Caio Contábil - Multi-Agente API v4.2",
        "version": "4.2.0",
        "agentes": list(AGENTES.keys())
    })

@app.route('/chat', methods=['GET', 'POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if request.method == 'GET':
        return jsonify({
            "status": "online",
            "service": "Caio Contábil - Multi-Agente API v4.2",
            "version": "4.2.0"
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
                "msg_count": 0,
                "agente_detectado": None
            }

        sessao = sessions[session_id]
        sessao["msg_count"] += 1

        # 1. DETECTA AGENTE por palavras-chave
        agente_detectado = detectar_agente_por_palavras(message)

        # 2. LÓGICA DE TRANSFERÊNCIA
        agente_key = sessao["agente_atual"]
        transferencia = False

        # Se detectou agente específico e está na triagem → TRANSFERE
        if agente_detectado and sessao["agente_atual"] == "triagem":
            agente_key = agente_detectado
            sessao["agente_atual"] = agente_key
            sessao["agente_detectado"] = agente_detectado
            transferencia = True

        # Se detectou agente diferente do atual → TRANSFERE
        elif agente_detectado and agente_detectado != sessao["agente_atual"]:
            agente_key = agente_detectado
            sessao["agente_atual"] = agente_key
            transferencia = True

        # 3. Chama Gemini com o agente correto
        reply = call_gemini_agent(message, agente_key, sessao["historico"], transferencia)

        # 4. Salva histórico
        sessao["historico"].append({"role": "user", "text": message})
        sessao["historico"].append({"role": "model", "text": reply})

        # 5. Notifica Telegram
        notify_telegram(session_id, message, reply, agente_key)

        return jsonify({
            "reply": reply,
            "session_id": session_id,
            "agente": agente_key,
            "agente_nome": AGENTES[agente_key]["nome"],
            "transferencia": transferencia
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== DETECTAR AGENTE ==========
def detectar_agente_por_palavras(message):
    """Detecta o agente correto baseado em palavras-chave."""

    pontuacao = {"fiscal": 0, "dp_rh": 0, "contabil": 0, "societario": 0}

    for categoria, palavras in PALAVRAS_CHAVE.items():
        for palavra in palavras:
            if palavra in message:
                pontuacao[categoria] += 1

    max_pontos = max(pontuacao.values())
    if max_pontos > 0:
        for cat, pts in pontuacao.items():
            if pts == max_pontos:
                return cat

    return None

# ========== CHAMAR AGENTE ==========
def call_gemini_agent(message, agente_key, historico, transferencia=False):
    if not GEMINI_API_KEY:
        return "⚠️ API do Gemini não configurada. Entre em contato pelo Telegram."

    agente = AGENTES[agente_key]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"

    # Monta o contexto
    contents = [{"role": "user", "parts": [{"text": agente["prompt"]}]}]

    # Se for transferência, adiciona contexto da conversa anterior
    if transferencia and len(historico) > 0:
        transfer_context = "Você está assumindo este atendimento agora. A conversa anterior foi:\n"
        for msg in historico[-4:]:
            quem = "Cliente" if msg["role"] == "user" else "Ana (triagem)"
            transfer_context += f"{quem}: {msg['text']}\n"
        transfer_context += "\nAgora você deve dar as boas-vindas ao cliente e perguntar como pode ajudá-lo."
        contents.append({"role": "user", "parts": [{"text": transfer_context}]})

    for msg in historico[-6:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["text"]}]})

    contents.append({"role": "user", "parts": [{"text": message}]})

    data = json.dumps({"contents": contents}).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode('utf-8'))
            reply = result["candidates"][0]["content"]["parts"][0]["text"]

            # Se for transferência, adiciona prefixo visual
            if transferencia:
                prefixo = f"{agente['emoji']} **{agente['nome']}** assumindo o atendimento...\n\n"
                reply = prefixo + reply

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
    emoji = AGENTES.get(agente, {}).get("emoji", "🤖")

    text = (
        f"{emoji} <b>{agente_nome}</b>\n"
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
