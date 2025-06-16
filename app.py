import os
import gradio as gr
from embedding_utils import load_documents, embed_documents, create_vector_db, query_db
from sentence_transformers import SentenceTransformer
import openai

# Configuration
VAULT_PATH = "vaults/user_001"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Load user documents and create vector DB
model = SentenceTransformer("all-MiniLM-L6-v2")
documents = load_documents(VAULT_PATH)
texts, embeddings, metadatas = embed_documents(documents, model)
collection = create_vector_db(texts, embeddings, metadatas)

# GPT Assistant Function
def ask_assistant(question):
    if not question.strip():
        return "❗ Please enter a question."
    
    results = query_db(collection, model, question)
    if not results["documents"]:
        return "🤷 No relevant context found in user notes."
    
    context = "\n\n".join(results["documents"][0])

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful personal assistant."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"}
        ],
        temperature=0.7
    )
    return response.choices[0].message["content"]

# Create/Update Note (from Lovable onboarding for example)
def update_user_note(note_title, note_content):
    filepath = f"{VAULT_PATH}/{note_title}.md"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(note_content)
    return f"✅ Note '{note_title}' has been saved to the vault."

# Gradio Interface
with gr.Blocks() as app:
    gr.Markdown("# 🧠 Cocoon AI Assistant")
    
    with gr.Tab("Chat with your assistant"):
        question = gr.Textbox(label="Your question")
        answer = gr.Markdown()
        submit_btn = gr.Button("Ask")
        submit_btn.click(ask_assistant, inputs=question, outputs=answer)

    with gr.Tab("Create or update a note"):
        title = gr.Textbox(label="Note title")
        content = gr.Textbox(label="Note content", lines=6)
        result = gr.Textbox(label="Result")
        update_btn = gr.Button("Save note")
        update_btn.click(update_user_note, inputs=[title, content], outputs=result)

app.launch()