import fitz  # PyMuPDF
import os
from retriever import hybrid_search, load_indexes

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def analyze_contract(pdf_path, collection, bm25_data):
    full_text = extract_text_from_pdf(pdf_path)
    
    # Split text into rough "clauses" (by double newline or section markers)
    clauses = [c.strip() for c in full_text.split('\n\n') if len(c.strip()) > 50]
    
    findings = []
    
    # Audit each clause against the law
    # For a demo, we'll focus on keywords that often cause issues for students
    risky_keywords = ["deposit", "terminate", "notice period", "fees", "repairs", "work hours", "redundancy"]
    
    for clause in clauses:
        is_relevant = any(kw in clause.lower() for kw in risky_keywords)
        
        if is_relevant:
            # Search for the law that might apply to this clause
            legal_matches = hybrid_search(clause, collection, bm25_data, top_k=1, alpha=0.8, rerank=True)
            
            if legal_matches:
                doc_id, score = legal_matches[0]
                chunk_data = next((c for c in bm25_data['chunks'] if c['id'] == doc_id), None)
                
                findings.append({
                    "clause": clause,
                    "law_title": chunk_data['act_title'] if chunk_data else "Unknown",
                    "law_section": chunk_data['section_number'] if chunk_data else "N/A",
                    "law_text": chunk_data['text'] if chunk_data else "",
                    "score": score
                })

                
    return findings

if __name__ == "__main__":
    # Test would go here
    pass
