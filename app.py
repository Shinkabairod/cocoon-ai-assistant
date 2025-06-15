
import gradio as gr
import os

def assistant(query):
    # Placeholder logic (à remplacer par ton moteur RAG)
    return f"Tu as demandé : '{query}'. (La réponse de l'IA sera ici.)"

iface = gr.Interface(
    fn=assistant,
    inputs=gr.Textbox(label="Pose ta question"),
    outputs=gr.Textbox(label="Réponse de l'assistant IA"),
    title="Cocoon AI Assistant",
    description="Assistant IA personnel basé sur tes ressources Obsidian.",
)

iface.launch()
