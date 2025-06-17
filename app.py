import os
import tempfile

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import openai

from embedding_utils import load_documents, embed_documents, create_vector_db, query_db

# Setup temporary cache directory
cache_dir = tempfile.gettempdir() + "/hf_cache"
os.makedirs(cache_dir, exist_ok=True)
os.environ["TRANSFORMERS_CACHE"] = cache_dir
os.environ["HF_HOME"] = cache_dir

# App and config
VAULT_PATH = "vaults/user_001"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

model = SentenceTransformer("all-MiniLM-L6-v2")
documents = load_documents(VAULT_PATH)
texts, embeddings, metadatas = embed_documents(documents, model)
collection = create_vector_db(texts, embeddings, metadatas)

app = FastAPI()

# Models
class AskRequest(BaseModel):
    question: str

class NoteRequest(BaseModel):
    title: str
    content: str

class GenerationRequest(BaseModel):
    goal: str
    type: str  # script | concept | idea

# Helper to call OpenAI
async def generate_openai_response(prompt: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for a content creator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Error: {str(e)}"

# Endpoints
@app.post("/ask")
async def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "Question cannot be empty."})

    results = query_db(collection, model, question)
    context = "\n\n".join(results["documents"][0]) if results["documents"] else ""

    prompt = f"Context:\n{context}\n\nQuestion:\n{question}"
    answer = await generate_openai_response(prompt)
    return {"answer": answer}

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

@app.post("/generate")
async def generate(req: GenerationRequest):
    goal = req.goal.strip()
    type_ = req.type.strip().lower()

    if not goal or type_ not in ["script", "concept", "idea"]:
        return JSONResponse(status_code=400, content={"error": "Invalid generation request."})

    prompt = f"User's goal: {goal}. Generate a {type_} aligned with this goal using their context notes if needed."
    result = await generate_openai_response(prompt)
    return {"type": type_, "result": result}
