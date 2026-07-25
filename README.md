# 🤖 Chatbot Inteligente - Caio Contábil
## Guia de Configuração Completa (100% Gratuito)

---

## 📋 RESUMO DO QUE VOCÊ VAI FAZER

1. ✅ Criar um bot no Telegram (via @BotFather)
2. ✅ Criar uma API Key no Google AI Studio (Gemini)
3. ✅ Hospedar o backend no Vercel (gratuito)
4. ✅ Colar o widget no Calima Site ("Scripts de integração")
5. ✅ Adicionar o Telegram nas "Redes Sociais" do Calima Site
6. ✅ Testar e começar a atender! 🚀

---

## 1️⃣ CRIAR O BOT NO TELEGRAM

1. Abra o Telegram e procure por **`@BotFather`**
2. Envie o comando: `/newbot`
3. Dê um nome ao bot: `Atendimento Caio Contábil`
4. Dê um username (deve terminar em "bot"): `Ex: caiocontabil_bot`
5. **Copie o TOKEN** que o BotFather te enviar (vai usar no passo 3)

### Criar um grupo para notificações:
1. Crie um grupo no Telegram com os contadores
2. Adicione o bot que você criou no grupo
3. Envie uma mensagem no grupo
4. Acesse no navegador:
   ```
   https://api.telegram.org/botSEU_TOKEN_AQUI/getUpdates
   ```
5. Procure pelo `"chat":{"id":` — o número é seu **CHAT_ID** (copie com o sinal de menos, ex: `-123456789`)

---

## 2️⃣ OBTER API KEY DO GEMINI

1. Acesse: https://aistudio.google.com/app/apikey
2. Clique em **"Create API Key"**
3. Copie a chave (vai usar no passo 3)

> 💡 O Gemini 1.5 Flash é **gratuito** até 1.500 requisições por dia!

---

## 3️⃣ HOSPEDAR O BACKEND NO VERCEL

### 3.1 Criar conta no GitHub
- Se ainda não tiver, crie em: https://github.com

### 3.2 Criar o repositório
1. No GitHub, clique em **"New Repository"**
2. Nome: `chatbot-caio-contabil`
3. Deixe como **Público**
4. Clique **"Create repository"**

### 3.3 Estrutura de arquivos
Crie esta estrutura no repositório:

```
chatbot-caio-contabil/
├── api/
│   └── index.py          ← Cole o conteúdo do arquivo api_index.py
├── vercel.json           ← Cole o conteúdo do arquivo vercel.json
└── requirements.txt      ← Cole o conteúdo do arquivo requirements.txt
```

> 💡 Você pode fazer upload dos arquivos diretamente pela interface web do GitHub!

### 3.4 Fazer deploy no Vercel
1. Acesse: https://vercel.com
2. Clique em **"Add New Project"**
3. Importe o repositório `chatbot-caio-contabil`
4. Em **"Environment Variables"**, adicione:

   | Nome | Valor |
   |------|-------|
   | `GEMINI_API_KEY` | Sua chave do Gemini |
   | `TELEGRAM_BOT_TOKEN` | Token do BotFather |
   | `TELEGRAM_CHAT_ID` | ID do grupo (ex: `-123456789`) |

5. Clique em **"Deploy"**
6. Anote a URL gerada (ex: `https://chatbot-caio-contabil.vercel.app`)

---

## 4️⃣ CONFIGURAR O WIDGET NO CALIMA SITE

### 4.1 Na seção "Scripts de integração"
1. No Calima Pro, vá em: **Site → Scripts de integração**
2. Cole o conteúdo do arquivo **`widget_chat.html`**
3. **IMPORTANTE:** Edite a linha do `API_URL`:
   ```javascript
   API_URL: 'https://SEU-PROJETO.vercel.app/chat',
   ```
   Substitua `SEU-PROJETO` pela URL que o Vercel gerou.
4. Salve

### 4.2 Na seção "Redes Sociais"
1. Vá em: **Site → Conteúdo → Redes Sociais**
2. Clique no **+** para adicionar nova rede
3. Configure:
   - **Ícone:** Telegram (ou use um link de imagem do ícone do Telegram)
   - **Nome:** Telegram
   - **Link:** `https://t.me/caiocontabil_bot` (substitua pelo username do seu bot)
4. Salve

---

## 5️⃣ TESTAR

1. Acesse seu site pelo botão **"Ver site"** no Calima
2. O widget 💬 deve aparecer no canto inferior direito
3. Clique e envie uma mensagem de teste
4. Verifique se:
   - ✅ O bot responde corretamente
   - ✅ A notificação chega no grupo do Telegram
   - ✅ O link do Telegram nas Redes Sociais funciona

---

## 🔧 PERSONALIZAÇÕES

### Mudar as cores do widget
No arquivo `widget_chat.html`, edite as variáveis CSS no topo:
```css
:root {
  --cor-primaria: #6366f1;      /* Roxo padrão */
  --cor-primaria: #0088cc;      /* Azul Telegram */
  --cor-primaria: #25d366;      /* Verde WhatsApp */
  --cor-primaria: #e11d48;      /* Vermelho */
}
```

### Mudar o nome da assistente
Edite a variável `EMPRESA` no JavaScript e o `SYSTEM_PROMPT` no backend.

### Adicionar mais perguntas no prompt
Edite o `SYSTEM_PROMPT` no arquivo `api/index.py` com as instruções do seu agente Gemini.

---

## 💰 CUSTOS

| Serviço | Custo |
|---------|-------|
| Telegram Bot API | **Grátis** |
| Gemini 1.5 Flash | **Grátis** (até 1.500 req/dia) |
| Vercel (Hobby) | **Grátis** |
| Calima Site | **Já pago** |
| **TOTAL** | **R$ 0,00** 🎉 |

---

## 🆘 SUPORTE E AJUDA

Se encontrar problemas:
1. Verifique se as variáveis de ambiente estão corretas no Vercel
2. Teste a API do Gemini diretamente: https://aistudio.google.com/app/apikey
3. Teste o bot do Telegram: envie `/start` para ele
4. Verifique os logs no painel do Vercel (aba "Deployments → Logs")

---

**Desenvolvido com 💙 para Caio Contábil LTDA**
