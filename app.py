import os
import tempfile

# Setup Hugging Face cache in a writable temp directory
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

def get_user_vault_path(user_id: str) -> str:
    return f"vaults/user_{user_id}"

# Load documents and initialize vector DB
model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=cache_dir)
documents = load_documents(VAULT_PATH)
texts, embeddings, metadatas = embed_documents(documents, model)
collection = create_vector_db(texts, embeddings, metadatas)

# FastAPI app
app = FastAPI()

# Request models
class AskRequest(BaseModel):
    user_id: str
    question: str

class NoteRequest(BaseModel):
    user_id: str
    title: str
    content: str

class GenerateRequest(BaseModel):
    prompt: str

# Endpoint: Ask assistant
@app.post("/ask")
async def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "Question cannot be empty."})

    user_vault = get_user_vault_path(req.user_id)

    try:
        documents = load_documents(user_vault)
        texts, embeddings, metadatas = embed_documents(documents, model)
        collection = create_vector_db(texts, embeddings, metadatas)

        results = query_db(collection, model, question)
        if not results["documents"]:
            return {"answer": "No relevant context found in your notes."}

        context = "\n\n".join(results["documents"][0])

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

    user_vault = get_user_vault_path(req.user_id)
    filepath = f"{user_vault}/{title}.md"

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return {"status": f"Note '{title}' saved successfully for user {req.user_id}."}

# Endpoint: Generate a script
@app.post("/script")
async def generate_script(req: GenerateRequest):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a creative screenwriter. Generate a script based on the following user prompt."},
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.8
        )
        return {"script": response.choices[0].message["content"]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Endpoint: Generate creative concepts
@app.post("/concepts")
async def generate_concepts(req: GenerateRequest):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an idea generation engine. Based on the prompt, generate innovative project or product concepts."},
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.9
        )
        return {"concepts": response.choices[0].message["content"]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Endpoint: Generate content ideas
@app.post("/ideas")
async def generate_ideas(req: GenerateRequest):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a social content strategist. Generate original content ideas based on the user input."},
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.9
        )
        return {"ideas": response.choices[0].message["content"]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})