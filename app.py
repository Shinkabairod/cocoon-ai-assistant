import os
import tempfile

# Create a temporary directory for Hugging Face model cache
cache_dir = tempfile.gettempdir() + "/hf_cache"
os.makedirs(cache_dir, exist_ok=True)
os.environ["TRANSFORMERS_CACHE"] = cache_dir
os.environ["HF_HOME"] = cache_dir

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import openai

from embedding_utils import load_documents, embed_documents, create_vector_db, query_db

# Configuration
VAULT_PATH = "vaults/user_001"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Load documents and initialize vector DB
model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=cache_dir)
documents = load_documents(VAULT_PATH)
texts, embeddings, metadatas = embed_documents(documents, model)
collection = create_vector_db(texts, embeddings, metadatas)

# FastAPI app
app = FastAPI()

# Request models
class AskRequest(BaseModel):
    question: str

class NoteRequest(BaseModel):
    title: str
    content: str

# Endpoint: Ask assistant
@app.post("/ask")
async def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "Question cannot be empty."})

    results = query_db(collection, model, question)
    if not results["documents"]:
        return {"answer": "No relevant context found in user notes."}

    context = "\n\n".join(results["documents"][0])

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful personal assistant."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"}
            ],
            temperature=0.7
        )
        answer = response.choices[0].message["content"]
        return {"answer": answer}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Endpoint: Save or update a note
@app.post("/note")
async def create_or_update_note(req: NoteRequest):
    title = req.title.strip()
    content = req.content.strip()

    if not title or not content:
        return JSONResponse(status_code=400, content={"error": "Title and content are required."})

    filepath = f"{VAULT_PATH}/{title}.md"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return {"status": f"Note '{title}' saved successfully."}