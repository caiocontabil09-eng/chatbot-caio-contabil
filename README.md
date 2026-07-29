# 🤖 Caio Contábil - Chatbot IA
Chatbot inteligente com múltiplos agentes especializados (Sofia, Mateus, Clara, Lucas, Tiago) e auditor técnico (Bruno), integrado com Gemini AI e alertas via Telegram.
📁 Arquivos
Planilhas
Arquivo	Descrição
app.py	Backend Flask (servidor)
widget.html	Widget de chat para colar no site
requirements.txt	Dependências Python
dados_radar.json	Base de conhecimento dos agentes
🚀 Deploy no Vercel
1. Crie um novo projeto no Vercel
Acesse vercel.com
Clique em "Add New..." → "Project"
Importe seu repositório do GitHub
2. Configure as variáveis de ambiente
No painel do Vercel, vá em Settings → Environment Variables e adicione:
Planilhas
Variável	Valor
GEMINI_API_KEY	Sua chave da API Gemini
TELEGRAM_TOKEN	Token do bot do Telegram
TELEGRAM_CHAT_ID	ID do chat onde receberá alertas
3. Crie o arquivo vercel.json
Na raiz do projeto, crie um arquivo vercel.json com:
JSON
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ]
}
4. Deploy
Faça commit e push para o GitHub
O Vercel faz o deploy automaticamente
🌐 Instalar o Widget no Site
Opção 1: iFrame (mais fácil)
Cole isso no HTML do seu site:
HTML
<iframe 
    src="URL_DO_WIDGET.html" 
    style="position:fixed;bottom:0;right:0;width:400px;height:600px;border:none;z-index:9999;"
    allow="microphone">
</iframe>
Opção 2: Código direto (recomendado)
Abra o arquivo widget.html
Copie TODO o conteúdo (HTML + CSS + JS)
Cole no final do <body> do seu site, antes de </body>
Altere a URL do servidor na linha:
JavaScript
const API_URL = 'https://SEU-SERVIDOR.vercel.app/chat';
🧪 Testar Localmente
bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente (Linux/Mac)
export GEMINI_API_KEY="sua_chave"
export TELEGRAM_TOKEN="seu_token"
export TELEGRAM_CHAT_ID="seu_chat_id"

# Rodar servidor
python app.py
Acesse: http://localhost:5000
📝 Como obter as chaves
Gemini API Key
Acesse aistudio.google.com/app/apikey
Clique em "Create API Key"
Copie a chave
Telegram Bot Token
No Telegram, procure por @BotFather
Envie /newbot e siga as instruções
Copie o token fornecido
Telegram Chat ID
Adicione o bot em um grupo ou converse com ele no privado
Acesse: https://api.telegram.org/bot<SEU_TOKEN>/getUpdates
Procure por "chat":{"id":12345678 — esse número é o Chat ID
⚡ Agentes Disponíveis
Planilhas
Agente	Especialidade
Sofia	Comunicação e Reforma Tributária
Mateus	Fiscal
Clara	Departamento Pessoal / RH
Lucas	Contábil
Tiago	Societário
Bruno	Auditor Técnico (verificação automática)
Desenvolvido com 💜 para Caio Contábil
