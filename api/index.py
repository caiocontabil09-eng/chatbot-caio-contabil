import os
import json
import re
import google.generativeai as genai
from flask import Flask, request, jsonify

# Inicializa o Flask para a Vercel ler como API
app = Flask(__name__)

# Configuração da API Key do Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def carregar_base_radar():
    try:
        with open('dados_radar.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"status_reforma_tributaria": {"pontos_conclusivos": {}, "pontos_inconclusivos": {}}}

base_conhecimento = carregar_base_radar()

# Prompts dos Especialistas
PROMPTS_AGENTES = {
    "sofia": f"""Você é Sofia, especialista em comunicação e Reforma Tributária na Caio Contábil. Use linguagem simples, evite termos técnicos. BASE TÉCNICA: {json.dumps(base_conhecimento.get('status_reforma_tributaria', {}))}. Se fugir da base técnica, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    "mateus": f"""Você é Mateus, especialista fiscal da Caio Contábil. Ajuda com notas fiscais, impostos (ICMS, ISS, Simples). BASE TÉCNICA: {json.dumps(base_conhecimento)}. Se fugir da base, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    "clara": f"""Você é Clara, especialista em Departamento Pessoal e RH da Caio Contábil. Resolve dúvidas de CLT e eSocial. BASE TÉCNICA: {json.dumps(base_conhecimento.get('diretrizes_trabalhistas_rh', {}))}. Se fugir da base, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    "lucas": f"""Você é Lucas, especialista contábil da Caio Contábil. Explica caixa e lucros de forma simples. BASE TÉCNICA: {json.dumps(base_conhecimento)}. Se fugir da base, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    "tiago": f"""Você é Tiago, especialista societário da Caio Contábil. Ajuda a abrir e fechar empresas. BASE TÉCNICA: {json.dumps(base_conhecimento)}. Se fugir da base, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'"""
}

PROMPT_AUDITOR_BRUNO = """Você é Bruno, o Auditor Técnico de riscos da Caio Contábil. Analise o rascunho de resposta. Se contiver '#CONTEUDO_INCONCLUSIVO#', erros ou for complexa, responda: 'BLOQUEADO'. Se estiver correta e simples, responda: 'APROVADO'."""

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
        return MENSAGEM_DR_CAIO_CEO
    return resposta_rascunho

# ROTA DE API PARA O WIDGET/CHATBOT SE CONECTAR
@app.route("/api/atendimento", methods=["POST"])
def api_atendimento():
    dados = request.get_json() or {}
    mensagem = dados.get("mensagem", "")
    setor = dados.get("setor", "sofia")
    
    # Executa a nossa engenharia de agentes cooperativos
    resposta_final = responder_cliente(setor, mensagem)
    return jsonify({ "resposta": resposta_final })

# Necessário para a Vercel mapear o servidor Flask
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    return jsonify({ "status": "Servidor Caio Contábil IA Ativo" })
