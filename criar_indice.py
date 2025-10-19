# criar_indice.py
import os
import pathlib
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS

# Carrega as variáveis do arquivo .env
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY não encontrada no arquivo .env")

print("Iniciando processo de criação de índice...")

# Inicializa o modelo de embeddings (Sugestão: use o modelo mais recente)
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", # <-- Modelo mais novo e recomendado
    google_api_key=GOOGLE_API_KEY
)

# 1. Carregar os documentos
docs = []
pdf_files = list(pathlib.Path("./docs_web_junior/").glob("*.pdf")) 

if not pdf_files:
    print("Nenhum arquivo PDF encontrado. Abortando.")
else:
    for n in pdf_files:
        try:
            loader = PyMuPDFLoader(str(n))
            docs.extend(loader.load())
            print(f"Carregado: {n.name}")
        except Exception as e:
            print(f"Erro ao carregar {n.name}: {e}")

    # 2. Dividir em chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=10)
    chunks = splitter.split_documents(docs)
    print(f"Total de documentos divididos em {len(chunks)} chunks.")

    # 3. Criar os embeddings e o Vectorstore FAISS
    # Esta é a parte que consome a API. Será executada apenas uma vez.
    print("Gerando embeddings e criando o vectorstore FAISS. Isso pode levar alguns minutos...")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    print("Vectorstore criado com sucesso.")

    # 4. Salvar o índice localmente
    vectorstore.save_local("faiss_index")
    print("Índice FAISS salvo com sucesso na pasta 'faiss_index'.")