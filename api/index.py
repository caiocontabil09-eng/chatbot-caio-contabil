import os
import json
import re
import requests
import google.generativeai as genai
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
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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

# ============================================================
# BASES POR SETOR (para o Bruno auditar)
# ============================================================
BASES_POR_SETOR = {
    "sofia": base_conhecimento.get('status_reforma_tributaria', {}),
    "mateus": base_conhecimento,
    "clara": base_conhecimento.get('diretrizes_trabalhistas_rh', {}),
    "lucas": base_conhecimento,
    "tiago": base_conhecimento
}

# ============================================================
# PROMPTS DOS AGENTES — SAUDAÇÕES PERMITIDAS
# ============================================================
PROMPTS_AGENTES = {
    "sofia": f"""Você é Sofia, especialista em comunicação e Reforma Tributária na Caio Contábil.

REGRAS:
1. Responda saudações (oi, olá, bom dia, tudo bem?) de forma natural e simpática.
2. Responda perguntas gerais sobre a Caio Contábil de forma cordial.
3. Use a BASE TÉCNICA abaixo SOMENTE quando o cliente perguntar especificamente sobre Reforma Tributária.
4. Se o cliente fizer uma pergunta técnica sobre Reforma Tributária que NÃO esteja na base abaixo, responda EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
5. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações ou perguntas simples.

BASE TÉCNICA (Reforma Tributária): {json.dumps(base_conhecimento.get('status_reforma_tributaria', {}))}""",

    "mateus": f"""Você é Mateus, especialista fiscal da Caio Contábil.

REGRAS:
1. Responda saudações e perguntas gerais de forma natural.
2. Use a BASE TÉCNICA abaixo SOMENTE para perguntas fiscais específicas.
3. Se o cliente perguntar algo fiscal que NÃO esteja na base, responda EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
4. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações.

BASE TÉCNICA: {json.dumps(base_conhecimento)}""",

    "clara": f"""Você é Clara, especialista em Departamento Pessoal e RH na Caio Contábil.

REGRAS:
1. Responda saudações e perguntas gerais de forma natural.
2. Use a BASE TÉCNICA abaixo SOMENTE para perguntas de DP/RH específicas.
3. Se o cliente perguntar algo de DP/RH que NÃO esteja na base, responda EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
4. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações.

BASE TÉCNICA: {json.dumps(base_conhecimento.get('diretrizes_trabalhistas_rh', {}))}""",

    "lucas": f"""Você é Lucas, especialista contábil na Caio Contábil.

REGRAS:
1. Responda saudações e perguntas gerais de forma natural.
2. Use a BASE TÉCNICA abaixo SOMENTE para perguntas contábeis específicas.
3. Se o cliente perguntar algo contábil que NÃO esteja na base, responda EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
4. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações.

BASE TÉCNICA: {json.dumps(base_conhecimento)}""",

    "tiago": f"""Você é Tiago, especialista societário na Caio Contábil.

REGRAS:
1. Responda saudações e perguntas gerais de forma natural.
2. Use a BASE TÉCNICA abaixo SOMENTE para perguntas societárias específicas.
3. Se o cliente perguntar algo societário que NÃO esteja na base, responda EXATAMENTE: '#CONTEUDO_INCONCLUSIVO#'
4. NUNCA retorne '#CONTEUDO_INCONCLUSIVO#' para saudações.

BASE TÉCNICA: {json.dumps(base_conhecimento)}"""
}

# ============================================================
# PROMPT DO BRUNO — AUDITORIA COM BASE TÉCNICA
# ============================================================
PROMPT_AUDITOR_BRUNO = """Você é Bruno, o Auditor Técnico de riscos da Caio Contábil.

CONTEXTO:
- Mensagem do cliente: {mensagem_cliente}
- Rascunho do agente: {rascunho}
- Base técnica do setor: {base_tecnica}

TAREFA:
1. Compare o rascunho com a base técnica fornecida.
2. Verifique se o rascunho contém fatos, números, prazos ou enquadramentos que NÃO estejam na base técnica.
3. Se o rascunho contiver EXATAMENTE o texto '#CONTEUDO_INCONCLUSIVO#', responda apenas: 'BLOQUEADO'
4. Se o rascunho inventar informações que não estão na base técnica, responda apenas: 'BLOQUEADO'
5. Se o rascunho for uma saudação, explicação geral ou resposta baseada corretamente na base técnica, responda apenas: 'APROVADO'
6. Se não tiver certeza, responda 'APROVADO' para não travar o atendimento.

Responda APENAS 'APROVADO' ou 'BLOQUEADO'."""

MENSAGEM_DR_CAIO_CEO = (
    "Olá, aqui é o Dr. Caio, CEO da Caio Contábil. Por se tratar de um ponto altamente complexo ou ainda "
    "inconclusivo na legislação, nossa equipe sênior vai te atender pessoalmente. Por favor, informe seu WhatsApp com DDD "
    "ou, se preferir, nos chame direto no nosso telefone oficial: (14) 99879-7126."
)

# ============================================================
# UTILITÁRIOS
# ============================================================
def extrair_texto_seguro(resposta):
    if not resposta:
        return ""
    try:
        return resposta.text
    except Exception:
        try:
            if resposta.candidates and len(resposta.candidates) > 0:
                parts = resposta.candidates[0].content.parts
                return "".join(part.text for part in parts if hasattr(part, 'text'))
        except Exception:
            pass
    return ""

# ============================================================
# LÓGICA PRINCIPAL — AUDITORIA CONDICIONAL
# ============================================================
def responder_cliente(setor_escolhido, mensagem_cliente):
    agente_nome = setor_escolhido.lower() if setor_escolhido.lower() in PROMPTS_AGENTES else "sofia"

    # 1. Chama o agente
    try:
        model_atendimento = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=PROMPTS_AGENTES[agente_nome]
        )
        resposta_raw = model_atendimento.generate_content(mensagem_cliente)
        resposta_rascunho = extrair_texto_seguro(resposta_raw)
    except Exception as e:
        print(f"[Erro Gemini - Atendimento] {e}")
        return "Desculpe, estou com dificuldades técnicas no momento. Tente novamente em instantes."

    # 2. Se NÃO contiver #CONTEUDO_INCONCLUSIVO#, retorna direto (economiza 1 chamada Gemini)
    if "#CONTEUDO_INCONCLUSIVO#" not in resposta_rascunho:
        return resposta_rascunho

    # 3. Se contiver #CONTEUDO_INCONCLUSIVO#, chama o Bruno com a base técnica
    try:
        base_do_setor = BASES_POR_SETOR.get(agente_nome, {})
        prompt_auditor = PROMPT_AUDITOR_BRUNO.format(
            mensagem_cliente=mensagem_cliente,
            rascunho=resposta_rascunho,
            base_tecnica=json.dumps(base_do_setor)
        )

        model_auditor = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=prompt_auditor
        )
        auditor_raw = model_auditor.generate_content("Audite esta resposta.")
        analise_seguranca = extrair_texto_seguro(auditor_raw).strip().upper()
    except Exception as e:
        print(f"[Erro Gemini - Auditor] {e}")
        analise_seguranca = "APROVADO"  # Em erro, aprova para não travar

    # 4. Se Bruno bloquear, envia alerta e retorna mensagem do Dr. Caio
    if "BLOQUEADO" in analise_seguranca:
        alerta = (
            "🚨 *ALERTA DE ATENDIMENTO - CAIO CONTÁBIL IA*\n\n"
            f"• *Setor solicitado:* {agente_nome.upper()}\n"
            f"• *Dúvida do cliente:* \"{mensagem_cliente}\"\n\n"
            "⚠️ _O Bruno Auditor bloqueou a resposta por complexidade técnica. O Dr. Caio assumiu o chat._"
        )
        enviar_alerta_telegram(alerta)
        return MENSAGEM_DR_CAIO_CEO

    # Se Bruno aprovar mesmo com #CONTEUDO_INCONCLUSIVO#, retorna o rascunho
    return resposta_rascunho

# ============================================================
# PROCESSAMENTO CENTRAL
# ============================================================
def processar_requisicao():
    dados = request.get_json() or {}

    mensagem = dados.get("mensagem") or dados.get("message") or dados.get("text") or ""
    setor = dados.get("setor") or dados.get("department") or "sofia"

    if not mensagem:
        return jsonify({"resposta": "Olá! Sou seu assistente virtual da Caio Contábil. Como posso ajudar você hoje? 😊"})

    padrao_telefone = r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}-\d{4}|\d{4}-\d{4}|9\d{8}|\d{8})'
    telefones = re.findall(padrao_telefone, mensagem)

    if telefones:
        alerta_lead = (
            "✅ *NOVO CLIENTE CAPTURADO!*\n\n"
            f"• *WhatsApp localizado:* `{telefones}`\n"
            f"• *Mensagem final:* \"{mensagem}\"\n\n"
            "📞 _Um contador humano deve entrar em contato via (14) 99879-7126 imediatamente._"
        )
        enviar_alerta_telegram(alerta_lead)
        return jsonify({
            "resposta": "Perfeito! Já captei o seu número. Encaminhei os detalhes para a nossa equipe e em instantes um de nossos contadores especialistas vai te chamar. Obrigado! 🙏"
        })

    resposta_final = responder_cliente(setor, mensagem)
    return jsonify({"resposta": resposta_final})

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
