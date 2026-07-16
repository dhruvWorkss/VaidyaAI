import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

# Path to our medical docs
DOCS_PATH = os.path.join(os.path.dirname(__file__), "../../data/medical_docs")
FAISS_INDEX_PATH = os.path.join(os.path.dirname(__file__), "../../data/faiss_index")

# We use a free HuggingFace embedding model — no API key needed
# This converts text into vectors so FAISS can search them
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def build_vector_store():
    """
    Loads all .txt files from medical_docs folder,
    splits them into chunks, embeds them, and saves FAISS index.
    Run this once to build the index.
    """
    print("Building FAISS vector store from medical docs...")
    
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    all_docs = []
    
    # Load every .txt file in the medical_docs folder
    for filename in os.listdir(DOCS_PATH):
        if filename.endswith(".txt"):
            filepath = os.path.join(DOCS_PATH, filename)
            loader = TextLoader(filepath, encoding="utf-8")
            docs = loader.load()
            all_docs.extend(docs)
    
    # Split docs into chunks
    # chunk_size=500 means each chunk is ~500 characters
    # chunk_overlap=50 means chunks share 50 chars to preserve context
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(all_docs)
    print(f"Split into {len(chunks)} chunks")
    
    # Create FAISS vector store and save it
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(FAISS_INDEX_PATH)
    print(f"FAISS index saved to {FAISS_INDEX_PATH}")
    
    return vector_store


def load_vector_store():
    """
    Loads the existing FAISS index from disk.
    If it doesn't exist, builds it first.
    """
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    if not os.path.exists(FAISS_INDEX_PATH):
        print("FAISS index not found — building it now...")
        return build_vector_store()
    
    print("Loading existing FAISS index...")
    return FAISS.load_local(
        FAISS_INDEX_PATH, 
        embeddings,
        allow_dangerous_deserialization=True
    )


def retrieve_medical_context(query: str, k: int = 3) -> str:
    """
    Main function — takes a patient query,
    searches the FAISS index, returns relevant medical context as text.
    k=3 means return top 3 most relevant chunks.
    """
    vector_store = load_vector_store()
    
    # Search for most similar chunks
    results = vector_store.similarity_search(query, k=k)
    
    if not results:
        return "No specific medical context found."
    
    # Join all chunks into one context string
    context = "\n\n".join([doc.page_content for doc in results])
    return context