from profile_writer import write_profile_to_obsidian
import os
import json
import tempfile
import openai
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Query, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from supabase import create_client
from embedding_utils import load_documents, embed_documents, create_vector_db, query_db

# === Hugging Face Cache Setup ===
cache_dir = os.path.join(tempfile.gettempdir(), "hf_cache")
os.makedirs(cache_dir, exist_ok=True)
os.environ["TRANSFORMERS_CACHE"] = cache_dir
os.environ["HF_HOME"] = cache_dir

# === Environment Variables ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY environment variable.")

# === Init services ===
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY
model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=cache_dir)
app = FastAPI()

# === Vault Path Helper ===
def get_user_vault_path(user_id: str) -> str:
    base_path = os.path.join(tempfile.gettempdir(), "vaults")
    user_path = os.path.join(base_path, f"user_{user_id}")
    os.makedirs(user_path, exist_ok=True)
    return user_path

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
    profile_data: dict

class GenerateRequest(BaseModel):
    prompt: str

# === Routes ===
@app.get("/")
def root():
    return {"message": "API running"}

@app.get("/ping")
def ping():
    return {"pong": "ok"}

@app.get("/secrets")
def show_secrets():
    return {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")
    }

@app.post("/test")
async def test_connection():
    return {"status": "ok", "message": "Connected successfully"}

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
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{req.question}"}
            ],
            temperature=0.7
        )
        return {"answer": response.choices[0].message.content}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/note")
async def save_note(req: NoteRequest):
    try:
        path = get_user_vault_path(req.user_id)
        with open(os.path.join(path, f"{req.title}.md"), "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "Note saved."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/profile")
async def save_profile(req: ProfileRequest):
    try:
        path = get_user_vault_path(req.user_id)
        with open(os.path.join(path, "user_profile.json"), "w", encoding="utf-8") as f:
            json.dump(req.profile_data, f, indent=2)

        vault_path, files_written = write_profile_to_obsidian(req.user_id, req.profile_data)

        for rel_path, content in files_written:
            supabase_client.table("vault_files").upsert({
                "user_id": req.user_id,
                "path": rel_path,
                "content": content
            }).execute()

        return {"status": "Profile saved & Obsidian updated."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/obsidian")
async def upload_obsidian_file(user_id: str, file: UploadFile = File(...)):
    try:
        path = get_user_vault_path(user_id)
        with open(os.path.join(path, file.filename), "wb") as f:
            f.write(await file.read())
        return {"status": "File uploaded."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/sync_from_obsidian")
async def sync_from_obsidian(user_id: str):
    try:
        path = get_user_vault_path(user_id)
        profile_path = os.path.join(path, "Profile/user_profile.md")

        if not os.path.exists(profile_path):
            return JSONResponse(status_code=404, content={"error": "Profile not found."})

        with open(profile_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {"status": "Profile loaded.", "content": content}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/script")
async def generate_script(req: GenerateRequest):
    return await generate_with_role(req, "You are a creative screenwriter.")

@app.post("/concepts")
async def generate_concepts(req: GenerateRequest):
    return await generate_with_role(req, "You are an innovation engine.")

@app.post("/ideas")
async def generate_ideas(req: GenerateRequest):
    return await generate_with_role(req, "You are a content strategist.")

async def generate_with_role(req: GenerateRequest, role: str):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": role},
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.9
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/update_file")
async def update_file(
    user_id: str = Form(...),
    file_path: str = Form(...),
    new_content: str = Form(...)
):
    try:
        vault_path = get_user_vault_path(user_id)
        full_path = os.path.join(vault_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content.strip())

        supabase_client.table("vault_files").upsert({
            "user_id": user_id,
            "path": file_path,
            "content": new_content.strip()
        }).execute()

        return {"status": "File updated successfully", "file": file_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/add_resource")
async def add_resource(
    user_id: str = Form(...),
    title: str = Form(...),
    link: str = Form(...),
    resource_type: str = Form(...)
):
    try:
        safe_title = title.replace(" ", "_").lower()
        file_path = f"Resources_and_Skills/resources/{safe_title}.md"
        content = f"""# 💎 {title}
- Type: {resource_type}
- Link: {link}
"""

        vault_path = get_user_vault_path(user_id)
        full_path = os.path.join(vault_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip())

        supabase_client.table("vault_files").upsert({
            "user_id": user_id,
            "path": file_path,
            "content": content.strip()
        }).execute()

        return {"status": "Resource saved.", "file": file_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})