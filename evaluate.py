import json
import os
from retriever import load_indexes, hybrid_search

def compute_metrics(dataset_path: str, collection, bm25_data, top_k=5, alpha=0.5):
    """
    Evaluates the hybrid search against the Golden Dataset.
    Metrics: Recall@K, Mean Reciprocal Rank (MRR)
    """
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
        
    total_queries = len(dataset)
    hits = 0
    mrr_sum = 0.0
    
    print(f"Evaluating {total_queries} queries with Alpha={alpha} (0=Sparse, 1=Dense)...")
    
    for item in dataset:
        query = item['query']
        ground_truth_id = item['ground_truth_chunk_id']
        
        # Retrieve top K
        results = hybrid_search(query, collection, bm25_data, top_k=top_k, alpha=alpha)
        
        # Calculate Rank
        rank = -1
        for i, (doc_id, score) in enumerate(results):
            if doc_id == ground_truth_id:
                rank = i + 1
                break
                
        if rank != -1:
            hits += 1
            mrr_sum += (1.0 / rank)
            
    recall_at_k = (hits / total_queries) * 100
    mrr = (mrr_sum / total_queries)
    
    print(f"--- Results (Top-{top_k}) ---")
    print(f"Recall@{top_k}: {recall_at_k:.2f}% ({hits}/{total_queries})")
    print(f"MRR:        {mrr:.4f}")
    
    return recall_at_k, mrr

if __name__ == "__main__":
    dataset_file = "data/benchmark/golden_dataset.json"
    
    if not os.path.exists(dataset_file):
        print("Please run generate_dataset.py first.")
        exit(1)
        
    print("Loading indexes...")
    collection, bm25_data = load_indexes()
    
    print("\n--- Baseline: Sparse Only (BM25) ---")
    compute_metrics(dataset_file, collection, bm25_data, top_k=5, alpha=0.0)
    
    print("\n--- Baseline: Dense Only (SentenceTransformers) ---")
    compute_metrics(dataset_file, collection, bm25_data, top_k=5, alpha=1.0)
    
    print("\n--- Hybrid Search (50/50 Split) ---")
    compute_metrics(dataset_file, collection, bm25_data, top_k=5, alpha=0.5)

    print("\n--- Hybrid Search (Dense Weighted) ---")
    compute_metrics(dataset_file, collection, bm25_data, top_k=5, alpha=0.8)
