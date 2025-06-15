
import gradio as gr
from InstructorEmbedding import INSTRUCTOR
from embedding_utils import load_documents, embed_documents, create_vector_db, query_db

model = INSTRUCTOR("hkunlp/instructor-base")

documents = load_documents("vault")
texts, embeddings, metadatas = embed_documents(documents, model)
collection = create_vector_db(texts, embeddings, metadatas)

def ask_question(question):
    if not question.strip():
        return "❗️ Veuillez poser une question."
    results = query_db(collection, model, question)
    if not results["documents"]:
        return "🤷 Aucun résultat trouvé."

    context = "\n\n".join(results["documents"][0])
    return f"📚 **Contexte extrait** :\n{context}\n\n🤖 **Réponse hypothétique** :\n{question}... (à compléter avec un LLM si besoin)"

iface = gr.Interface(
    fn=ask_question,
    inputs=gr.Textbox(placeholder="Pose ta question ici..."),
    outputs="markdown",
    title="Cocoon AI – Question sur ton contenu",
    description="Pose une question à partir de tes fichiers Obsidian (`vault/`) – l'IA cherchera et répondra avec le contexte."
)

iface.launch()
