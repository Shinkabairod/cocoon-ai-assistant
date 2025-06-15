import gradio as gr
import os

def load_vault(vault_path="vault"):
    output = ""
    output += f"🔍 Dossier scanné : {vault_path}\n\n"
    if not os.path.exists(vault_path):
        return f"❌ Le dossier `{vault_path}` n'existe pas."

    files_found = 0
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            files_found += 1
            full_path = os.path.join(root, file)
            output += f"📄 Fichier trouvé : {file}\n"
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    preview = content[:200] if len(content) > 200 else content
                    output += f"🧠 Contenu (extrait) :\n{preview}\n\n---\n\n"
            except Exception as e:
                output += f"⚠️ Erreur lors de la lecture de {file} : {str(e)}\n"

    if files_found == 0:
        output += "❌ Aucun fichier trouvé dans le dossier."
    else:
        output += f"✅ {files_found} fichier(s) traité(s)."

    return output

iface = gr.Interface(
    fn=load_vault,
    inputs=[],
    outputs="text",
    title="🧠 Debug Cocoon Vault",
    description="Affiche tous les fichiers trouvés dans `/vault/` et leur contenu (extrait)."
)

iface.launch()