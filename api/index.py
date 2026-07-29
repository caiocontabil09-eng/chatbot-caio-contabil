import os
import json
import re
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configurações de API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def enviar_alerta_telegram(mensagem_texto):
    """
    Função que dispara um alerta em tempo real para o Grupo de Contadores no Telegram.
    """
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensagem_texto,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception:
            pass

def carregar_base_radar():
    try:
        with open('dados_radar.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"status_reforma_tributaria": {"pontos_conclusivos": {}, "pontos_inconclusivos": {}}}

base_conhecimento = carregar_base_radar()

PROMPTS_AGENTES = {
    "sofia": f"""Você é Sofia, especialista em comunicação e Reforma Tributária na Caio Contábil. Use linguagem simples. BASE TÉCNICA: {json.dumps(base_conhecimento.get('status_reforma_tributaria', {}))}. Se fugir da base, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    "mateus": f"""Você é Mateus, especialista fiscal da Caio Contábil. BASE TÉCNICA: {json.dumps(base_conhecimento)}. Se fugir da base, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    "clara": f"""Você é Clara, especialista em Departamento Pessoal e RH. BASE TÉCNICA: {json.dumps(base_conhecimento.get('diretrizes_trabalhistas_rh', {}))}. Se fugir da base, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    "lucas": f"""Você é Lucas, especialista contábil. BASE TÉCNICA: {json.dumps(base_conhecimento)}. Se fugir da base, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    "tiago": f"""Você é Tiago, especialista societário. BASE TÉCNICA: {json.dumps(base_conhecimento)}. Se fugir da base, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'"""
}

PROMPT_AUDITOR_BRUNO = """Você é Bruno, o Auditor Técnico de riscos da Caio Contábil. Analise o rascunho. Se contiver '#CONTEUDO_INCONCLUSIVO#', responda: 'BLOQUEADO'. Caso contrário, responda: 'APROVADO'."""

MENSAGEM_DR_CAIO_CEO = (
    "Olá, aqui é o Dr. Caio, CEO da Caio Contábil. Por se tratar de um ponto altamente complexo ou ainda "
    "inconclusivo na lei, nossa equipe seniores vai te atender pessoalmente. Por favor, informe seu WhatsApp com DDD "
    "ou, se preferir, nos chame direto no nosso telefone oficial: (14) 99879-7126."
)

def responder_cliente(setor_escolhido, mensagem_cliente):
    agente_nome = setor_escolhido.lower() if setor_escolhido.lower() in PROMPTS_AGENTES else "sofia"
    model_atendimento = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=PROMPTS_AGENTES[agente_nome])
    resposta_rascunho = model_atendimento.generate_content(mensagem_cliente).text
    
    model_auditor = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=PROMPT_AUDITOR_BRUNO)
    analise_seguranca = model_auditor.generate_content(f"Mensagem: {mensagem_cliente}\nRascunho: {resposta_rascunho}").text.strip()
    
    if "BLOQUEADO" in analise_seguranca or "#CONTEUDO_INCONCLUSIVO#" in resposta_rascunho:
        # Alerta o grupo que um cliente caiu no filtro de segurança
        alerta = (
            "🚨 *ALERTA DE ATENDIMENTO - CAIO CONTÁBIL IA*\n\n"
            f"• *Setor solicitado:* {agente_nome.upper()}\n"
            f"• *Dúvida do cliente:* \"{mensagem_cliente}\"\n\n"
            "⚠️ _O Bruno Auditor bloqueou a resposta por complexidade técnica. O Dr. Caio assumiu o chat e pediu o contato._"
        )
        enviar_alerta_telegram(alerta)
        return MENSAGEM_DR_CAIO_CEO
        
    return resposta_rascunho

@app.route("/api/atendimento", methods=["POST"])
def api_atendimento():
    dados = request.get_json() or {}
    mensagem = dados.get("mensagem", "")
    setor = dados.get("setor", "sofia")
    
    # Verifica se a mensagem se parece com a entrega de um número de WhatsApp pós-bloqueio
    padrao_telefone = r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}-\d{4}|\d{4}-\d{4}|9\d{8}|\d{8})'
    telefones = re.findall(padrao_telefone, mensagem)
    
    if telefones:
        alerta_lead = (
            "✅ *NOVO CLIENTE CAPTURADO!*\n\n"
            f"• *WhatsApp localizado:* `{telefones[0]}`\n"
            f"• *Mensagem final:* \"{mensagem}\"\n\n"
            "📞 _Por favor, um contador humano deve entrar em contato via (14) 99879-7126 imediatamente._"
        )
        enviar_alerta_telegram(alerta_lead)
        return jsonify({
            "resposta": "Perfeito! Já captei o seu número. Encaminhei os detalhes para a nossa equipe e em instantes um de nossos contadores especialistas vai te chamar. Obrigado!"
        })

    resposta_final = responder_cliente(setor, mensagem)
    return jsonify({ "resposta": resposta_final })

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    return jsonify({ "status": "Servidor Caio Contábil IA Ativo" })
