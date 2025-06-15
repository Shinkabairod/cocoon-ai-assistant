import gradio as gr
from utils import load_vault

documents = load_vault()

def show_documents():
    if not documents:
        return "Aucun fichier trouvé dans le dossier /vault."
    output = ""
    for doc in documents:
        output += f"### {doc['filename']}\n"
        output += doc["text"][:500] + "\n\n---\n\n"
    return output

iface = gr.Interface(
    fn=show_documents,
    inputs=[],
    outputs=gr.Markdown(),
    title="Cocoon Vault Preview",
    description="Aperçu des fichiers présents dans le dossier Obsidian `/vault/`."
)

iface.launch()