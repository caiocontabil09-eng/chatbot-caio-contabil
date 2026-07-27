from flask import Flask, request, jsonify
import os
import json
import urllib.request
import urllib.error
import time
import random
import re
import csv
import io

app = Flask(__name__)

# ========== CONFIGURAÇÃO ==========
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ========== CONFIGURAÇÃO DA PLANILHA GOOGLE SHEETS ==========
# Aceita duas variáveis de ambiente:
#   GOOGLE_SHEET_ID          → nome padrão
#   ID_DA_PLANILHA_DO_GOOGLE → nome usado no Vercel do Caio Contábil
#
# FORMATO 1 (planilha normal): Se a URL for https://docs.google.com/spreadsheets/d/1ABC123xyz/edit
# O ID é: 1ABC123xyz
#
# FORMATO 2 (planilha já publicada): Se a URL for https://docs.google.com/spreadsheets/d/e/2PACX-.../pubhtml
# O ID é: 2PACX-1vTuLsYnIyy5xYymmdjb4UEBreRH7KAe8VxyHCnjr8uyc8FMEkUsuYuWzEhqiEfx84zSKpTz7Gaw-0iy
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "") or os.environ.get("ID_DA_PLANILHA_DO_GOOGLE", "")

# Monta a URL de CSV automaticamente conforme o formato do ID
def montar_url_csv(sheet_id):
    if not sheet_id:
        return ""
    # Se o ID começa com "2PACX-", é uma planilha já publicada (formato /e/)
    if sheet_id.startswith("2PACX-"):
        return f"https://docs.google.com/spreadsheets/d/e/{sheet_id}/pub?output=csv"
    # Caso contrário, é o ID normal da planilha
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

GOOGLE_SHEET_CSV_URL = montar_url_csv(GOOGLE_SHEET_ID)

# ========== DADOS OFICIAIS DO ESCRITÓRIO ==========
TELEFONE_OFICIAL = "(14) 99879-7126"

# ========== BASE DE CLIENTES (carregada da planilha) ==========
CLIENTES_DB = {}
ULTIMA_ATUALIZACAO = 0
CACHE_TTL_SEGUNDOS = 300  # 5 minutos

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
        "substituicao", "tributario", "tributário", "icms st", "diferimento",
        "apuração", "apuracao", "apurar", "apurado", "apurados", "periodo", "período",
        "mensal", "trimestral", "anual", "semestral"
    ],
    "dp_rh": [
        "folha", "pagamento", "esocial", "social", "férias", "ferias", "rescisão", "rescisao",
        "admissão", "admissao", "demissão", "demissao", "inss", "fgts", "trabalhista", "clt",
        "convenção", "convencao", "dissídio", "dissidio", "ppp", "rais", "dirf", "gfip",
        "funcionário", "funcionario", "empregado", "salário", "salario", "holerite", "contra-cheque",
        "trabalhador", "empregador", "13º", "decimo", "decimo terceiro",
        "hora extra", "adicional", "insalubridade", "periculosidade", "vt", "vr", "va",
        "homologação", "homologacao", "aviso prévio", "aviso previo", "justa causa", "justa-causa",
        "sem justa", "despido", "dispensado", "exoneracao", "exoneração",
        "estagiário", "estagiario", "pj", "mei funcionario", "pessoa jurídica",
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
        "debito", "débito", "credito", "crédito", "plano de contas", "balancete",
        "verificação", "verificacao", "razonete", "razonetes", "t", "conta", "contas",
        "fornecedor", "cliente", "banco", "caixa", "tesouraria", "fluxo",
        "fluxo de caixa", "demonstração do resultado", "demonstracao do resultado",
        "patrimonio liquido", "patrimônio líquido", "capital", "reserva", "lucros",
        "lucros acumulados", "prejuizos", "prejuízos", "dividendos", "juros",
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
        "arquivamento", "reabertura", "reabrir", "reorganização", "reorganizacao",
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
    "fiscal": "📊 **Especialista Fiscal** assumindo o atendimento...\n\nOlá! Sou o Especialista Fiscal da Caio Contábil. Em que posso ajudá-lo? 😊",
    "dp_rh": "👥 **Especialista DP/RH** assumindo o atendimento...\n\nOlá! Sou o Especialista de DP/RH da Caio Contábil. Em que posso ajudá-lo? 😊",
    "contabil": "📈 **Especialista Contábil** assumindo o atendimento...\n\nOlá! Sou o Especialista Contábil da Caio Contábil. Em que posso ajudá-lo? 😊",
    "societario": "🏢 **Especialista Societário** assumindo o atendimento...\n\nOlá! Sou o Especialista Societário da Caio Contábil. Em que posso ajudá-lo? 😊"
}

# ========== PROMPTS DOS AGENTES ==========
AGENTES = {
    "triagem": {
        "nome": "Ana",
        "emoji": "🤖",
        "prompt": """Você é "Ana", assistente virtual de triagem da Caio Contábil LTDA.

🎯 SEU TRABALHO:
1. Cumprimente o cliente de forma calorosa
2. Peça o CNPJ da empresa para verificar na base de clientes
3. Se o CNPJ constar na base → colete nome e e-mail, identifique a demanda e transfira
4. Se o CNPJ NÃO constar na base → informe que o canal é exclusivo para clientes e ofereça transferir para o Contador Caio
5. Seja breve e objetiva — máximo 3 frases por resposta

📞 TELEFONE DO ESCRITÓRIO: (14) 99879-7126
• Se pedirem telefone, forneça EXATAMENTE este número
• NUNCA invente outro número

⚠️ IMPORTANTE: Não resolva dúvidas técnicas. Só classifique e transfira."""
    },

    "fiscal": {
        "nome": "Especialista Fiscal",
        "emoji": "📊",
        "prompt": """Você é o "Especialista Fiscal" da Caio Contábil LTDA.

📊 SUA ESPECIALIDADE: Impostos, guias, obrigações acessórias, SPED, notas fiscais, CFOP, CST.

📝 REGRAS DE RESPOSTA (SIGA RIGOROSAMENTE):
1. Seja DIRETO e OBJETIVO — respostas curtas, máximo 4 linhas
2. NÃO peça CNPJ — ele já foi coletado pela Ana na triagem
3. Responda apenas o que foi perguntado, sem enrolar
4. Se não souber, diga que vai consultar o contador responsável
5. Ao final, pergunte se precisa de mais alguma coisa

📞 TELEFONE: (14) 99879-7126 — forneça SEMPRE este número, nunca invente outro.

⚠️ NUNCA dê orientação definitiva sem confirmar dados cadastrais."""
    },

    "dp_rh": {
        "nome": "Especialista DP/RH",
        "emoji": "👥",
        "prompt": """Você é o "Especialista de DP/RH" da Caio Contábil LTDA.

👥 SUA ESPECIALIDADE: Folha, eSocial, férias, rescisões, INSS, FGTS, admissões, demissões.

📝 REGRAS DE RESPOSTA (SIGA RIGOROSAMENTE):
1. Seja DIRETO e OBJETIVO — respostas curtas, máximo 4 linhas
2. NÃO peça CNPJ — ele já foi coletado pela Ana na triagem
3. Responda apenas o que foi perguntado, sem enrolar
4. Seja claro sobre prazos legais (ex: rescisão em 10 dias)
5. Seja empático com questões sensíveis

📞 TELEFONE: (14) 99879-7126 — forneça SEMPRE este número, nunca invente outro.

⚠️ NUNCA dê orientação trabalhista sem confirmar dados da empresa."""
    },

    "contabil": {
        "nome": "Especialista Contábil",
        "emoji": "📈",
        "prompt": """Você é o "Especialista Contábil" da Caio Contábil LTDA.

📈 SUA ESPECIALIDADE: Balanço, DRE, livros contábeis, escrituração, conciliação, indicadores.

📝 REGRAS DE RESPOSTA (SIGA RIGOROSAMENTE):
1. Seja DIRETO e OBJETIVO — respostas curtas, máximo 4 linhas
2. NÃO peça CNPJ — ele já foi coletado pela Ana na triagem
3. Use linguagem clara, evite jargões excessivos
4. Responda apenas o que foi perguntado, sem enrolar
5. Relacione dados contábeis com decisões de negócio quando relevante

📞 TELEFONE: (14) 99879-7126 — forneça SEMPRE este número, nunca invente outro.

⚠️ NUNCA dê parecer contábil sem acesso aos dados completos."""
    },

    "societario": {
        "nome": "Especialista Societário",
        "emoji": "🏢",
        "prompt": """Você é o "Especialista Societário" da Caio Contábil LTDA.

🏢 SUA ESPECIALIDADE: Abertura, alteração, encerramento de empresas, certidões, contratos, regularização.

📝 REGRAS DE RESPOSTA (SIGA RIGOROSAMENTE):
1. Seja DIRETO e OBJETIVO — respostas curtas, máximo 4 linhas
2. NÃO peça CNPJ — ele já foi coletado pela Ana na triagem
3. Explique o passo a passo de forma resumida
4. Dê prazos realistas (abertura: 5-15 dias úteis)
5. Seja paciente — processos societários geram ansiedade

📞 TELEFONE: (14) 99879-7126 — forneça SEMPRE este número, nunca invente outro.

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


# ========== CARREGAR CLIENTES DA PLANILHA ==========
def carregar_clientes_da_planilha():
    """
    Baixa a planilha pública do Google Sheets em formato CSV e carrega os clientes.
    A planilha deve ter as colunas: cnpj, razao_social, nome_fantasia, regime_tributario, atividade, responsavel, setor
    """
    global CLIENTES_DB, ULTIMA_ATUALIZACAO

    # Se não tiver ID da planilha configurado, usa fallback vazio
    if not GOOGLE_SHEET_ID:
        print("⚠️ GOOGLE_SHEET_ID não configurado. Usando base de clientes vazia.")
        CLIENTES_DB = {}
        ULTIMA_ATUALIZACAO = time.time()
        return

    # Verifica se o cache ainda é válido
    agora = time.time()
    if CLIENTES_DB and (agora - ULTIMA_ATUALIZACAO) < CACHE_TTL_SEGUNDOS:
        return

    try:
        req = urllib.request.Request(GOOGLE_SHEET_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            csv_data = response.read().decode('utf-8')

        leitor = csv.DictReader(io.StringIO(csv_data))
        novos_clientes = {}

        for linha in leitor:
            cnpj = linha.get("cnpj", "").strip()
            # Remove formatação do CNPJ (pontos, traços, barras)
            cnpj_limpo = re.sub(r'\D', '', cnpj)

            if len(cnpj_limpo) == 14:
                novos_clientes[cnpj_limpo] = {
                    "razao_social": linha.get("razao_social", "").strip(),
                    "nome_fantasia": linha.get("nome_fantasia", "").strip(),
                    "regime_tributario": linha.get("regime_tributario", "").strip(),
                    "atividade": linha.get("atividade", "").strip(),
                    "responsavel": linha.get("responsavel", "").strip(),
                    "setor": linha.get("setor", "").strip()
                }

        CLIENTES_DB = novos_clientes
        ULTIMA_ATUALIZACAO = agora
        print(f"✅ {len(CLIENTES_DB)} clientes carregados da planilha.")

    except Exception as e:
        print(f"⚠️ Erro ao carregar planilha: {e}")
        # Mantém a base anterior se houver, senão fica vazia
        if not CLIENTES_DB:
            CLIENTES_DB = {}
        ULTIMA_ATUALIZACAO = agora


# ========== FUNÇÃO DE SANITIZAÇÃO DE TELEFONE ==========
def sanitizar_telefone_na_resposta(reply, user_message):
    """
    Pós-processamento de segurança: garante que qualquer número de telefone
    na resposta seja o número oficial (14) 99879-7126.
    """
    pedindo_telefone = any(palavra in user_message.lower() for palavra in [
        "telefone", "ligar", "ligação", "ligacao", "contato", "whatsapp", "zap",
        "numero", "número", "fone", "celular", "call", "phone", "tel"
    ])

    if not pedindo_telefone:
        return reply

    padroes_telefone = [
        r'\(\d{2}\)\s?\d{4,5}-\d{4}',
        r'\(\d{2}\)\s?\d{4,5}-[Xx\*]{4}',
        r'\d{2}\s?\d{4,5}-\d{4}',
        r'\(\d{2}\)\s?\d{8,9}',
        r'\d{2}\s?\d{8,9}',
        r'\(\d{2}\)\s?\d{4}-\d{4}',
    ]

    reply_corrigida = reply
    for padrao in padroes_telefone:
        reply_corrigida = re.sub(padrao, TELEFONE_OFICIAL, reply_corrigida)

    if reply_corrigida != reply:
        reply_corrigida = re.sub(r'\*?\(número fictício[/\-]?padrão[^)]*\)\*?', '', reply_corrigida, flags=re.IGNORECASE)
        reply_corrigida = re.sub(r'\*?número fictício[^\*]*\*?', '', reply_corrigida, flags=re.IGNORECASE)
        reply_corrigida = re.sub(r'\*?padrão de atendimento[^\*]*\*?', '', reply_corrigida, flags=re.IGNORECASE)
        reply_corrigida = re.sub(r'\s{2,}', ' ', reply_corrigida)
        reply_corrigida = reply_corrigida.strip()

    return reply_corrigida


# ========== FUNÇÃO DE DETECÇÃO DE CNPJ/CPF ==========
def detectar_documento(message):
    """
    Detecta se a mensagem é apenas um CNPJ (14 dígitos) ou CPF (11 dígitos).
    Retorna uma tupla (tipo, numero) ou (None, None).
    """
    apenas_numeros = re.sub(r'\D', '', message)

    if len(apenas_numeros) == 14:
        return ("CNPJ", apenas_numeros)

    if len(apenas_numeros) == 11:
        return ("CPF", apenas_numeros)

    return (None, None)


# ========== FUNÇÃO DE VERIFICAÇÃO DE CLIENTE ==========
def verificar_cliente(cnpj):
    """
    Verifica se o CNPJ está na base de clientes do escritório.
    Recarrega a planilha se o cache expirou.
    Retorna os dados do cliente ou None.
    """
    carregar_clientes_da_planilha()
    return CLIENTES_DB.get(cnpj)


# ========== ROTAS ==========
@app.route('/')
def home():
    carregar_clientes_da_planilha()
    return jsonify({
        "status": "online",
        "service": "Caio Contábil - Multi-Agente API v5.1",
        "version": "5.1.0",
        "agentes": list(AGENTES.keys()),
        "clientes_carregados": len(CLIENTES_DB)
    })

@app.route('/chat', methods=['GET', 'POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if request.method == 'GET':
        carregar_clientes_da_planilha()
        return jsonify({
            "status": "online",
            "service": "Caio Contábil - Multi-Agente API v5.1",
            "version": "5.1.0",
            "clientes_carregados": len(CLIENTES_DB)
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
                "cnpj": None,
                "cliente_verificado": False,
                "fora_carteira": False,
                "transferencia_pendente": False,
                "agente_destino": None
            }

        sessao = sessions[session_id]
        sessao["msg_count"] += 1

        # === 1. DETECTA SE É CNPJ/CPF ===
        tipo_doc, numero_doc = detectar_documento(message)
        mensagem_para_gemini = message

        # Se for CNPJ na triagem e ainda não foi verificado
        if tipo_doc == "CNPJ" and sessao["agente_atual"] == "triagem" and not sessao["cliente_verificado"]:
            cliente = verificar_cliente(numero_doc)
            sessao["cnpj"] = numero_doc
            sessao["cliente_verificado"] = True

            if cliente:
                # Cliente encontrado na base
                info_cliente = f"Cliente verificado na base: {cliente['razao_social']}. Regime: {cliente['regime_tributario']}."
                mensagem_para_gemini = f"CNPJ confirmado na base de clientes: {numero_doc}. {info_cliente} O cliente agora precisa de atendimento."
            else:
                # Cliente NÃO encontrado na base
                sessao["fora_carteira"] = True
                reply = (
                    "Verificando nossa base de dados, constatei que sua empresa não faz parte da nossa carteira de clientes. "
                    "Sendo assim, peço desculpas, mas este canal é voltado para o atendimento de empresas parceiras.\n\n"
                    "Caso tenha pretensão de mudar de contabilidade, posso transferir seu atendimento para fazer diretamente com o Contador Caio. "
                    "Deseja prosseguir?"
                )

                sessao["historico"].append({"role": "user", "text": message})
                sessao["historico"].append({"role": "model", "text": reply})
                notify_telegram(session_id, message, reply, "triagem")

                return jsonify({
                    "reply": reply,
                    "session_id": session_id,
                    "agente": "triagem",
                    "agente_nome": "Ana",
                    "transferencia": False,
                    "fora_carteira": True
                })

        # Se for CNPJ/CPF fornecido como resposta (não na triagem)
        if tipo_doc and sessao["agente_atual"] != "triagem":
            mensagem_para_gemini = f"O cliente está fornecendo o {tipo_doc} que você solicitou: {numero_doc}"

        # === 2. DETECTA AGENTE por palavras-chave ===
        agente_detectado = detectar_agente_por_palavras(message)

        # === 3. LÓGICA DE TRANSFERÊNCIA ===
        agente_key = sessao["agente_atual"]
        transferencia = False

        if agente_detectado:
            if sessao["agente_atual"] == "triagem":
                # Só transfere se o cliente já foi verificado e está na carteira
                if sessao["cliente_verificado"] and not sessao["fora_carteira"]:
                    agente_key = agente_detectado
                    sessao["agente_atual"] = agente_key
                    transferencia = True
            elif agente_detectado != sessao["agente_atual"]:
                agente_key = agente_detectado
                sessao["agente_atual"] = agente_key
                transferencia = True

        # === 4. Chama Gemini com retry ===
        reply = call_gemini_com_retry(mensagem_para_gemini, agente_key, sessao["historico"], transferencia)

        # === 5. SANITIZAÇÃO DE SEGURANÇA ===
        reply = sanitizar_telefone_na_resposta(reply, message)

        # === 6. Se Gemini falhou, usa fallback ===
        if reply.startswith("⚠️"):
            if transferencia:
                reply = BOAS_VINDAS.get(agente_key, BOAS_VINDAS["triagem"])
            else:
                reply = f"Olá! Sou o {AGENTES[agente_key]['nome']}. Em que posso ajudá-lo? 😊"

        # === 7. Salva histórico ===
        sessao["historico"].append({"role": "user", "text": message})
        sessao["historico"].append({"role": "model", "text": reply})

        # === 8. Notifica Telegram ===
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

    contents = [{"role": "user", "parts": [{"text": agente["prompt"]}]}]

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

    for tentativa in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

            with urllib.request.urlopen(req, timeout=25) as response:
                result = json.loads(response.read().decode('utf-8'))
                reply = result["candidates"][0]["content"]["parts"][0]["text"]

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
