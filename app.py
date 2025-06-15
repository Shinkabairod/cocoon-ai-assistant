import gradio as gr
from utils import load_vault

def test_vault():
    documents = load_vault()
    if not documents:
        return "⚠️ Aucun fichier trouvé dans /vault/"
    return f"✅ {len(documents)} fichier(s) trouvé(s) :\\n\\n" + "\\n".join([doc["filename"] for doc in documents])

iface = gr.Interface(
    fn=test_vault,
    inputs=[],
    outputs="text",
    title="Test Lecture Vault",
    description="Ce test affiche les fichiers trouvés dans ton dossier `/vault`."
)

iface.launch()