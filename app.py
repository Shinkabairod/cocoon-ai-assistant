import gradio as gr

def lire_fichier_test():
    try:
        with open("./vault/test.md", "r", encoding="utf-8") as f:
            contenu = f.read()
            return f"✅ Fichier trouvé !\n\n🧠 Contenu :\n{contenu}"
    except FileNotFoundError:
        return "❌ Le fichier `vault/test.md` n'existe pas ou n'est pas visible."
    except Exception as e:
        return f"⚠️ Erreur : {str(e)}"

iface = gr.Interface(
    fn=lire_fichier_test,
    inputs=[],
    outputs="text",
    title="🧪 Test Lecture Unique",
    description="Essaie de lire `vault/test.md` en lecture brute."
)

iface.launch()