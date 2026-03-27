import json
import os
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
import pickle

def setup_chromadb(collection_name="uk_statutes"):
    """
    Initializes a persistent ChromaDB client.
    """
    # Store DB in the data folder
    db_path = os.path.join(os.getcwd(), "data", "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    
    # We will use a lightweight local model for demonstration (MiniLM)
    # In production for legal text, you would use NLPAUEB/Legal-BERT or OpenAI
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    # Get or create collection
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=sentence_transformer_ef,
        metadata={"hnsw:space": "cosine"}
    )
    
    return collection

def index_dense_embeddings(chunks_path: str, collection):
    """
    Embeds the parsed JSON chunks and stores them in ChromaDB.
    """
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
        
    documents = []
    metadatas = []
    ids = []
    
    for chunk in chunks:
        # The document is what gets embedded. It's crucial to include title context.
        doc_text = f"Act: {chunk.get('act_title', '')}. Section: {chunk.get('section_title', '')}. Text: {chunk.get('text', '')}"
        
        documents.append(doc_text)
        
        # Metadata is highly useful for pre-filtering (e.g. "Only search Fraud Act 2006")
        metadatas.append({
            "act_title": chunk.get('act_title', ''),
            "year": chunk.get('year', ''),
            "section_number": chunk.get('section_number', '')
        })
        
        ids.append(chunk["id"])
        
    print(f"Adding {len(documents)} chunks to ChromaDB...")
    # Add to collection in batches (Chroma handles batching nicely natively)
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print("Dense Indexing Complete.")

def index_sparse_bm25(chunks_path: str, output_path: str):
    """
    Creates a traditional BM25 TF-IDF index for exact keyword matching.
    """
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
        
    # BM25 requires tokenized text
    corpus = [chunk.get('text', '').lower().split() for chunk in chunks]
    chunk_ids = [chunk["id"] for chunk in chunks]
    
    bm25 = BM25Okapi(corpus)
    
    # Save the BM25 index and chunk ID mapping
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump({'bm25': bm25, 'ids': chunk_ids, 'chunks': chunks}, f)
        
    print(f"Sparse (BM25) Indexing Complete. Saved to {output_path}")

def load_all_chunks(parsed_dir: str):
    import glob
    all_chunks = []
    chunk_files = glob.glob(os.path.join(parsed_dir, "*.json"))
    for file_path in chunk_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
            all_chunks.extend(chunks)
    return all_chunks

def index_dense_embeddings_from_data(chunks, collection):
    documents = []
    metadatas = []
    ids = []
    
    for chunk in chunks:
        doc_text = f"Act: {chunk.get('act_title', '')}. Section: {chunk.get('section_title', '')}. Text: {chunk.get('text', '')}"
        documents.append(doc_text)
        metadatas.append({
            "act_title": chunk.get('act_title', ''),
            "year": chunk.get('year', ''),
            "section_number": chunk.get('section_number', '')
        })
        ids.append(chunk["id"])
        
    print(f"Adding {len(documents)} chunks to ChromaDB...")
    # Add to collection in batches natively supported by ChromaDB
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print("Dense Indexing Complete.")

def index_sparse_bm25_from_data(chunks, output_path: str):
    corpus = [chunk.get('text', '').lower().split() for chunk in chunks]
    chunk_ids = [chunk["id"] for chunk in chunks]
    
    bm25 = BM25Okapi(corpus)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump({'bm25': bm25, 'ids': chunk_ids, 'chunks': chunks}, f)
        
    print(f"Sparse (BM25) Indexing Complete. Saved to {output_path}")

def run_indexing():
    parsed_dir = "data/parsed"
    bm25_index_file = "data/index/bm25_index.pkl"
    
    if not os.path.exists(parsed_dir):
        print("Please run parse_statute.py first to generate chunks.")
        return
        
    all_chunks = load_all_chunks(parsed_dir)
    if not all_chunks:
        print("No chunks found in data/parsed")
        return
        
    print("Starting Dense Indexing (Vector Embeddings)...")
    collection = setup_chromadb()
    
    if collection.count() < len(all_chunks):
        print("Updating ChromaDB collection...")
        client = chromadb.PersistentClient(path=os.path.join(os.getcwd(), "data", "chroma_db"))
        try:
            client.delete_collection("uk_statutes")
            print("Dropped old collection.")
        except:
            pass
        collection = setup_chromadb()
        index_dense_embeddings_from_data(all_chunks, collection)
    else:
         print(f"Collection already has {collection.count()} chunks. Skipping dense indexing.")
         
    print("\nStarting Sparse Indexing (BM25)...")
    index_sparse_bm25_from_data(all_chunks, bm25_index_file)

if __name__ == "__main__":
    run_indexing()
