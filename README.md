# 📌 AutoLink Pinterest (Shopee Affiliate ➔ Pinterest Automator)

Sistema completo e automatizado para transformar ofertas e produtos da **Shopee** em **Pins profissionais de alta conversão no Pinterest** com o seu **link de afiliado oficial encurtado**, utilizando **100% de ferramentas oficiais e gratuitas**.

---

## 🚀 Principais Funcionalidades

* **🛍️ Shopee Affiliate Open API (Oficial):**
  * Coleta em tempo real de produtos em oferta, mais vendidos (*Top Sales*) e maiores comissões via GraphQL com autenticação oficial SHA256.
  * Geração instantânea de links de afiliado rastreados (`s.shopee.com.br/...`).
  * Suporte adicional para colar qualquer link direto de produto Shopee na interface.
  * Filtro de validação por volume mínimo de vendas (prova social).

* **🔥 Inteligência de Mercado & Nichos Virais:**
  * Catálogo integrado com 7 nichos campeões de busca e conversão no Pinterest (*Casa & Organização, Cozinha Prática, Decoração & Estilo, Beleza & Skincare, Limpeza Inteligente, Jardim & Piscina, Achadinhos Virais*).
  * Seletores de ordenação oficial: **Mais Vendidos**, **Maior Desconto (% OFF)** e **Maior Comissão**.

* **🎨 Motor Gráfico 1000x1500 (Pillow - 100% Gratuito & Local):**
  * Gera artes verticais em formato 2:3 (1000x1500 px - padrão oficial do Pinterest).
  * Design de alta conversão com alinhamento óptico e geométrico milimétrico (`anchor="mm"`): fundo gradiente, card centralizado com sombra suave, selo de desconto chamativo (`-50% OFF`), preço De/Por e botão CTA.
  * Processamento local ultrarrápido, sem custos de APIs externas de imagem.

* **✍️ Copywriting com IA ou Templates Offline:**
  * **Modo IA Google Gemini:** Consulta dinâmica aos modelos ativos da conta (`gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`) com fallback automático em cascata contra indisponibilidade (503).
  * **Modo Gratuito Offline:** Templates de alta conversão com ganchos virais, benefícios, chamadas para ação e hashtags de SEO.

* **📁 Gerenciamento Automático de Pastas (Boards):**
  * **Modo Rotação Automática:** Alterna as postagens entre todas as pastas da sua conta ao longo do dia de forma balanceada.
  * **Modo Correspondência Inteligente:** Detecta o nicho do produto e envia direto para a pasta compatível.
  * **Modo Pasta Fixa:** Envia todos os pins para a pasta selecionada.

* **🛡️ Piloto Automático Anti-Spam & Deduplicação:**
  * Banco de dados local SQLite (`autolink.db`) para deduplicação contínua (nunca posta o mesmo produto duas vezes).
  * Agendamento humanizado com intervalo médio configurável e variação randômica (*jitter*).
  * Limite diário de segurança (ex: 5 a 15 pins/dia) para proteção da autoridade da conta no Pinterest.
  * **Bandeja do Sistema (System Tray):** Ao clicar em fechar (X), minimiza discretamente ao lado do relógio do Windows e continua rodando em segundo plano.

---

## 🛠️ Stack Tecnológico

* **Linguagem & GUI:** Python 3.12, PySide6 (Qt)
* **Design Gráfico:** Pillow (PIL)
* **Banco de Dados:** SQLite3 (nativo)
* **Integrações Oficiais:**
  * Shopee Open Platform GraphQL API
  * Pinterest Developer REST API v5
  * Google Gemini API (`google-genai`)

---

## ⚙️ Instalação e Configuração

### 1. Clonar o Repositório
```bash
git clone https://github.com/IsmaelPacheco/Auto-Link-Pinterest.git
cd Auto-Link-Pinterest
```

### 2. Criar e Ativar Ambiente Virtual
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar Credenciais
Copie o arquivo de exemplo para criar o seu arquivo de configurações:
```bash
copy config.example.json config.json
```
Abra o programa e preencha suas chaves na aba **⚙️ Configurações**:
* **Shopee:** App ID e Secret obtidos na [Shopee Open Platform / Afiliados](https://affiliate.shopee.com.br).
* **Pinterest:** Access Token obtido no [Pinterest Developers](https://developers.pinterest.com/).
* **Gemini (Opcional):** Chave gratuita obtida no [Google AI Studio](https://aistudio.google.com/).

---

## 🏃 Como Executar

Basta dar dois cliques no arquivo:
```
Executar para rodar.bat
```
Ou pelo terminal:
```bash
.venv\Scripts\python main.py
```

---

## 📄 Licença
Distribuído sob licença MIT. Veja `LICENSE` para mais detalhes.