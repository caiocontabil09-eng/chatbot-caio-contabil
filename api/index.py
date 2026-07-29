import os
import json
import re
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================================================
# CONFIGURAÇÕES
# ============================================================
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
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
# PROMPTS DOS AGENTES
# ============================================================
PROMPTS_AGENTES = {
    "sofia": f"""Você é Sofia, especialista em comunicação e Reforma Tributária na Caio Contábil. Use linguagem simples e acessível. BASE TÉCNICA: {json.dumps(base_conhecimento.get('status_reforma_tributaria', {}))}. Se a pergunta fugir da base técnica fornecida, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",

    "mateus": f"""Você é Mateus, especialista fiscal da Caio Contábil. Seja técnico mas claro. BASE TÉCNICA: {json.dumps(base_conhecimento)}. Se a pergunta fugir da base técnica fornecida, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",

    "clara": f"""Você é Clara, especialista em Departamento Pessoal e RH na Caio Contábil. BASE TÉCNICA: {json.dumps(base_conhecimento.get('diretrizes_trabalhistas_rh', {}))}. Se a pergunta fugir da base técnica fornecida, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",

    "lucas": f"""Você é Lucas, especialista contábil na Caio Contábil. BASE TÉCNICA: {json.dumps(base_conhecimento)}. Se a pergunta fugir da base técnica fornecida, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",

    "tiago": f"""Você é Tiago, especialista societário na Caio Contábil. BASE TÉCNICA: {json.dumps(base_conhecimento)}. Se a pergunta fugir da base técnica fornecida, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'"""
}

PROMPT_AUDITOR_BRUNO = """Você é Bruno, o Auditor Técnico de riscos da Caio Contábil. Analise o rascunho da resposta. Se contiver '#CONTEUDO_INCONCLUSIVO#', responda apenas: 'BLOQUEADO'. Caso contrário, responda apenas: 'APROVADO'."""

MENSAGEM_DR_CAIO_CEO = (
    "Olá, aqui é o Dr. Caio, CEO da Caio Contábil. Por se tratar de um ponto altamente complexo ou ainda "
    "inconclusivo na legislação, nossa equipe sênior vai te atender pessoalmente. Por favor, informe seu WhatsApp com DDD "
    "ou, se preferir, nos chame direto no nosso telefone oficial: (14) 99879-7126."
)

# ============================================================
# UTILITÁRIOS
# ============================================================
def extrair_texto_seguro(resposta):
    """Extrai texto da resposta do Gemini sem crashar."""
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
# LÓGICA PRINCIPAL
# ============================================================
def responder_cliente(setor_escolhido, mensagem_cliente):
    agente_nome = setor_escolhido.lower() if setor_escolhido.lower() in PROMPTS_AGENTES else "sofia"

    try:
        model_atendimento = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=PROMPTS_AGENTES[agente_nome]
        )
        resposta_raw = model_atendimento.generate_content(mensagem_cliente)
        resposta_rascunho = extrair_texto_seguro(resposta_raw)
    except Exception as e:
        print(f"[Erro Gemini - Atendimento] {e}")
        resposta_rascunho = "#CONTEUDO_INCONCLUSIVO#"

    try:
        model_auditor = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=PROMPT_AUDITOR_BRUNO
        )
        auditor_raw = model_auditor.generate_content(
            f"Mensagem do cliente: {mensagem_cliente}\nRascunho da resposta: {resposta_rascunho}"
        )
        analise_seguranca = extrair_texto_seguro(auditor_raw).strip().upper()
    except Exception as e:
        print(f"[Erro Gemini - Auditor] {e}")
        analise_seguranca = "BLOQUEADO"

    if "BLOQUEADO" in analise_seguranca or "#CONTEUDO_INCONCLUSIVO#" in resposta_rascunho:
        alerta = (
            "🚨 *ALERTA DE ATENDIMENTO - CAIO CONTÁBIL IA*\n\n"
            f"• *Setor solicitado:* {agente_nome.upper()}\n"
            f"• *Dúvida do cliente:* \"{mensagem_cliente}\"\n\n"
            "⚠️ _O Bruno Auditor bloqueou a resposta por complexidade técnica. O Dr. Caio assumiu o chat._"
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
    setor = dados.get("setor") or dados.get("department") or "sofia"

    if not mensagem:
        return jsonify({"resposta": "Olá! Sou seu assistente virtual da Caio Contábil. Como posso ajudar você hoje? 😊"})

    # Detecta telefone/WhatsApp na mensagem
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
    return processar_requisicao()

@app.route("/chat", methods=["GET", "POST", "OPTIONS"])
def chat_atendimento():
    if request.method == "GET":
        return jsonify({"status": "Rota /chat ativa e operacional ✅"})
    return processar_requisicao()

@app.route("/<path:path>", methods=["GET", "POST", "OPTIONS"])
def catch_all(path):
    return home_atendimento()

# ============================================================
# EXECUÇÃO
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
