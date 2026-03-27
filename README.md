# ⚖️ Ask UK Law: Professional Student Legal Assistant

An advanced **RAG-powered Knowledge Base** designed to help international students in the UK understand their legal rights regarding **Housing**, **Employment**, **Work Rights**, and **Schengen Visas**.

This system uses a **Hybrid Retrieval** approach (Keyword + Semantic) with **Neural Reranking** to provide high-precision legal citations from real UK Statutes.

---

## 🚀 Key Features

- **💬 Expert Legal Chat**: Search across the *Housing Act 1988*, *Employment Rights Act 1996*, and *UK Immigration Rules*.
- **📄 Contract PDF Auditor**: Upload your tenancy or employment contract to identify potential conflicts with UK law (e.g., illegal viewing fees or deposit issues).
- **✉️ Formal Letter Generator**: Automate the drafting of professional complaint letters based on specific retrieved legal sections.
- **🔊 Multilingual Support & TTS**: Translate results into Spanish, Mandarin, or Hindi with AI-generated audio summaries.

---

## 🛠️ Technical Stack

| Component | Tool / Implementation |
| :--- | :--- |
| **Language** | Python 3.10+ |
| **Vector Database** | **ChromaDB** (Persistent Dense Embeddings) |
| **Keyword Search** | **BM25Okapi** (Sparse Ranking) |
| **Embedding Model** | `all-MiniLM-L6-v2` (SentenceTransformers) |
| **Reranker** | `ms-marco-MiniLM-L-6-v2` (Cross-Encoder) |
| **Frontend** | **Gradio** (Modern Web UI) |
| **Translation** | GoogleTranslator API |

---

## 🏗️ Retrieval Architecture

The system uses a **Two-Stage Retrieval Pipeline**:

1.  **Stage 1: Hybrid Retrieval**:
    - **Dense**: ChromaDB finds sections with similar *meaning*.
    - **Sparse**: BM25 finds sections with exact *keywords*.
    - Combined using an Alpha weight ($\alpha=0.8$ for semantic-heavy results).

2.  **Stage 2: Neural Reranking**:
    - A **Cross-Encoder** reviews the top 10 candidates from Stage 1. It compares the user's specific query against the full text of each law section to ensure the most accurate legislation is ranked #1.

---

## 📊 Evaluation Metrics

Run `evaluate.py` to benchmark the system against the included Golden Dataset (`data/benchmark/golden_dataset.json`).

- **Recall@5**: Measures how often the ground-truth law is in the top 5 results.
- **MRR (Mean Reciprocal Rank)**: Evaluates the specific position of the correct law section.

---

## ⚙️ Installation & Usage

### 1. Set up Environment
```bash
python -m venv venv
source venv/bin/activate
pip install gradio chromadb sentence-transformers deep-translator gTTS pdfplumber rank-bm25
```

### 2. Index the Data
If the `data/` folder is empty, run the pipeline:
1.  `python fetch_statute.py` (Fetch XML)
2.  `python parse_statute.py` (Generate Chunks)
3.  `python indexer.py` (Build ChromaDB and BM25 indexes)

### 3. Launch the App
```bash
python app.py
```
Open `http://localhost:7860` in your browser.

---

## 📂 Project Structure

- `app.py`: Main Gradio web application.
- `retriever.py`: Hybrid search and reranking logic (Optimized Singleton).
- `indexer.py`: Logic for building semantic and keyword indexes.
- `contract_analyzer.py`: PDF parsing and automated risk audit.
- `data/chroma_db/`: Persistent vector database storage.
- `data/index/bm25_index.pkl`: Serialized keyword index.

---

## ⚖️ Disclaimer
*This tool is intended for educational and informational purposes only and does not constitute official legal advice. Always consult a qualified solicitor for specific legal matters.*
