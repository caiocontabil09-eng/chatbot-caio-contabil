import os
import json
import google.generativeai as genai

# 1. Configuração da API Key do Gemini (Deve estar nas variáveis de ambiente da Vercel)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# 2. Carregar a Base de Dados Técnica atualizada pelo Radar AI
def carregar_base_radar():
    try:
        with open('dados_radar.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"erro": "Base de dados indisponível"}

base_conhecimento = carregar_base_radar()

# 3. Definição dos Prompts de Sistema dos Agentes de Atendimento
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

PROMPT_AUDITOR_BRUNO = """Você é Bruno, o Auditor Técnico de riscos da Caio Contábil. Você analisa o rascunho de resposta gerado pelos especialistas de atendimento.
Se a resposta gerada contiver o termo '#CONTEUDO_INCONCLUSIVO#', contiver erros fiscais claros ou for complexa demais para um cliente simples, você deve responder estritamente com a palavra: 'BLOQUEADO'.
Caso a resposta esteja correta, segura e perfeitamente simples para o cliente ler, responda estritamente com a palavra: 'APROVADO'."""

MENSAGEM_DR_CAIO_CEO = (
    "Olá, aqui é o Dr. Caio, CEO da Caio Contábil. Analisei o seu caso junto aos meus assistentes "
    "virtuais e, por se tratar de um ponto altamente complexo ou ainda inconclusivo na lei atual do governo, "
    "faço questão que um de nossos contadores seniores do time físico te atenda pessoalmente. "
    "Qual o seu melhor WhatsApp ou telefone com DDD para entrarmos em contato agora?"
)

def responder_cliente(setor_escolhido, mensagem_cliente):
    """
    Função principal que gerencia o fluxo de dupla checagem dos agentes.
    """
    # Se o chatbot mandar um setor inválido, cai no padrão da Sofia
    agente_nome = setor_escolhido.lower() if setor_escolhido.lower() in PROMPTS_AGENTES else "sofia"
    prompt_sistema_atendimento = PROMPTS_AGENTES[agente_nome]
    
    # 1. Agente de Atendimento cria o rascunho da resposta
    model_atendimento = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=prompt_sistema_atendimento
    )
    resposta_rascunho = model_atendimento.generate_content(mensagem_cliente).text
    
    # 2. Bruno (Auditor) faz a revisão secreta nos bastidores
    model_auditor = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=PROMPT_AUDITOR_BRUNO
    )
    analise_seguranca = model_auditor.generate_content(f"Mensagem do Cliente: {mensagem_cliente}\nRascunho do Atendente: {resposta_rascunho}").text.strip()
    
    # 3. Validação final do fluxo cooperativo
    if "BLOQUEADO" in analise_seguranca or "#CONTEUDO_INCONCLUSIVO#" in resposta_rascunho:
        # Aciona o protocolo de transição humana controlado pelo Dr. Caio (CEO)
        return MENSAGEM_DR_CAIO_CEO
    else:
        # Resposta aprovada pelo controle de qualidade técnico
        return resposta_rascunho

# Exemplo de teste de execução interna do fluxo (Pode ser integrado ao seu handler HTTP da Vercel)
if __name__ == "__main__":
    # Teste simulando o chatbot direcionando para a Sofia sobre a Alíquota Inconclusiva
    resultado_teste = responder_cliente("sofia", "Qual vai ser a aliquota final exata do imposto em SP?")
    print("RESPOSTA DO SISTEMA:")
    print(resultado_teste)
