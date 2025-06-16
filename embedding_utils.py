
import os
import chromadb
from chromadb.config import Settings
from sentence_transformers.util import cos_sim

def load_documents(path="vault"):
    docs = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".md") or file.endswith(".txt"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    docs.append({
                        "source": file,
                        "content": f.read()
                    })
    return docs

def chunk_text(text, max_length=500):
    chunks = []
    lines = text.split("\n")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) < max_length:
            chunk += line + "\n"
        else:
            chunks.append(chunk.strip())
            chunk = line + "\n"
    if chunk:
        chunks.append(chunk.strip())
    return chunks

def embed_documents(docs, model):
    texts = []
    metadatas = []
    for doc in docs:
        chunks = chunk_text(doc["content"])
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({"source": doc["source"]})
    embeddings = model.encode(texts)
    return texts, embeddings, metadatas

def create_vector_db(texts, embeddings, metadatas, persist_dir="chromadb"):
    os.makedirs(persist_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir)    if "docs" in client.list_collections():
        client.delete_collection("docs")
    collection = client.create_collection(name="docs")
    for i, (text, emb, meta) in enumerate(zip(texts, embeddings, metadatas)):
        collection.add(documents=[text], embeddings=[emb.tolist()], metadatas=[meta], ids=[f"id_{i}"])
    return collection

def query_db(collection, model, question, top_k=3):
    query_embedding = model.encode([question])[0].tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return results
