import os
import tempfile
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from supabase import create_client
import openai
from embedding_utils import load_documents, embed_documents, create_vector_db, query_db

# === Hugging Face Cache Setup ===
cache_dir = tempfile.gettempdir() + "/hf_cache"
os.makedirs(cache_dir, exist_ok=True)
os.environ["TRANSFORMERS_CACHE"] = cache_dir
os.environ["HF_HOME"] = cache_dir

# === Environment Variables ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# === Validation ===
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY environment variable.")

# === Initialize Services ===
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY
model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=cache_dir)
app = FastAPI()

# === Utils ===
def get_user_vault_path(user_id: str) -> str:
    return f"vaults/user_{user_id}"

# === Request Models ===
class AskRequest(BaseModel):
    user_id: str
    question: str

class NoteRequest(BaseModel):
    user_id: str
    title: str
    content: str

class ProfileRequest(BaseModel):
    user_id: str
    profile: str

class GenerateRequest(BaseModel):
    prompt: str

# === Test Endpoint ===
@app.post("/test")
async def test_connection(_: dict):
    return {"status": "ok", "message": "Connected successfully"}

# === Ask ===
@app.post("/ask")
async def ask(req: AskRequest):
    try:
        user_vault = get_user_vault_path(req.user_id)
        docs = load_documents(user_vault)
        texts, embeddings, metadatas = embed_documents(docs, model)
        collection = create_vector_db(texts, embeddings, metadatas)

        results = query_db(collection, model, req.question)
        if not results["documents"]:
            return {"answer": "No relevant context found."}

        context = "\n\n".join(results["documents"][0])

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{req.question}"},
            ],
            temperature=0.7
        )
        return {"answer": response.choices[0].message.content}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Save Note ===
@app.post("/note")
async def save_note(req: NoteRequest):
    try:
        path = get_user_vault_path(req.user_id)
        os.makedirs(path, exist_ok=True)
        with open(f"{path}/{req.title}.md", "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "Note saved."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Save Profile ===
@app.post("/profile")
async def save_profile(req: ProfileRequest):
    try:
        path = get_user_vault_path(req.user_id)
        os.makedirs(path, exist_ok=True)
        with open(f"{path}/user_profile.md", "w", encoding="utf-8") as f:
            f.write(req.profile)
        return {"status": "Profile saved."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Upload Obsidian ===
@app.post("/obsidian")
async def upload_obsidian_file(user_id: str, file: UploadFile = File(...)):
    try:
        path = get_user_vault_path(user_id)
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, file.filename), "wb") as f:
            f.write(await file.read())
        return {"status": "File uploaded."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Generate ===
@app.post("/script")
@app.post("/concepts")
@app.post("/ideas")
async def generate(req: GenerateRequest):
    try:
        prompt_type = {
            "/script": "You are a creative screenwriter.",
            "/concepts": "You are an innovation engine.",
            "/ideas": "You are a content strategist."
        }
        last_path = str(app.router.routes[-1].path)
        system_msg = prompt_type.get(last_path, "You are a helpful assistant.")

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.9
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Ping (Healthcheck) ===
@app.get("/ping")
def ping():
    return {"pong": "ok"}
