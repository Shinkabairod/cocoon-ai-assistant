import gradio as gr
from sentence_transformers import SentenceTransformer
from embedding_utils import load_documents, embed_documents, create_vector_db, query_db

# ✅ Chargement du modèle stable
model = SentenceTransformer("all-MiniLM-L6-v2")

# ✅ Chargement des documents depuis /vault
documents = load_documents("vault")
texts, embeddings, metadatas = embed_documents(documents, model)
collection = create_vector_db(texts, embeddings, metadatas)

# ✅ Fonction principale
def ask_question(question):
    if not question.strip():
        return "❗️ Veuillez poser une question."
    results = query_db(collection, model, question)
    if not results["documents"]:
        return "🤷 Aucun résultat trouvé."

    context = "\n\n".join(results["documents"][0])
    return f"📚 **Contexte extrait** :\n{context}\n\n🤖 **Réponse hypothétique** :\n{question}... (à compléter avec un LLM si besoin)"

# ✅ Interface Gradio
iface = gr.Interface(
    fn=ask_question,
    inputs=gr.Textbox(placeholder="Pose ta question ici..."),
    outputs="markdown",
    title="Cocoon AI – Question sur ton contenu",
    description="Pose une question à partir de tes fichiers Obsidian (`vault/`) – l'IA cherchera et répondra avec le contexte."
)

iface.launch()