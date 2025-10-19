# Projeto Agente de IA - Tutor para Desenvolvedores



![Interface do Agente de IA para Desenvolvedores. A tela é dividida em um cabeçalho com o título "Assistente para Devs", uma área principal exibindo uma resposta formatada em parágrafos, e um rodapé com um campo de texto para digitar uma pergunta e um botão de enviar.](https://i.postimg.cc/3wgZTBMs/Captura-de-Tela-78.png)



## 🚀 Sobre o Projeto

Este projeto é um agente de IA conversacional que atua como um tutor para desenvolvedores. A iniciativa surgiu como uma forma de aprofundar meus estudos na área de desenvolvimento web, aproveitando a base de backend da "Imersão Dev Agentes de IA com o Google", promovida pela Alura.

Meu foco principal e contribuição autoral neste projeto foi o desenvolvimento da interface e da experiência do usuário, **criando todo o visual da aplicação com HTML e CSS**. O objetivo foi construir uma interface limpa, amigável e responsiva, que tornasse a interação com a IA mais agradável e intuitiva. Para a integração final entre o backend em Python e o front-end, utilizei recursos de IA como ferramenta assistiva para acelerar o desenvolvimento.

## 🛠️ Tecnologias Utilizadas

A arquitetura do projeto utiliza a abordagem RAG (Retrieval-Augmented Generation).

*   **Front-end:**
    *   HTML5
    *   CSS3 (com Flexbox e Variáveis)
    *   JavaScript (Fetch API para comunicação com o backend)
*   **Back-end:**
    *   Python
    *   Flask
*   **Inteligência Artificial:**
    *   Google Gemini 2.5 Flash
    *   LangChain & LangGraph (para orquestração do fluxo)
    *   FAISS (para a busca vetorial da base de conhecimento)

## ⚙️ Como Executar

**Atenção:** Este projeto foi projetado como um template flexível. Para funcionar, ele precisa de uma base de conhecimento fornecida por você em formato PDF.

1.  **Clone este repositório:**
    `git clone [URL_DO_SEU_REPO]`

2.  **Crie a pasta da base de conhecimento:**
    Na raiz do projeto, crie uma pasta chamada `docs_web_junior`.

3.  **Adicione seus documentos:**
    Coloque os arquivos PDF que você deseja usar como base de conhecimento dentro da pasta `docs_web_junior`.

4.  **Crie e ative um ambiente virtual:**
    `python -m venv .venv`
    `.\.venv\Scripts\Activate.ps1`

5.  **Instale as dependências:**
    `pip install -r requirements.txt`

6.  **Configure sua API Key:**
    Crie um arquivo chamado `.env` na raiz do projeto e adicione sua chave da API do Google Gemini:
    `GOOGLE_API_KEY="SUA_CHAVE_AQUI"`

7.  **Crie o Índice de Conhecimento:**
    Execute o script para processar seus PDFs e criar o banco de dados vetorial:
    `python criar_indice.py`

8.  **Inicie o Servidor:**
    `python app.py`

O agente estará rodando em `http://127.0.0.1:5000`. Abra o arquivo `index.html` em seu navegador para começar a interagir!

## ✨ Autor

Desenvolvido por **Bruno Amaral de Sousa** como parte da minha jornada de aprendizado no desenvolvimento web.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/brunoamrls/)