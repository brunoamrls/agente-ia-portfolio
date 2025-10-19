# Importações necessárias
from flask import Flask, request, jsonify
from flask_cors import CORS # Para lidar com CORS
from typing import TypedDict, Optional, List, Dict, Literal

#LangChai e Google Imports
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_google_genai import HarmBlockThreshold, HarmCategory
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langgraph.graph import StateGraph, START, END
import re, pathlib
import traceback
from langchain_core.messages import SystemMessage, HumanMessage
# Importe userdata apenas se estiver rodando no Colab para carregar a chave
# from google.colab import userdata



import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Tenta pegar a API key do ambiente
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY não encontrada no arquivo .env")

print("API Key carregada do arquivo .env")


# Inicializa o modelo Gemini para chat e triagem
llm_triagem = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.0,
    api_key=GOOGLE_API_KEY
)

# Inicializa o modelo de embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=GOOGLE_API_KEY
)


# Definição do prompt para triagem de mensagens
TRIAGEM_PROMPT = (
    "Você é um consultor de tecnologias web para desenvolvedores iniciantes. "
    "Dada a pergunta do usuário, retorne SOMENTE um JSON com:\n"
    "{\n"
    '  "decisao": "AUTO_RESOLVER" | "PEDIR_INFO" | "ABRIR_CHAMADO",\n'
    '  "urgencia": "BAIXA" | "MEDIA" | "ALTA",\n'
    '  "campos_faltantes": ["..."]\n'
    "}\n"
    "Regras:\n"
    '- **AUTO_RESOLVER**: Perguntas claras sobre tecnologias, frameworks, ou escolhas de stack para projetos web simples.\n'
    '- **PEDIR_INFO**: Perguntas vagas sobre desenvolvimento sem contexto específico do projeto ou nível de experiência.\n'
    '- **ABRIR_CHAMADO**: Pedidos de mentoria personalizada, code review, ou ajuda com projetos específicos complexos.'
    "Analise a pergunta e decida a ação mais apropriada."
)

# Definição do modelo Pydantic para a saída da triagem
from pydantic import BaseModel, Field
class TriagemOut(BaseModel):
    decisao: Literal["AUTO_RESOLVER", "PEDIR_INFO", "ABRIR_CHAMADO"]
    urgencia: Literal["BAIXA", "MEDIA", "ALTA"]
    campos_faltantes: List[str] = Field(default_factory=list)

# Cria a cadeia de triagem com saída estruturada
triagem_chain = llm_triagem.with_structured_output(TriagemOut)

# Define a função de triagem
def triagem(mensagem: str) -> Dict:
    print(f"Triando mensagem: {mensagem}")
    saida: TriagemOut = triagem_chain.invoke([
        SystemMessage(content=TRIAGEM_PROMPT),
        HumanMessage(content=mensagem)
    ])
    return saida.model_dump()


# Carrega o vectorstore do disco em vez de recriá-lo
vectorstore = None
retriever = None
INDEX_PATH = "faiss_index" # Nome da pasta onde o índice será salvo/lido

if os.path.exists(INDEX_PATH):
    print(f"Carregando índice FAISS de '{INDEX_PATH}'...")
    # Nota: `allow_dangerous_deserialization=True` é necessário para carregar índices FAISS com pickle.
    # É seguro neste contexto pois você está carregando um arquivo que você mesmo criou.
    vectorstore = FAISS.load_local(
        INDEX_PATH, 
        embeddings, 
        allow_dangerous_deserialization=True 
    )
    retriever = vectorstore.as_retriever( search_type="similarity_score_threshold",
                                         search_kwargs={"score_threshold": 0.15, "k": 8}
)
    print("Vectorstore e Retriever carregados com sucesso.")
else:
    print(f"ERRO: Diretório do índice '{INDEX_PATH}' não encontrado.")
    print("Por favor, execute o script 'criar_indice.py' primeiro para gerar o índice.")
    # Se o índice for essencial para o funcionamento do app, você pode encerrar a execução:
    # import sys
    # sys.exit(1)


# Define o prompt para o RAG
prompt_rag = ChatPromptTemplate.from_messages([
        ("system",
         # 1. Definição da Persona
         "Você é um consultor de desenvolvimento web amigável e encorajador, especializado em ajudar iniciantes. "
         "Seu tom deve ser didático e paciente, como se estivesse explicando um conceito novo para um aluno pela primeira vez."

         # 2. Instruções de Conteúdo
         " Use o contexto fornecido para formular suas respostas. Se o contexto não tiver a definição exata, INTERPRETE as informações disponíveis"
         " para fornecer uma resposta útil. Sempre explique o 'porquê' das suas recomendações e evite dizer 'não encontrei' se houver informação relacionada."
         
         # 3. Regras de Formatação
         "\n\n**REGRAS DE FORMATAÇÃO DA RESPOSTA:**"
         "\n1. **Estrutura:** Separe os parágrafos com uma linha em branco (duas quebras de linha). A resposta deve ter entre 2 a 4 parágrafos curtos."
         "\n2. **Clareza:** Mantenha a resposta concisa e focada na pergunta do usuário."
         "\n3. **Estilo:** Use apenas texto puro. Não use Markdown (como asteriscos para negrito, hífens para listas, etc.)."
         "\n4. **Metalinguagem:** **Não mencione o 'contexto' ou a 'base de conhecimento' em sua resposta.** Fale de forma natural, como se o conhecimento fosse seu."
         ),

        ("human", "Pergunta sobre desenvolvimento web: {input}\n\nContexto técnico:\n{context}")
    ])

# Cria a cadeia de documentos para o RAG (apenas se llm_triagem e retriever existirem)
document_chain = None
if llm_triagem and retriever:
    document_chain = create_stuff_documents_chain(llm_triagem, prompt_rag)
    print("Cadeia de documentos RAG criada.")
else:
     print("Não foi possível criar a cadeia de documentos RAG (verifique llm_triagem e retriever).")


# Funções auxiliares para formatação de texto e citações
def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def extrair_trecho(texto: str, query: str, janela: int = 240) -> str:
    txt = _clean_text(texto)
    termos = [t.lower() for t in re.findall(r"\w+", query or "") if len(t) >= 4]
    pos = -1
    for t in termos:
        pos = txt.lower().find(t)
        if pos != -1: break
    if pos == -1: pos = 0
    ini, fim = max(0, pos - janela//2), min(len(txt), pos + janela//2)
    return txt[ini:fim]

def formatar_citacoes(docs_rel: List, query: str) -> List[Dict]:
    cites, seen = [], set()
    for d in docs_rel:
        src = pathlib.Path(d.metadata.get("source","")).name
        page = int(d.metadata.get("page", 0)) + 1
        key = (src, page)
        if key in seen:
            continue
        seen.add(key)
        cites.append({"documento": src, "pagina": page, "trecho": extrair_trecho(d.page_content, query)})
    return cites[:3]

# Função principal para responder perguntas usando RAG
def perguntar_stack_RAG(pergunta: str) -> Dict:
    print(f"Executando RAG para: {pergunta}")
    # Verifica se o retriever e a cadeia de documentos existem antes de usá-los
    if not retriever or not document_chain:
        print("RAG não configurado corretamente (retriever ou document_chain ausente).")
        return {"answer": "Não sei.",
                "citacoes": [],
                "contexto_encontrado": False}

    docs_relacionados = retriever.invoke(pergunta)

    if not docs_relacionados:
        print("Nenhum documento relevante encontrado pelo RAG.")
        return {"answer": "Não sei.",
                "citacoes": [],
                "contexto_encontrado": False}

    answer = document_chain.invoke({"input": pergunta,
                                    "context": docs_relacionados})

    txt = (answer or "").strip()

    if txt.rstrip(".!?") == "Não sei":
        print("RAG retornou 'Não sei'.")
        return {"answer": "Não sei.",
                "citacoes": [],
                "contexto_encontrado": False}

    print("RAG bem-sucedido.")
    return {"answer": txt,
            "citacoes": formatar_citacoes(docs_relacionados, pergunta), #Verificar aqui se é onde podemos limitar a apresentação das citações
            "contexto_encontrado": True}

# Definição do estado do agente no LangGraph
class AgentState(TypedDict, total = False):
    pergunta: str
    triagem: dict
    resposta: Optional[str]
    citacoes: List[dict]
    rag_sucesso: bool
    acao_final: str

# Nó do grafo para executar a triagem
def node_triagem(state: AgentState) -> AgentState:
    print("Executando nó de triagem...")
    # Verifica se a função de triagem está disponível
    if 'triagem' not in globals():
        print("Erro: Função 'triagem' não definida.")
        return {"acao_final": "ERRO", "resposta": "Erro interno: Função de triagem não encontrada."}
    try:
        return {"triagem": triagem(state["pergunta"])}
    except Exception as e:
        print(f"Erro na triagem: {e}")
        return {"acao_final": "ERRO", "resposta": f"Ocorreu um erro durante a triagem: {e}"}


# Nó do grafo para auto-resolver perguntas usando RAG
def node_auto_resolver(state: AgentState) -> AgentState:
    print("Executando nó de auto_resolver...")
    if 'perguntar_stack_RAG' not in globals():
         print("Erro: Função 'perguntar_stack_RAG' não definida.")
         return {"acao_final": "ERRO", "resposta": "Erro interno: Função RAG não encontrada."}
    try:
        resposta_rag = perguntar_stack_RAG(state["pergunta"])

        update: AgentState = {
            "resposta": resposta_rag["answer"],
            "citacoes": resposta_rag.get("citacoes", []),
            "rag_sucesso": resposta_rag["contexto_encontrado"],
        }

        if resposta_rag["contexto_encontrado"]:
            update["acao_final"] = "AUTO_RESOLVER"

        return update
    except Exception as e:
        print(f"====== ERRO DETALHADO NO AUTO_RESOLVER ======")
        traceback.print_exc()  # <-- O novo log de erro detalhado
        print(f"==============================================")
        return {"acao_final": "ERRO", "resposta": f"Ocorreu um erro durante o auto-resolver: {e}"}


# Nó do grafo para solicitar informações adicionais
def node_pedir_info(state: AgentState) -> AgentState:
    print("Executando nó de pedir_info...")
    # Verifica se 'triagem' está no estado antes de acessar
    if 'triagem' not in state or not state['triagem']:
         print("Erro: Estado da triagem ausente.")
         return {"acao_final": "ERRO", "resposta": "Erro interno: Resultado da triagem não disponível."}

    faltantes = state["triagem"].get("campos_faltantes", [])
    if faltantes:
        detalhe = ",".join(faltantes)
    else:
        detalhe = "Tema e contexto específico"

    return {
        "resposta": f"Para avançar, preciso que detalhe: {detalhe}",
        "citacoes": [],
        "acao_final": "PEDIR_INFO"
    }

# Nó do grafo para abrir um chamado
def node_abrir_chamado(state: AgentState) -> AgentState:
    print("Executando nó de abrir_chamado...")
    # Verifica se 'triagem' está no estado antes de acessar
    if 'triagem' not in state or not state['triagem']:
         print("Erro: Estado da triagem ausente.")
         return {"acao_final": "ERRO", "resposta": "Erro interno: Resultado da triagem não disponível."}

    triagem = state["triagem"]

    return {
        "resposta": f"Abrindo chamado com urgência {triagem['urgencia']}. Descrição: {state.get('pergunta', '')[:140]}",
        "citacoes": [],
        "acao_final": "ABRIR_CHAMADO"
    }

# Função para decidir o próximo passo após a triagem
KEYWORDS_ABRIR_TICKET = ["aprovação", "exceção", "liberação", "abrir ticket", "abrir chamado", "acesso especial"]

def decidir_pos_triagem(state: AgentState) -> str:
    print("Decidindo após a triagem...")
     # Verifica se 'triagem' está no estado antes de acessar
    if 'triagem' not in state or not state['triagem']:
         print("Erro: Estado da triagem ausente para decisão.")
         return "ERRO" # Retorna um estado de erro ou padrão
    decisao = state["triagem"]["decisao"]

    if decisao == "AUTO_RESOLVER": return "auto"
    if decisao == "PEDIR_INFO": return "info"
    if decisao == "ABRIR_CHAMADO": return "chamado"
    return "ERRO" # Caso a decisão da triagem seja inesperada

# Função para decidir o próximo passo após o auto-resolver
def decidir_pos_auto_resolver(state: AgentState) -> str:
    print("Decidindo após o auto_resolver...")

    if state.get("rag_sucesso"):
        print("Rag com sucesso, finalizando o fluxo.")
        return "ok"

    state_da_pergunta = (state.get("pergunta", "") or "").lower()

    if any(k in state_da_pergunta for k in KEYWORDS_ABRIR_TICKET):
        print("Rag falhou, mas foram encontradas keywords de abertura de ticket. Abrindo...")
        return "chamado"

    print("Rag falhou, sem keywords, vou pedir mais informações...")
    return "info"

# Definição do grafo de estado usando LangGraph
workflow = StateGraph(AgentState)

workflow.add_node("triagem", node_triagem)
workflow.add_node("auto_resolver", node_auto_resolver)
workflow.add_node("pedir_info", node_pedir_info)
workflow.add_node("abrir_chamado", node_abrir_chamado)

workflow.add_edge(START, "triagem")

workflow.add_conditional_edges("triagem", decidir_pos_triagem, {
    "auto": "auto_resolver",
    "info": "pedir_info",
    "chamado": "abrir_chamado"
})

workflow.add_conditional_edges("auto_resolver", decidir_pos_auto_resolver, {
    "info": "pedir_info",
    "chamado": "abrir_chamado",
    "ok": END
})

workflow.add_edge("pedir_info", END)
workflow.add_edge("abrir_chamado", END)

grafo = workflow.compile()
print("Grafo do agente compilado.")


# --- Configuração do Flask ---
app = Flask(__name__)
CORS(app) # Aplica a configuração de CORS

# Define a rota '/perguntar'
@app.route('/perguntar', methods=['POST'])
def handle_pergunta():
    print("Requisição POST recebida em /perguntar")
    data = request.get_json()
    pergunta = data.get('pergunta')

    if not pergunta:
        print("Erro: Pergunta não fornecida.")
        return jsonify({"error": "Pergunta não fornecida"}), 400

    print(f"Processando pergunta: {pergunta}")
    try:
        # Invoca o grafo (agente) com a pergunta recebida
        resposta_final = grafo.invoke({"pergunta": pergunta})
        print(f"Resposta final do grafo: {resposta_final}")
        # Retorna a resposta do agente como um JSON
        return jsonify(resposta_final)
    except Exception as e:
        print(f"Erro ao invocar o grafo: {e}")
        return jsonify({"error": f"Erro interno ao processar a pergunta: {e}"}), 500


if __name__ == '__main__':
    print("Iniciando servidor Flask em http://127.0.0.1:5000/")
    app.run(host='127.0.0.1', port=5000, debug=True)