import os
import json
import re
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Libera acesso de qualquer origem (seu widget pode falar com o servidor)

# Configurações de API nas Variáveis de Ambiente
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def enviar_alerta_telegram(mensagem_texto):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensagem_texto,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"[Telegram] Falha ao enviar alerta: {e}")

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
    "inconclusivo na lei, nossa equipe seniores vai te atender pessoamente. Por favor, informe seu WhatsApp com DDD "
    "ou, se preferir, nos chame direto no nosso telefone oficial: (14) 99879-7126."
)

def extrair_texto_seguro(resposta):
    if not resposta or not resposta.candidates:
        return ""
    try:
        return resposta.text
    except Exception:
        try:
            return "".join(part.text for part in resposta.candidates[0].content.parts)
        except Exception:
            return ""

def responder_cliente(setor_escolhido, mensagem_cliente):
    agente_nome = setor_escolhido.lower() if setor_escolhido.lower() in PROMPTS_AGENTES else "sofia"
    
    model_atendimento = genai.GenerativeModel(
        model_name="gemini-1.5-flash", 
        system_instruction=PROMPTS_AGENTES[agente_nome]
    )
    resposta_raw = model_atendimento.generate_content(mensagem_cliente)
    resposta_rascunho = extrair_texto_seguro(resposta_raw)
    
    model_auditor = genai.GenerativeModel(
        model_name="gemini-1.5-flash", 
        system_instruction=PROMPT_AUDITOR_BRUNO
    )
    auditor_raw = model_auditor.generate_content(f"Mensagem: {mensagem_cliente}\nRascunho: {resposta_rascunho}")
    analise_seguranca = extrair_texto_seguro(auditor_raw).strip()
    
    if "BLOQUEADO" in analise_seguranca or "#CONTEUDO_INCONCLUSIVO#" in resposta_rascunho:
        alerta = (
            "🚨 *ALERTA DE ATENDIMENTO - CAIO CONTÁBIL IA*\n\n"
            f"• *Setor solicitado:* {agente_nome.upper()}\n"
            f"• *Dúvida do cliente:* \"{mensagem_cliente}\"\n\n"
            "⚠️ _O Bruno Auditor bloqueou a resposta por complexidade técnica. O Dr. Caio assumiu o chat e pediu o contato._"
        )
        enviar_alerta_telegram(alerta)
        return MENSAGEM_DR_CAIO_CEO
        
    return resposta_rascunho

@app.route("/", methods=["GET", "POST", "OPTIONS"])
def home_atendimento():
    if request.method == "GET":
        return jsonify({ "status": "Servidor Caio Contábil IA Ativo e Operacional" })
        
    dados = request.get_json() or {}
    
    mensagem = dados.get("mensagem") or dados.get("message") or dados.get("text") or ""
    setor = dados.get("setor") or dados.get("department") or "sofia"
    
    if not mensagem:
        return jsonify({ "resposta": "Olá! Como posso ajudar você hoje?" })
    
    # Varredura para identificar se o cliente forneceu um telefone/WhatsApp
    padrao_telefone = r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}-\d{4}|\d{4}-\d{4}|9\d{8}|\d{8})'
    telefones = re.findall(padrao_telefone, mensagem)
    
    if telefones:
        alerta_lead = (
            "✅ *NOVO CLIENTE CAPTURADO!*\n\n"
            f"• *WhatsApp localizado:* `{telefones}`\n"
            f"• *Mensagem final:* \"{mensagem}\"\n\n"
            "📞 _Por favor, um contador humano deve entrar em contato via (14) 99879-7126 imediatamente._"
        )
        enviar_alerta_telegram(alerta_lead)
        return jsonify({
            "resposta": "Perfeito! Já captei o seu número. Encaminhei os detalhes para a nossa equipe e em instantes um de nossos contadores especialistas vai te chamar. Obrigado!"
        })

    resposta_final = responder_cliente(setor, mensagem)
    return jsonify({ "resposta": resposta_final })

@app.route("/<path:path>", methods=["GET", "POST", "OPTIONS"])
def catch_all(path):
    return home_atendimento()

if __name__ == "__main__":
    app.run(debug=True)
