import gradio as gr
import os
import openai
from embedding_utils import load_documents, embed_documents, create_vector_db, query_db
from sentence_transformers import SentenceTransformer

# 🔐 Auth OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# 📁 Chemin vers ton dossier de notes
VAULT_PATH = "vaults/user_001"
model = SentenceTransformer("all-MiniLM-L6-v2")

# 📦 Indexation
documents = load_documents(VAULT_PATH)
texts, embeddings, metadatas = embed_documents(documents, model)
collection = create_vector_db(texts, embeddings, metadatas)

# 🧠 Prompt GPT-3.5
def generate_answer(context, question):
    prompt = f"""Tu es un assistant IA spécialisé dans l'analyse de notes Obsidian. Voici le contexte extrait des fichiers de l'utilisateur :

{context}

Réponds à la question suivante de manière claire et précise :
"{question}"
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un assistant intelligent et utile."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ Erreur GPT : {str(e)}"

# 🎯 Fonction principale
def ask_question(question):
    if not question.strip():
        return "❗️ Veuillez poser une question."
    
    results = query_db(collection, model, question)
    if not results["documents"]:
        return "🤷 Aucun contexte trouvé dans les fichiers."
    
    context = "\n\n".join(results["documents"])
    response = generate_answer(context, question)

    return f"📚 **Contexte extrait** :\n{context}\n\n🤖 **Réponse générée par GPT-3.5** :\n{response}"

# 🚀 Interface Gradio
iface = gr.Interface(
    fn=ask_question,
    inputs=gr.Textbox(placeholder="Pose ta question ici..."),
    outputs="markdown",
    title="Cocoon AI – Question sur ton contenu",
    description="Pose une question à partir de tes notes Obsidian (`vaults/user_001`) – l'IA lira et répondra avec le contexte."
)

iface.launch()