import json
import os
import pickle
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import CrossEncoder

# Initialize reranker lazily or once
_RERANKER_MODEL = None

def get_reranker():
    global _RERANKER_MODEL
    if _RERANKER_MODEL is None:
        print("Loading Cross-Encoder reranker...")
        _RERANKER_MODEL = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _RERANKER_MODEL

def load_indexes():
    """
    Loads both ChromaDB (Dense) and BM25 (Sparse) indexes.
    """
    db_path = os.path.join(os.getcwd(), "data", "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    collection = client.get_collection(
        name="uk_statutes",
        embedding_function=sentence_transformer_ef
    )
    
    bm25_path = "data/index/bm25_index.pkl"
    with open(bm25_path, 'rb') as f:
        bm25_data = pickle.load(f)
        
    return collection, bm25_data

def rerank_results(query, candidates, bm25_data, top_n=3):
    """
    Uses a Cross-Encoder model to rerank the top candidates.
    """
    if not candidates:
        return []
    
    # Load Cross-Encoder (MiniLM is fast for local CPU)
    model = get_reranker()
    
    # Prepare the query-passage pairs
    pairs = []
    chunk_map = {c['id']: c for c in bm25_data['chunks']}
    
    for doc_id, _ in candidates:
        chunk = chunk_map.get(doc_id)
        if chunk:
            text = f"Act: {chunk['act_title']}. Section: {chunk['section_title']}. Text: {chunk['text']}"
            pairs.append([query, text])
    
    if not pairs:
        return candidates[:top_n]
        
    # Predict scores
    scores = model.predict(pairs)
    
    # Pair scores with IDs and sort
    reranked = []
    for i in range(len(pairs)):
        doc_id = candidates[i][0]
        reranked.append((doc_id, float(scores[i])))
        
    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked[:top_n]


def hybrid_search(query: str, collection, bm25_data, top_k=5, alpha=0.5, rerank=False):
    """
    Performs a hybrid search combining dense and sparse scores.
    Alpha controls the weight (1.0 = purely dense, 0.0 = purely sparse).
    If rerank=True, an additional Cross-Encoder step is performed.
    """
    # 1. Sparse Retrieval (BM25)
    tokenized_query = query.lower().split()
    bm25_scores = bm25_data['bm25'].get_scores(tokenized_query)
    
    sparse_results = {}
    for i, score in enumerate(bm25_scores):
        if score > 0:
             sparse_results[bm25_data['ids'][i]] = score

    # Normalize sparse scores (simple max normalization)
    max_sparse = max(sparse_results.values()) if sparse_results else 1.0
    if max_sparse == 0: max_sparse = 1.0
    for k in sparse_results:
        sparse_results[k] = sparse_results[k] / max_sparse

    # 2. Dense Retrieval (ChromaDB)
    dense_resp = collection.query(
        query_texts=[query],
        n_results=top_k * 5 # get more results to merge if we are reranking
    )
    
    dense_results = {}
    # Chroma uses distance (lower is better), we need similarity (higher is better)
    # Cosine distance: similarity = 1 - distance
    distances = dense_resp['distances'][0]
    ids = dense_resp['ids'][0]
    
    for i in range(len(ids)):
        sim_score = 1.0 - distances[i]
        dense_results[ids[i]] = sim_score
        
    # 3. Combine Scores
    hybrid_scores = {}
    all_keys = set(sparse_results.keys()).union(set(dense_results.keys()))
    
    for key in all_keys:
        s_score = sparse_results.get(key, 0.0)
        d_score = dense_results.get(key, 0.0)
        hybrid_scores[key] = (alpha * d_score) + ((1 - alpha) * s_score)
        
    # 4. Sort
    sorted_candidates = sorted(hybrid_scores.items(), key=lambda item: item[1], reverse=True)
    
    # 5. Optional Reranking
    if rerank:
        # Rerank the top 10 candidates using Cross-Encoder
        return rerank_results(query, sorted_candidates[:10], bm25_data, top_n=top_k)
        
    return sorted_candidates[:top_k]


if __name__ == "__main__":
    try:
        collection, bm25_data = load_indexes()
        
        test_queries = [
            "What is the penalty for fraud by false representation?", # Should hit Section 1/2
            "Is there a punishment for possessing articles for use in fraud?", # Should hit Section 6
        ]
        
        print("=== Testing Hybrid Search ===")
        for q in test_queries:
            print(f"\nQuery: '{q}'")
            results = hybrid_search(q, collection, bm25_data, top_k=3, alpha=0.5) # Balanced hybrid
            
            for i, (doc_id, score) in enumerate(results):
                chunk_data = next(c for c in bm25_data['chunks'] if c['id'] == doc_id)
                print(f"  {i+1}. [Score: {score:.4f}] {chunk_data['act_title']} - Sec {chunk_data['section_number']}: {chunk_data['section_title']}")
                
    except Exception as e:
        print(f"Error loading indexes or running search: {e}")
        print("Make sure indexer.py has completed successfully.")
