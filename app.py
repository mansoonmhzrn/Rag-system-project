import os
import json
import gradio as gr
import tempfile
import re
from retriever import load_indexes, hybrid_search
from deep_translator import GoogleTranslator
from gtts import gTTS
from contract_analyzer import analyze_contract
from letter_generator import generate_complaint_letter

# Load indexes once when the app starts
try:
    print("Loading legal indexes...")
    collection, bm25_data = load_indexes()
    print("Indexes loaded successfully!")
except Exception as e:
    collection, bm25_data = None, None
    print(f"Failed to load indexes: {e}")

# --- Helper Functions ---

LEGAL_GLOSSARY = {
    "fraud": "Dishonestly tricking someone to get money or a benefit.",
    "possession": "Having or controlling an object.",
    "indictment": "A formal charge or accusation of a serious crime.",
    "conviction": "Being found guilty of a crime in a court of law.",
    "tenant": "A person who occupies land or property rented from a landlord.",
    "landlord": "A person who rents out land, a building, or accommodation.",
    "assured shorthold tenancy": "The most common type of tenancy used by private landlords in the UK.",
    "unfair dismissal": "When an employee is fired from their job in a way that is not legal."
}

def apply_glossary(text):
    for term, definition in LEGAL_GLOSSARY.items():
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(f'<span class="glossary-term" title="{definition}">{term}</span>', text)
    return text

def translate_text(text, target_lang_code):
    if target_lang_code == "en": return text
    try:
        return GoogleTranslator(source='auto', target=target_lang_code).translate(text)
    except: return text

def generate_tts(text, lang_code):
    try:
        tts = gTTS(text=text, lang='en' if lang_code not in ['en', 'es', 'zh-CN', 'hi'] else lang_code)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_file.name)
        return temp_file.name
    except: return None

# --- Chat Logic ---

def chat_search(query, search_type, top_k, language, rerank, history):
    history = history or []
    lang_codes = {"English": "en", "Spanish": "es", "Mandarin": "zh-CN", "Hindi": "hi"}
    target_lang = lang_codes.get(language, "en")
    
    query_en = translate_text(query, "en") if target_lang != "en" else query
    
    alpha = 0.8
    if "Sparse" in search_type: alpha = 0.0
    elif "Dense" in search_type: alpha = 1.0

    try:
        results = hybrid_search(query_en, collection, bm25_data, top_k=int(top_k), alpha=alpha, rerank=rerank)
        
        if not results:
            msg = translate_text("No relevant legal sections found.", target_lang)
            new_history = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": msg}
            ]
            return "", new_history, None, ""

        # Use first result for summary
        first_doc_id = results[0][0]
        first_chunk = next((c for c in bm25_data['chunks'] if c['id'] == first_doc_id), None)
        
        # Smart Summary logic snippet
        summary_en = f"Based on {first_chunk['act_title']}, Section {first_chunk['section_number']} appears most relevant. It covers {first_chunk['section_title']}. [Professional AI generated analysis]"
        summary_translated = translate_text(summary_en, target_lang)
        audio_path = generate_tts(summary_translated, target_lang)

        output_markdown = f"### {translate_text('Top Legal Citations', target_lang)}\n\n"
        for i, (doc_id, score) in enumerate(results):
            chunk = next((c for c in bm25_data['chunks'] if c['id'] == doc_id), None)
            if chunk:
                url = f"https://www.legislation.gov.uk/ukpga/{chunk['year']}/{chunk['act_number']}/section/{chunk['section_number']}"
                output_markdown += f"#### {i+1}. {chunk['act_title']} - Section {chunk['section_number']}: {chunk['section_title']}\n"
                output_markdown += f"**[{translate_text('View Original on Legislation.gov.uk', target_lang)}]({url})** | Score: `{score:.4f}`\n\n"
                output_markdown += f"{apply_glossary(chunk['text'])}\n\n---\n"

        # FOR SEARCH TOOLS: Replacing history is often better for visibility of fresh citations
        # To keep chat, use history = list(history) or []
        # To show only latest, use history = []
        new_history = [
            {"role": "user", "content": query},
            {"role": "assistant", "content": output_markdown}
        ]
        
        return "", new_history, audio_path, summary_translated
    except Exception as e:
        import traceback
        traceback.print_exc()
        # On error, we can try to return what we have or just show the error message
        return "", history or [], None, f"Error: {e}"

# --- Contract Audit Logic ---

def audit_pdf(file):
    if file is None: return "Please upload a PDF."
    try:
        findings = analyze_contract(file.name, collection, bm25_data)
        if not findings: return "No major legal risks identified in this sample scan."
        
        report = "### 📋 Contract Audit Report\nPotential conflicts identified with UK Statutes:\n\n"
        for item in findings:
            report += f'<div class="audit-card">\n'
            report += f"#### 🚩 Conflict with {item['law_title']}\n"
            report += f"**In your contract:**\n> {item['clause']}\n\n"
            report += f"**Relevant Law (Section {item['law_section']}):**\n{item['law_text']}\n"
            report += f'</div>\n\n'
        return report

    except Exception as e:
        return f"Error analyzing PDF: {e}"

# --- Letter Generator Logic ---

def create_letter(name, subject, grievance, law_ref):
    try:
        # Simple extraction for demo: "Housing Act 1988 - Sec 1"
        if " - Sec " in law_ref:
            parts = law_ref.split(' - Sec ')
            act = parts[0].strip()
            sec = parts[1].strip()
        else:
            act, sec = "UK Legislation", "Specified Section"
        
        # Search for full law text to include in letter
        res = hybrid_search(law_ref, collection, bm25_data, top_k=1)
        law_text = "[Statutory text will be inserted here]"
        if res:
            c = next((c for c in bm25_data['chunks'] if c['id'] == res[0][0]), None)
            if c: law_text = c['text']

        return generate_complaint_letter(name, "[Contact Details Provided]", subject, act, sec, law_text, grievance)
    except Exception as e:
        return f"Error generating letter: {e}"

# --- UI Layout ---

custom_css = """
.glossary-term { border-bottom: 2px dashed #ff4b4b; color: #ff4b4b; cursor: help; font-weight: bold; }
.gradio-container { background-color: #fdfdfd; }
.tabs { border-radius: 10px; overflow: hidden; }
.audit-card { 
    background-color: #ffffff; 
    border: 1px solid #e0e0e0; 
    border-radius: 8px; 
    padding: 15px; 
    margin-bottom: 20px; 
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
"""


with gr.Blocks(title="Ask UK Law Pro") as demo:
    gr.Markdown("# ⚖️ Ask UK Law: Professional Student Legal Assistant")
    gr.Markdown("Advanced RAG-powered toolkit for international students in the UK. (Reranking + Contract Audit + Letter Gen)")

    with gr.Tabs(elem_classes="tabs"):
        with gr.TabItem("💬 Expert Legal Chat"):
            with gr.Row():
                with gr.Column(scale=1):
                    lang_select = gr.Dropdown(choices=["English", "Spanish", "Mandarin", "Hindi"], value="English", label="Student's Language")
                    query_in = gr.Textbox(label="Enter your legal question", placeholder="e.g. My landlord is charging me a viewing fee...", lines=3)
                    
                    with gr.Accordion("Search Intelligence", open=False):
                        rerank_toggle = gr.Checkbox(label="Enable Cross-Encoder Reranking", value=True)
                        search_strat = gr.Dropdown(choices=["Hybrid Search (Recommended)", "Dense Semantic", "Sparse Keyword"], value="Hybrid Search (Recommended)", label="Vector Strategy")
                        k_slider = gr.Slider(minimum=1, maximum=10, value=3, step=1, label="Retrieve Top K")
                    
                    search_btn = gr.Button("🔍 Search Legislation", variant="primary")
                    
                    gr.Markdown("---")
                    gr.Markdown("### 🎓 Quick Scenario Buttons")
                    with gr.Row():
                        btn_f = gr.Button("Fraud/Scams", size="sm")
                        btn_h = gr.Button("Housing Issue", size="sm")
                    with gr.Row():
                        btn_v = gr.Button("Visa Rules", size="sm")
                        btn_w = gr.Button("Work Rights", size="sm")

                with gr.Column(scale=2):
                    with gr.Group():
                        gr.Markdown("### 💡 AI Plain-English Insight")
                        sum_out = gr.Markdown("*Search to generate a simplified legal summary...*")
                        aud_out = gr.Audio(label="Listen to Insight", autoplay=False)
                    chat_out = gr.Chatbot(label="Legal Citations & Official Text", height=550)

        with gr.TabItem("📄 Contract PDF Auditor"):
            gr.Markdown("### 🔍 Upload a Tenancy or Employment Contract")
            gr.Markdown("Identify potential illegal clauses by auditing your PDF contract against the UK Housing Act 1988 and Employment Rights Act 1996.")
            with gr.Row():
                with gr.Column():
                    pdf_in = gr.File(label="Upload Contract PDF", file_types=[".pdf"])
                    audit_btn = gr.Button("▶️ Begin Contract Audit", variant="primary")
                with gr.Column():
                    audit_out = gr.Markdown("### 🚩 Risk Findings\n*Awaiting analysis result...*")

        with gr.TabItem("✉️ Letter Generator"):
            gr.Markdown("### 🖋️ Draft a Formal Legal Complaint")
            with gr.Row():
                with gr.Column():
                    user_name = gr.Textbox(label="Your Full Name", placeholder="e.g. John Doe")
                    target_name = gr.Textbox(label="Recipient (Landlord/Employer Name)")
                    grievance = gr.Textbox(label="Describe the problem", placeholder="e.g. They are not returning my £500 deposit...")
                    law_reference = gr.Textbox(label="Law Reference (Copy-Paste from Chat)", placeholder="e.g. Housing Act 1988 - Sec 1")
                    gen_btn = gr.Button("📝 Generate Document", variant="primary")
                with gr.Column():
                    letter_out = gr.TextArea(label="Formal Complaint Draft", lines=25)

    # --- Interactions ---
    search_btn.click(chat_search, [query_in, search_strat, k_slider, lang_select, rerank_toggle, chat_out], [query_in, chat_out, aud_out, sum_out])
    audit_btn.click(audit_pdf, [pdf_in], [audit_out])
    gen_btn.click(create_letter, [user_name, target_name, grievance, law_reference], [letter_out])
    
    btn_f.click(lambda: "I think I am a victim of fraud", outputs=query_in)
    btn_h.click(lambda: "What are the rules for tenancy deposits?", outputs=query_in)
    btn_v.click(lambda: "Student visa work conditions Rules", outputs=query_in)
    btn_w.click(lambda: "I was fired unfairly from my job", outputs=query_in)

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(), css=custom_css)
