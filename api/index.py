import os
import json
import re
import google.generativeai as genai

# =====================================================================
# 1. CONFIGURAÇÃO DA API KEY DO GEMINI
# =====================================================================
# Certifique-se de cadastrar a variável GEMINI_API_KEY no painel da Vercel
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# =====================================================================
# 2. CARREGAMENTO DA BASE DE DADOS DO RADAR AI
# =====================================================================
def carregar_base_radar():
    """
    Carrega o arquivo dados_radar.json criado pelo Agente Radar AI.
    """
    try:
        with open('dados_radar.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # Fallback de segurança caso o arquivo não seja encontrado
        return {
            "status_reforma_tributaria": {
                "pontos_conclusivos": {},
                "pontos_inconclusivos": {}
            }
        }

base_conhecimento = carregar_base_radar()

# =====================================================================
# 3. PROMPTS DE SISTEMA DOS AGENTES DE ATENDIMENTO (LINHA DE FRENTE)
# =====================================================================
PROMPTS_AGENTES = {
    "sofia": f"""Você é Sofia, especialista em comunicação e Reforma Tributária na Caio Contábil. 
    Seu foco são MEIs e pequenas empresas assustadas com as leis. Use linguagem simples, evite termos técnicos.
    BASE TÉCNICA ATUAL DO RADAR AI: {json.dumps(base_conhecimento.get('status_reforma_tributaria', {}))}
    Se o cliente perguntar algo sobre pontos inconclusivos ou que não estão na base técnica acima, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    
    "mateus": f"""Você é Mateus, especialista fiscal da Caio Contábil. Ajuda com notas fiscais, impostos (ICMS, ISS, Simples Nacional).
    BASE TÉCNICA ATUAL DO RADAR AI: {json.dumps(base_conhecimento)}
    Se a dúvida envolver multas graves ou algo fora da base técnica, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    
    "clara": f"""Você é Clara, especialista em Departamento Pessoal e RH da Caio Contábil. Resolve dúvidas de CLT, férias e eSocial.
    BASE TÉCNICA ATUAL DO RADAR AI: {json.dumps(base_conhecimento.get('diretrizes_trabalhistas_rh', {}))}
    Se a dúvida fugir do padrão simples ou exigir cálculos complexos, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    
    "lucas": f"""Você é Lucas, especialista contábil da Caio Contábil. Explica caixa, lucros e balancetes como se falasse com um comerciante simples.
    BASE TÉCNICA ATUAL DO RADAR AI: {json.dumps(base_conhecimento)}
    Se o cliente exigir laudos, perícias ou dados complexos, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'""",
    
    "tiago": f"""Você é Tiago, especialista societário da Caio Contábil. Ajuda a abrir, alterar ou fechar empresas de forma rápida.
    BASE TÉCNICA ATUAL DO RADAR AI: {json.dumps(base_conhecimento)}
    Para regras complexas de holdings ou fusões, responda estritamente: '#CONTEUDO_INCONCLUSIVO#'"""
}

# =====================================================================
# 4. PROMPTS DO BACKOFFICE (AUDITORIA E CEO)
# =====================================================================
PROMPT_AUDITOR_BRUNO = """Você é Bruno, o Auditor Técnico de riscos da Caio Contábil. Você analisa o rascunho de resposta gerado pelos especialistas de atendimento.
Se a resposta gerada contiver o termo '#CONTEUDO_INCONCLUSIVO#', contiver erros fiscais claros ou for complexa demais para um cliente simples, você deve responder estritamente com a palavra: 'BLOQUEADO'.
Caso a resposta esteja correta, segura e perfeitamente simples para o cliente ler, responda estritamente com a palavra: 'APROVADO'."""

MENSAGEM_DR_CAIO_CEO = (
    "Olá, aqui é o Dr. Caio, CEO da Caio Contábil. Analisei o seu caso junto aos meus assistentes "
    "virtuais e, por se tratar de um ponto altamente complexo ou ainda inconclusivo na lei atual do governo, "
    "faço questão que um de nossos contadores seniores do time físico te atenda pessoalmente. "
    "Qual o seu melhor WhatsApp ou telefone com DDD para entrarmos em contato agora?"
)

# =====================================================================
# 5. ENGENHARIA DE ROTEAMENTO E CONTROLE DE QUALIDADE
# =====================================================================
def responder_cliente(setor_escolhido, mensagem_cliente):
    """
    Gerencia o fluxo de dupla checagem dos agentes antes de exibir ao cliente.
    """
    agente_nome = setor_escolhido.lower() if setor_escolhido.lower() in PROMPTS_AGENTES else "sofia"
    prompt_sistema_atendimento = PROMPTS_AGENTES[agente_nome]
    
    # 1. Agente especialista cria o rascunho da resposta
    model_atendimento = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=prompt_sistema_atendimento
    )
    resposta_rascunho = model_atendimento.generate_content(mensagem_cliente).text
    
    # 2. Bruno (Auditor) faz a revisão secreta em segundo plano
    model_auditor = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=PROMPT_AUDITOR_BRUNO
    )
    analise_seguranca = model_auditor.generate_content(
        f"Mensagem do Cliente: {mensagem_cliente}\nRascunho do Atendente: {resposta_rascunho}"
    ).text.strip()
    
    # 3. Decisão do fluxo de segurança cooperativo
    if "BLOQUEADO" in analise_seguranca or "#CONTEUDO_INCONCLUSIVO#" in resposta_rascunho:
        return MENSAGEM_DR_CAIO_CEO
    else:
        return resposta_rascunho

# =====================================================================
# 6. ENGENHARIA DE CAPTURA DE LEADS (MENSAGEM DO WHATSAPP)
# =====================================================================
def extrair_contato_e_salvar(mensagem_cliente):
    """
    Analisa se a resposta do cliente após falar com o Dr. Caio contém 
    um número de WhatsApp válido e prepara os dados para o envio técnico.
    """
    # Expressão regular ajustada para capturar números de telefone brasileiros
    padrao_telefone = r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}-\d{4}|\d{4}-\d{4}|9\d{8}|\d{8})'
    telefones_encontrados = re.findall(padrao_telefone, mensagem_cliente)
    
    if telefones_encontrados:
        whatsapp_capturado = telefones_encontrados[0]
        
        # Estrutura JSON gerada para enviar para sua equipe de contadores reais
        dados_lead = {
            "status": "LEAD_QUALIFICADO_REFORMA",
            "whatsapp": whatsapp_capturado,
            "mensagem_original": mensagem_cliente,
            "alerta": "Caso inconclusivo ou complexo interceptado pelo Bruno Auditor. Repassar para um humano."
        }
        
        # Mensagem de encerramento amigável para o cliente final
        texto_sucesso = (
            "Perfeito! Já peguei o seu contato técnico. Encaminhei os detalhes para a nossa "
            "equipe física e, em alguns minutos, um de nossos contadores especialistas vai "
            "te chamar aqui no WhatsApp para analisar seu caso de perto. Muito obrigado!"
        )
        
        return {
            "sucesso": True,
            "dados_lead": dados_lead,
            "resposta_chat": texto_sucesso
        }
    
    # Caso o cliente digite texto mas esqueça de colocar o número de telefone
    texto_falha = (
        "Por favor, envie o seu número de WhatsApp com o DDD (exemplo: 11 99999-9999) "
        "para que eu possa pedir para o nosso time de contadores entrar em contato com você."
    )
    return {
        "sucesso": False,
        "dados_lead": None,
        "resposta_chat": texto_falha
    }

# =====================================================================
# 7. EXECUÇÃO DE TESTE LOCAL
# =====================================================================
if __name__ == "__main__":
    print("--- Testando fluxo seguro com pergunta complexa ---")
    teste_bloqueio = responder_cliente("sofia", "A nova alíquota em SP vai ser exatamente quanto?")
    print(teste_bloqueio)
    
    print("\n--- Testando captura automática de número de contato ---")
    teste_lead = extrair_contato_e_salvar("Meu whatsapp é (11) 98888-7777 pode me chamar")
    print(teste_lead["resposta_chat"])
