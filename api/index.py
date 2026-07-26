from flask import Flask, request, jsonify
import os
import json
import urllib.request
import urllib.error
import time
import random
import re

app = Flask(__name__)

# ========== CONFIGURAÇÃO ==========
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ========== DADOS OFICIAIS DO ESCRITÓRIO ==========
TELEFONE_OFICIAL = "(14) 99879-7126"

# ========== PALAVRAS-CHAVE PARA ROUTING ==========
PALAVRAS_CHAVE = {
    "fiscal": [
        "imposto", "impostos", "das", "darf", "gps", "guia", "guias", "sef", "rfb", "sped",
        "efd", "ecd", "ecf", "nota fiscal", "nfe", "cfop", "cst", "icms", "ipi", "pis",
        "cofins", "irpj", "csll", "simples", "presumido", "real", "tributação", "tributacao",
        "fiscal", "obrigação", "obrigacao", "acessória", "acessoria", "declaração", "declaracao",
        "pagamento", "recolhimento", "aliquota", "alíquota", "base de calculo", "base de cálculo",
        "iss", "iptu", "itbi", "iof", "cide", "contribuição", "contribuicao", "receita federal",
        "estadual", "municipal", "sintegra", "gnre", "sefaz", "suframa", "importação", "importacao",
        "exportação", "exportacao", "custo", "despesa", "dedução", "deducao", "crédito", "credito",
        "enquadramento", "anexo", "fator r", "fatorr", "retencao", "retenção", "substituição",
        "substituicao", "tributario", "tributário", "icms st", "diferimento", "diferimento",
        "apuração", "apuracao", "apurar", "apurado", "apurados", "periodo", "período",
        "mensal", "trimestral", "anual", "semestral", "apuracao", "apuração", "apurar"
    ],
    "dp_rh": [
        "folha", "pagamento", "esocial", "social", "férias", "ferias", "rescisão", "rescisao",
        "admissão", "admissao", "demissão", "demissao", "inss", "fgts", "trabalhista", "clt",
        "convenção", "convencao", "dissídio", "dissidio", "ppp", "rais", "dirf", "gfip",
        "funcionário", "funcionario", "empregado", "salário", "salario", "holerite", "contra-cheque",
        "trabalhador", "empregador", "férias", "ferias", "13º", "decimo", "decimo terceiro",
        "hora extra", "adicional", "insalubridade", "periculosidade", "vt", "vr", "va",
        "homologação", "homologacao", "aviso prévio", "aviso previo", "justa causa", "justa-causa",
        "sem justa", "despido", "dispensado", "demissão", "demissao", "exoneracao", "exoneração",
        "estagiário", "estagiario", "pj", "mei funcionario", "pessoa jurídica", "trabalhador",
        "emprego", "vaga", "contratação", "contratacao", "admitir", "demitir", "exonerar",
        "falta", "atestado", "licença", "licenca", "maternidade", "paternidade", "doença",
        "doenca", "acidente", "trabalho", "seguro", "desemprego", "seguro desemprego",
        "vale transporte", "vale refeição", "vale alimentação", "cesta", "ticket", "beneficio",
        "benefício", "plano de saude", "plano de saúde", "odontologico", "odontológico",
        "previdencia", "previdência", "aposentadoria", "pensão", "pensao", "dependente",
        "irrf", "imposto renda", "imposto de renda", "dedução dependente", "deducao dependente"
    ],
    "contabil": [
        "balanço", "balanco", "dre", "livro", "livros", "contábil", "contabil", "escrituração",
        "escrituracao", "conciliação", "conciliacao", "contas", "custo", "custos", "financeiro",
        "indicador", "demonstração", "demonstracao", "patrimonial", "ativo", "passivo",
        "receita", "despesa", "lucro", "prejuízo", "prejuizo", "caixa", "bancário", "bancario",
        "depreciação", "depreciacao", "estoque", "inventário", "inventario", "razão", "razao",
        "contábeis", "contabeis", "escriturar", "lancamento", "lançamento", "partida dobrada",
        "debito", "débito", "credito", "crédito", "plano de contas", "balancete", "balancete",
        "verificação", "verificacao", "razonete", "razonetes", "t", "conta", "contas",
        "fornecedor", "cliente", "banco", "caixa", "tesouraria", "tesouraria", "fluxo",
        "fluxo de caixa", "demonstração do resultado", "demonstracao do resultado",
        "patrimonio liquido", "patrimônio líquido", "capital", "reserva", "lucros",
        "lucros acumulados", "prejuizos", "prejuízos", "dividendos", "juros", "capital",
        "giro", "prazo medio", "prazo médio", "rotatividade", "rentabilidade", "margem",
        "ebitda", "ebit", "noi", "roi", "roe", "roa", "payback", "break-even", "ponto de equilibrio",
        "análise", "analise", "horizontal", "vertical", "comparativo", "comparativa"
    ],
    "societario": [
        "abertura", "abrir", "encerramento", "encerrar", "alteração", "alteracao", "baixa",
        "certidão", "certidao", "negativa", "jucesp", "contrato", "sócio", "socio", "cnae",
        "capital social", "regularização", "regularizacao", "inativa", "mei", "empresa",
        "constituição", "constituicao", "sociedade", "ltda", "eireli", "me", "epp",
        "enquadramento", "simples", "lucro presumido", "lucro real",
        "registro", "junta comercial", "receita federal", "prefeitura", "alvará", "alvara",
        "inscrição", "inscricao", "cnpj", "cpf", "razao social", "razão social", "fantasia",
        "nome fantasia", "endereço", "endereco", "sede", "filial", "matriz", "transformação",
        "transformacao", "fusão", "fusao", "cisão", "cisao", "incorporação", "incorporacao",
        "extinção", "extincao", "dissolução", "dissolucao", "liquidacao", "liquidação",
        "arquivamento", "arquivamento", "reabertura", "reabrir", "reorganização", "reorganizacao",
        "holding", "patrimonial", "participação", "participacao", "quotas", "ações", "acoes",
        "capital", "quota", "quotas", "sócios", "socios", "administrador", "diretor",
        "presidente", "vice", "conselho", "assembleia", "ata", "reunião", "reuniao",
        "protocolo", "registro", "cartório", "cartorio", "tabelião", "tabeliao",
        "procuração", "procuracao", "mandato", "representação", "representacao"
    ]
}

# ========== MENSAGENS DE BOAS-VINDAS POR AGENTE (fallback) ==========
BOAS_VINDAS = {
    "triagem": "Olá! 😊 Bem-vindo ao atendimento da Caio Contábil. Sou a Ana, sua assistente virtual de triagem.\n\nPara te direcionar ao contador certo, me conta: você precisa de ajuda com dúvida fiscal, folha de pagamento, contabilidade, ou abertura/alteração de empresa?",
    "fiscal": "📊 **Especialista Fiscal** assumindo o atendimento...\n\nOlá! Sou o Especialista Fiscal da Caio Contábil. Estou aqui para ajudar com suas dúvidas sobre impostos, guias, obrigações acessórias e toda a parte tributária.\n\nEm que posso ajudá-lo? 😊",
    "dp_rh": "👥 **Especialista DP/RH** assumindo o atendimento...\n\nOlá! Sou o Especialista de Departamento Pessoal da Caio Contábil. Estou aqui para ajudar com folha de pagamento, eSocial, férias, rescisões e toda a parte trabalhista.\n\nEm que posso ajudá-lo? 😊",
    "contabil": "📈 **Especialista Contábil** assumindo o atendimento...\n\nOlá! Sou o Especialista Contábil da Caio Contábil. Estou aqui para ajudar com balanço, DRE, livros contábeis, escrituração e análise financeira.\n\nEm que posso ajudá-lo? 😊",
    "societario": "🏢 **Especialista Societário** assumindo o atendimento...\n\nOlá! Sou o Especialista Societário da Caio Contábil. Estou aqui para ajudar com abertura, alteração, encerramento de empresas, certidões e contratos.\n\nEm que posso ajudá-lo? 😊"
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

📞 INFORMAÇÃO DE CONTATO — LEIA COM ATENÇÃO:
O ÚNICO telefone de contato do escritório Caio Contábil é: (14) 99879-7126

REGRAS ABSOLUTAS SOBRE TELEFONE:
• Se o cliente pedir telefone, WhatsApp, número para ligar, contato por ligação ou similar → FORNEÇA SEMPRE: (14) 99879-7126
• NUNCA diga "não tenho telefone", "não sei o telefone" ou "um contador vai ligar para você"
• NUNCA invente, crie ou imagine outro número de telefone
• NUNCA use números como (11) 3003-XXXX, (11) 5555-5555 ou qualquer outro — esses são FALSOS
• O número (14) 99879-7126 é o ÚNICO número verdadeiro e deve ser repetido EXATAMENTE assim

🚫 PROIBIDO:
• NUNCA invente e-mails, endereços ou outros dados de contato além do telefone (14) 99879-7126

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

📞 INFORMAÇÃO DE CONTATO — LEIA COM ATENÇÃO:
O ÚNICO telefone de contato do escritório Caio Contábil é: (14) 99879-7126

REGRAS ABSOLUTAS SOBRE TELEFONE:
• Se o cliente pedir telefone, WhatsApp, número para ligar, contato por ligação ou similar → FORNEÇA SEMPRE: (14) 99879-7126
• NUNCA diga "não tenho telefone", "não sei o telefone" ou "um contador vai ligar para você"
• NUNCA invente, crie ou imagine outro número de telefone
• NUNCA use números como (11) 3003-XXXX, (11) 5555-5555 ou qualquer outro — esses são FALSOS
• O número (14) 99879-7126 é o ÚNICO número verdadeiro e deve ser repetido EXATAMENTE assim

🚫 PROIBIDO:
• NUNCA invente e-mails, endereços ou outros dados de contato além do telefone (14) 99879-7126

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

📞 INFORMAÇÃO DE CONTATO — LEIA COM ATENÇÃO:
O ÚNICO telefone de contato do escritório Caio Contábil é: (14) 99879-7126

REGRAS ABSOLUTAS SOBRE TELEFONE:
• Se o cliente pedir telefone, WhatsApp, número para ligar, contato por ligação ou similar → FORNEÇA SEMPRE: (14) 99879-7126
• NUNCA diga "não tenho telefone", "não sei o telefone" ou "um contador vai ligar para você"
• NUNCA invente, crie ou imagine outro número de telefone
• NUNCA use números como (11) 3003-XXXX, (11) 5555-5555 ou qualquer outro — esses são FALSOS
• O número (14) 99879-7126 é o ÚNICO número verdadeiro e deve ser repetido EXATAMENTE assim

🚫 PROIBIDO:
• NUNCA invente e-mails, endereços ou outros dados de contato além do telefone (14) 99879-7126

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

📞 INFORMAÇÃO DE CONTATO — LEIA COM ATENÇÃO:
O ÚNICO telefone de contato do escritório Caio Contábil é: (14) 99879-7126

REGRAS ABSOLUTAS SOBRE TELEFONE:
• Se o cliente pedir telefone, WhatsApp, número para ligar, contato por ligação ou similar → FORNEÇA SEMPRE: (14) 99879-7126
• NUNCA diga "não tenho telefone", "não sei o telefone" ou "um contador vai ligar para você"
• NUNCA invente, crie ou imagine outro número de telefone
• NUNCA use números como (11) 3003-XXXX, (11) 5555-5555 ou qualquer outro — esses são FALSOS
• O número (14) 99879-7126 é o ÚNICO número verdadeiro e deve ser repetido EXATAMENTE assim

🚫 PROIBIDO:
• NUNCA invente e-mails, endereços ou outros dados de contato além do telefone (14) 99879-7126

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

📞 INFORMAÇÃO DE CONTATO — LEIA COM ATENÇÃO:
O ÚNICO telefone de contato do escritório Caio Contábil é: (14) 99879-7126

REGRAS ABSOLUTAS SOBRE TELEFONE:
• Se o cliente pedir telefone, WhatsApp, número para ligar, contato por ligação ou similar → FORNEÇA SEMPRE: (14) 99879-7126
• NUNCA diga "não tenho telefone", "não sei o telefone" ou "um contador vai ligar para você"
• NUNCA invente, crie ou imagine outro número de telefone
• NUNCA use números como (11) 3003-XXXX, (11) 5555-5555 ou qualquer outro — esses são FALSOS
• O número (14) 99879-7126 é o ÚNICO número verdadeiro e deve ser repetido EXATAMENTE assim

🚫 PROIBIDO:
• NUNCA invente e-mails, endereços ou outros dados de contato além do telefone (14) 99879-7126

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

# ========== FUNÇÃO DE SANITIZAÇÃO DE TELEFONE ==========
def sanitizar_telefone_na_resposta(reply, user_message):
    """
    Pós-processamento de segurança: garante que qualquer número de telefone
    na resposta seja o número oficial (14) 99879-7126.
    """
    # Detecta se o usuário está pedindo telefone/contato
    pedindo_telefone = any(palavra in user_message.lower() for palavra in [
        "telefone", "ligar", "ligação", "ligacao", "contato", "whatsapp", "zap",
        "numero", "número", "fone", "celular", "call", "phone", "tel"
    ])

    if not pedindo_telefone:
        return reply

    # Padrões de telefone brasileiro que podem ter sido inventados pelo modelo
    padroes_telefone = [
        r'\(\d{2}\)\s?\d{4,5}-\d{4}',           # (11) 99999-9999
        r'\(\d{2}\)\s?\d{4,5}-[Xx\*]{4}',        # (11) 3003-XXXX
        r'\d{2}\s?\d{4,5}-\d{4}',                 # 11 99999-9999
        r'\(\d{2}\)\s?\d{8,9}',                   # (11) 999999999
        r'\d{2}\s?\d{8,9}',                       # 11 999999999
        r'\(\d{2}\)\s?\d{4}-\d{4}',              # (11) 5555-5555
    ]

    telefone_oficial = TELEFONE_OFICIAL
    reply_corrigida = reply

    for padrao in padroes_telefone:
        reply_corrigida = re.sub(padrao, telefone_oficial, reply_corrigida)

    # Se a resposta continha um número fictício e foi substituído,
    # garante que não fique texto estranho ao redor
    if reply_corrigida != reply:
        # Remove menções a "fictício", "padrão", "exemplo" etc. que o modelo possa ter adicionado
        reply_corrigida = re.sub(r'\*?\(número fictício[/\-]?padrão[^)]*\)\*?', '', reply_corrigida, flags=re.IGNORECASE)
        reply_corrigida = re.sub(r'\*?número fictício[^\*]*\*?', '', reply_corrigida, flags=re.IGNORECASE)
        reply_corrigida = re.sub(r'\*?padrão de atendimento[^\*]*\*?', '', reply_corrigida, flags=re.IGNORECASE)
        reply_corrigida = re.sub(r'\s{2,}', ' ', reply_corrigida)
        reply_corrigida = reply_corrigida.strip()

    return reply_corrigida

# ========== ROTAS ==========
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Caio Contábil - Multi-Agente API v5.1",
        "version": "5.1.0",
        "agentes": list(AGENTES.keys())
    })

@app.route('/chat', methods=['GET', 'POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if request.method == 'GET':
        return jsonify({
            "status": "online",
            "service": "Caio Contábil - Multi-Agente API v5.1",
            "version": "5.1.0"
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
                "msg_count": 0,
                "transferencia_pendente": False,
                "agente_destino": None
            }

        sessao = sessions[session_id]
        sessao["msg_count"] += 1

        # 1. DETECTA AGENTE por palavras-chave
        agente_detectado = detectar_agente_por_palavras(message)

        # 2. LÓGICA DE TRANSFERÊNCIA
        agente_key = sessao["agente_atual"]
        transferencia = False

        # Se detectou agente específico
        if agente_detectado:
            # Se está na triagem → TRANSFERE para o agente detectado
            if sessao["agente_atual"] == "triagem":
                agente_key = agente_detectado
                sessao["agente_atual"] = agente_key
                transferencia = True
            # Se já está com outro agente e detectou diferente → TRANSFERE
            elif agente_detectado != sessao["agente_atual"]:
                agente_key = agente_detectado
                sessao["agente_atual"] = agente_key
                transferencia = True

        # 3. Chama Gemini com retry para rate limit
        reply = call_gemini_com_retry(message, agente_key, sessao["historico"], transferencia)

        # 4. SANITIZAÇÃO DE SEGURANÇA: corrige telefones inventados pelo modelo
        reply = sanitizar_telefone_na_resposta(reply, message)

        # 5. Se Gemini falhou completamente, usa fallback
        if reply.startswith("⚠️"):
            if transferencia:
                reply = BOAS_VINDAS.get(agente_key, BOAS_VINDAS["triagem"])
            else:
                reply = f"Olá! Sou o {AGENTES[agente_key]['nome']}. Em que posso ajudá-lo? 😊"

        # 6. Salva histórico
        sessao["historico"].append({"role": "user", "text": message})
        sessao["historico"].append({"role": "model", "text": reply})

        # 7. Notifica Telegram
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

# ========== CHAMAR GEMINI COM RETRY ==========
def call_gemini_com_retry(message, agente_key, historico, transferencia=False, max_retries=3):
    """Chama Gemini com retry exponencial para rate limit (429)."""

    if not GEMINI_API_KEY:
        return "⚠️ API do Gemini não configurada."

    agente = AGENTES[agente_key]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"

    # Monta o contexto
    contents = [{"role": "user", "parts": [{"text": agente["prompt"]}]}]

    # Se for transferência, adiciona contexto
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

    # Retry com backoff exponencial
    for tentativa in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

            with urllib.request.urlopen(req, timeout=25) as response:
                result = json.loads(response.read().decode('utf-8'))
                reply = result["candidates"][0]["content"]["parts"][0]["text"]

                # Se for transferência, adiciona prefixo visual
                if transferencia:
                    prefixo = f"{agente['emoji']} **{agente['nome']}** assumindo o atendimento...\n\n"
                    reply = prefixo + reply

                return reply

        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = (2 ** tentativa) + random.uniform(0, 1)
                print(f"Rate limit (429). Tentativa {tentativa + 1}/{max_retries}. Aguardando {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"Erro HTTP {e.code}")
                return f"⚠️ Erro na API ({e.code})."
        except Exception as ex:
            print(f"Erro de conexão: {ex}")
            return "⚠️ Erro de conexão."

    return "⚠️ Servidor ocupado. Tente novamente em alguns segundos."

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
