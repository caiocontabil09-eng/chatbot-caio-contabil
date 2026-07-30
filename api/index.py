import os
import json
import re
import requests
from google import genai
from google.genai import types
from flask import Flask, request, jsonify

app = Flask(__name__)

# ============================================================
# CORS MANUAL
# ============================================================
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# ============================================================
# CONFIGURAÇÕES
# ============================================================
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Modelo Gemini usado por todos os agentes (atendimento e auditoria).
# gemini-1.5-flash e gemini-2.0-flash já foram desativados pela Google (retornam 404).
# gemini-3.1-flash-lite tem shutdown previsto só para maio de 2027 - mais seguro por enquanto.
GEMINI_MODEL = "gemini-3.1-flash-lite"

# ============================================================
# TELEGRAM ALERTS
# ============================================================
def enviar_alerta_telegram(mensagem_texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem_texto,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[Telegram] Erro: {e}")

# ============================================================
# BASE DE CONHECIMENTO
# ============================================================
def carregar_base_radar():
    try:
        with open('dados_radar.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            "status_reforma_tributaria": {
                "pontos_conclusivos": {},
                "pontos_inconclusivos": {}
            },
            "diretrizes_trabalhistas_rh": {}
        }

base_conhecimento = carregar_base_radar()

BASES_POR_SETOR = {
    "sofia": base_conhecimento.get('status_reforma_tributaria', {}),
    "mateus": base_conhecimento,
    "clara": base_conhecimento.get('diretrizes_trabalhistas_rh', {}),
    "lucas": base_conhecimento,
    "tiago": base_conhecimento
}

# ============================================================
# PROMPTS DOS AGENTES
# ============================================================
PROMPTS_AGENTES = {
    "sofia": f"""Você é Sofia, recepcionista virtual da Caio Contábil. Você é a PRIMEIRA pessoa com quem o cliente fala.

FLUXO OBRIGATÓRIO — SIGA EXATAMENTE NESTA ORDEM:
1. SEMPRE comece com uma saudação calorosa.
2. PERGUNTE se o cliente já faz parte da carteira de clientes da Caio Contábil.
3. INDEPENDENTEMENTE da resposta (sim, não, talvez, qualquer coisa), agradeça e apresente o menu:
   "Perfeito! Com qual especialista você gostaria de falar? Escolha uma opção:
   1️⃣ Fiscal (Mateus)
   2️⃣ Pessoal / DP / RH (Clara)
   3️⃣ Contábil (Lucas)
   4️⃣ Reforma Tributária (Tiago)"
4. Se o cliente fizer uma pergunta técnica sobre Reforma Tributária, use a base abaixo. Se não souber, retorne EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
5. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações ou para a pergunta sobre carteira de clientes.

BASE TÉCNICA (Reforma Tributária): {json.dumps(base_conhecimento.get('status_reforma_tributaria', {}))}""",

    "mateus": f"""Você é Mateus, especialista fiscal da Caio Contábil. O cliente já foi triado pela Sofia e escolheu falar com VOCÊ.

REGRAS:
1. Saúde o cliente de forma profissional.
2. Responda perguntas fiscais usando a base técnica abaixo.
3. Se a pergunta fiscal NÃO estiver na base, retorne EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
4. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações.

BASE TÉCNICA: {json.dumps(base_conhecimento)}""",

    "clara": f"""Você é Clara, especialista em Departamento Pessoal e RH da Caio Contábil. O cliente já foi triado pela Sofia e escolheu falar com VOCÊ.

REGRAS:
1. Saúde o cliente de forma profissional.
2. Responda perguntas de DP/RH usando a base técnica abaixo.
3. Se a pergunta NÃO estiver na base, retorne EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
4. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações.

BASE TÉCNICA: {json.dumps(base_conhecimento.get('diretrizes_trabalhistas_rh', {}))}""",

    "lucas": f"""Você é Lucas, especialista contábil da Caio Contábil. O cliente já foi triado pela Sofia e escolheu falar com VOCÊ.

REGRAS:
1. Saúde o cliente de forma profissional.
2. Responda perguntas contábeis usando a base técnica abaixo.
3. Se a pergunta NÃO estiver na base, retorne EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
4. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações.

BASE TÉCNICA: {json.dumps(base_conhecimento)}""",

    "tiago": f"""Você é Tiago, especialista societário da Caio Contábil. O cliente já foi triado pela Sofia e escolheu falar com VOCÊ.

REGRAS:
1. Saúde o cliente de forma profissional.
2. Responda perguntas societárias usando a base técnica abaixo.
3. Se a pergunta NÃO estiver na base, retorne EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
4. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações.

BASE TÉCNICA: {json.dumps(base_conhecimento)}"""
}

PROMPT_AUDITOR_BRUNO = """Você é Bruno, Auditor Técnico da Caio Contábil.

CONTEXTO:
- Mensagem do cliente: {mensagem_cliente}
- Rascunho do agente: {rascunho}
- Base técnica do setor: {base_tecnica}

REGRAS:
1. Compare o rascunho com a base técnica.
2. Se o rascunho contiver '#CONTEUDO_INCONCLUSIVO#', responda: 'BLOQUEADO'
3. Se o rascunho inventar fatos fora da base, responda: 'BLOQUEADO'
4. Caso contrário, responda: 'APROVADO'
5. Em dúvida, responda 'APROVADO'."""

MENSAGEM_DR_CAIO_CEO = (
    "Olá, aqui é o Dr. Caio, CEO da Caio Contábil. Por se tratar de um ponto altamente complexo ou ainda "
    "inconclusivo na legislação, nossa equipe sênior vai te atender pessoalmente. Por favor, informe seu WhatsApp com DDD "
    "ou, se preferir, nos chame direto no nosso telefone oficial: (14) 99879-7126."
)

# ============================================================
# ROTEAMENTO DE MENU / TROCA DE ATENDENTE
# ============================================================
TEXTO_MENU = (
    "Perfeito! Com qual especialista você gostaria de falar? Escolha uma opção:\n"
    "1️⃣ Fiscal (Mateus)\n"
    "2️⃣ Pessoal / DP / RH (Clara)\n"
    "3️⃣ Contábil (Lucas)\n"
    "4️⃣ Reforma Tributária (Tiago)"
)

# Mensagem exata (após strip + lower) que o cliente digitou -> setor de destino
# (usado só para as respostas curtas do menu, tipo clicar em "2")
OPCOES_MENU = {
    "1": "mateus", "1️⃣": "mateus",
    "2": "clara", "2️⃣": "clara",
    "3": "lucas", "3️⃣": "lucas",
    "4": "tiago", "4️⃣": "tiago",
}

# Palavras/nomes que podem aparecer em QUALQUER parte de uma frase livre
# ("quero falar com o Matheus", "minha dúvida é sobre RH") -> setor de destino
PADROES_SETOR = {
    "mateus": [r"\bmateus\b", r"\bmatheus\b", r"\bfiscal\b"],
    "clara": [r"\bclara\b", r"\bdp\b", r"\brh\b", r"departamento pessoal", r"recursos humanos", r"\btrabalhista\b"],
    "lucas": [r"\blucas\b", r"\bcontabil\b", r"\bcontábil\b", r"\bcontabilidade\b"],
    "tiago": [r"\btiago\b", r"reforma tributaria", r"reforma tributária", r"\bsocietario\b", r"\bsocietário\b"],
}

# Frases genéricas (sem citar nome de agente) que indicam pedido de troca
FRASES_TROCA_ATENDENTE = [
    "falar com outro", "falar com outra pessoa", "trocar de atendente", "trocar atendente",
    "voltar ao menu", "outro especialista", "menu principal", "mudar de setor", "menu de novo",
    "outro assunto", "falar com alguem", "falar com alguém",
]

def detectar_pedido_de_troca(mensagem):
    msg = mensagem.strip().lower()
    return any(frase in msg for frase in FRASES_TROCA_ATENDENTE)

def detectar_setor_mencionado(mensagem):
    """Procura nome de agente ou palavra-chave de setor em qualquer parte da frase."""
    msg = mensagem.lower()
    for setor, padroes in PADROES_SETOR.items():
        if any(re.search(padrao, msg) for padrao in padroes):
            return setor
    return None

def detectar_escolha_menu(mensagem):
    """Só bate se a mensagem inteira for exatamente uma opção numérica do menu."""
    msg = mensagem.strip().lower()
    return OPCOES_MENU.get(msg)

# ============================================================
# UTILITÁRIOS
# ============================================================
def extrair_texto_seguro(resposta):
    if not resposta:
        return ""
    try:
        if resposta.text:
            return resposta.text
    except Exception:
        pass
    try:
        if resposta.candidates and len(resposta.candidates) > 0:
            parts = resposta.candidates[0].content.parts
            return "".join(part.text for part in parts if hasattr(part, 'text') and part.text)
    except Exception:
        pass
    return ""

# ============================================================
# LÓGICA PRINCIPAL
# ============================================================
def responder_cliente(setor_escolhido, mensagem_cliente):
    agente_nome = setor_escolhido.lower() if setor_escolhido.lower() in PROMPTS_AGENTES else "sofia"

    try:
        resposta_raw = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=mensagem_cliente,
            config=types.GenerateContentConfig(
                system_instruction=PROMPTS_AGENTES[agente_nome]
            )
        )
        resposta_rascunho = extrair_texto_seguro(resposta_raw)
    except Exception as e:
        print(f"[Erro Gemini - Atendimento] {e}")
        return "Desculpe, estou com dificuldades técnicas no momento. Tente novamente em instantes."

    # Auditoria condicional: só audita se contiver #CONTEUDO_INCONCLUSIVO#
    if "#CONTEUDO_INCONCLUSIVO#" not in resposta_rascunho:
        return resposta_rascunho

    try:
        base_do_setor = BASES_POR_SETOR.get(agente_nome, {})
        prompt_auditor = PROMPT_AUDITOR_BRUNO.format(
            mensagem_cliente=mensagem_cliente,
            rascunho=resposta_rascunho,
            base_tecnica=json.dumps(base_do_setor)
        )
        auditor_raw = client.models.generate_content(
            model=GEMINI_MODEL,
            contents="Audite.",
            config=types.GenerateContentConfig(
                system_instruction=prompt_auditor
            )
        )
        analise_seguranca = extrair_texto_seguro(auditor_raw).strip().upper()
    except Exception as e:
        print(f"[Erro Gemini - Auditor] {e}")
        analise_seguranca = "APROVADO"

    if "BLOQUEADO" in analise_seguranca:
        alerta = (
            "🚨 *ALERTA - CAIO CONTÁBIL IA*\n\n"
            f"• *Setor:* {agente_nome.upper()}\n"
            f"• *Cliente:* \"{mensagem_cliente}\"\n\n"
            "⚠️ _Bruno bloqueou. Dr. Caio assumiu._"
        )
        enviar_alerta_telegram(alerta)
        return MENSAGEM_DR_CAIO_CEO

    return resposta_rascunho

# ============================================================
# PROCESSAMENTO CENTRAL
# ============================================================
def processar_requisicao():
    dados = request.get_json() or {}

    mensagem = dados.get("mensagem") or dados.get("message") or dados.get("text") or ""
    setor = (dados.get("setor") or dados.get("department") or "sofia").lower()

    if not mensagem:
        return jsonify({
            "resposta": "Olá! Sou a Sofia, recepcionista virtual da Caio Contábil. Como posso ajudar você hoje? 😊",
            "setor": "sofia"
        })

    # Detecta telefone/WhatsApp
    padrao_telefone = r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}-\d{4}|\d{4}-\d{4}|9\d{8}|\d{8})'
    telefones = re.findall(padrao_telefone, mensagem)

    if telefones:
        alerta_lead = (
            "✅ *NOVO CLIENTE CAPTURADO!*\n\n"
            f"• *WhatsApp:* `{telefones}`\n"
            f"• *Mensagem:* \"{mensagem}\"\n\n"
            "📞 _Contatar via (14) 99879-7126._"
        )
        enviar_alerta_telegram(alerta_lead)
        return jsonify({
            "resposta": "Perfeito! Já captei o seu número. Em instantes um contador especialista vai te chamar. Obrigado! 🙏",
            "setor": setor
        })

    # Cliente citou o nome de um agente ou palavra-chave do setor em qualquer
    # parte da frase ("quero falar com o Matheus", "minha dúvida é de RH") -> troca na hora
    setor_mencionado = detectar_setor_mencionado(mensagem)
    if setor_mencionado and setor_mencionado != setor:
        resposta_boas_vindas = responder_cliente(
            setor_mencionado,
            "Se apresente brevemente em uma frase e pergunte como pode ajudar."
        )
        return jsonify({"resposta": resposta_boas_vindas, "setor": setor_mencionado})

    # Cliente pediu para trocar de atendente sem citar nome -> reabre o menu
    if detectar_pedido_de_troca(mensagem):
        return jsonify({"resposta": TEXTO_MENU, "setor": "sofia"})

    # Mensagem inteira é exatamente uma opção numérica do menu (ex: cliente digitou só "2")
    setor_escolhido = detectar_escolha_menu(mensagem)
    if setor_escolhido and setor_escolhido != setor:
        resposta_boas_vindas = responder_cliente(
            setor_escolhido,
            "Se apresente brevemente em uma frase e pergunte como pode ajudar."
        )
        return jsonify({"resposta": resposta_boas_vindas, "setor": setor_escolhido})

    resposta_final = responder_cliente(setor, mensagem)
    return jsonify({"resposta": resposta_final, "setor": setor})

# ============================================================
# ROTAS
# ============================================================
@app.route("/", methods=["GET", "POST", "OPTIONS"])
def home_atendimento():
    if request.method == "GET":
        return jsonify({"status": "Servidor Caio Contábil IA Ativo e Operacional 🚀"})
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"})
    return processar_requisicao()

@app.route("/chat", methods=["GET", "POST", "OPTIONS"])
def chat_atendimento():
    if request.method == "GET":
        return jsonify({"status": "Rota /chat ativa e operacional ✅"})
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"})
    return processar_requisicao()

@app.route("/<path:path>", methods=["GET", "POST", "OPTIONS"])
def catch_all(path):
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"})
    return home_atendimento()
