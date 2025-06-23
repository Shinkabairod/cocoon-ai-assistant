# embedding_utils.py - Version simplifiée et robuste

import os
import tempfile
from typing import List, Dict, Tuple, Optional

def load_documents(path: str = "vaults/user_001") -> List[Dict]:
    """Charger les documents depuis un dossier"""
    docs = []
    
    if not os.path.exists(path):
        print(f"⚠️ Chemin {path} n'existe pas")
        return docs
    
    try:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith((".md", ".txt")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            docs.append({
                                "source": file,
                                "content": content,
                                "path": file_path
                            })
                    except Exception as e:
                        print(f"⚠️ Erreur lecture fichier {file}: {e}")
                        continue
        
        print(f"✅ {len(docs)} documents chargés depuis {path}")
        return docs
        
    except Exception as e:
        print(f"❌ Erreur chargement documents: {e}")
        return []

def chunk_text(text: str, max_length: int = 500) -> List[str]:
    """Découper le texte en chunks plus petits"""
    if not text or len(text) <= max_length:
        return [text] if text else []
    
    chunks = []
    lines = text.split("\n")
    current_chunk = ""
    
    for line in lines:
        # Si ajouter cette ligne dépasse la limite
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = line + "\n"
            else:
                # Ligne trop longue, la découper par mots
                words = line.split(" ")
                for word in words:
                    if len(current_chunk) + len(word) + 1 > max_length:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = word + " "
                    else:
                        current_chunk += word + " "
        else:
            current_chunk += line + "\n"
    
    # Ajouter le dernier chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def embed_documents(docs: List[Dict], model=None) -> Tuple[List[str], Optional[List], List[Dict]]:
    """Créer des embeddings pour les documents"""
    texts = []
    metadatas = []
    embeddings = None
    
    try:
        # Traiter chaque document
        for doc in docs:
            # Découper le contenu en chunks
            chunks = chunk_text(doc["content"])
            
            for i, chunk in enumerate(chunks):
                if chunk.strip():  # Ignorer les chunks vides
                    texts.append(chunk)
                    metadatas.append({
                        "source": doc["source"],
                        "chunk_id": i,
                        "total_chunks": len(chunks)
                    })
        
        # Créer les embeddings si le modèle est disponible
        if model is not None:
            try:
                embeddings = model.encode(texts)
                print(f"✅ Embeddings créés pour {len(texts)} chunks")
            except Exception as e:
                print(f"⚠️ Erreur création embeddings: {e}")
                embeddings = None
        else:
            print("⚠️ Modèle non disponible, pas d'embeddings créés")
        
        return texts, embeddings, metadatas
        
    except Exception as e:
        print(f"❌ Erreur embedding documents: {e}")
        return [], None, []

def create_vector_db(texts: List[str], embeddings=None, metadatas: List[Dict] = None):
    """Créer une base de données vectorielle simple"""
    try:
        # Si chromadb n'est pas disponible, créer une structure simple
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Utiliser un répertoire temporaire
            persist_dir = os.path.join(tempfile.gettempdir(), "chromadb")
            os.makedirs(persist_dir, exist_ok=True)
            
            client = chromadb.PersistentClient(path=persist_dir)
            
            # Supprimer la collection si elle existe
            try:
                client.delete_collection("docs")
            except:
                pass
            
            collection = client.create_collection(name="docs")
            
            # Ajouter les documents
            for i, (text, meta) in enumerate(zip(texts, metadatas or [])):
                embedding = embeddings[i].tolist() if embeddings is not None else None
                collection.add(
                    documents=[text],
                    embeddings=[embedding] if embedding else None,
                    metadatas=[meta or {}],
                    ids=[f"doc_{i}"]
                )
            
            print(f"✅ Base vectorielle créée avec {len(texts)} documents")
            return collection
            
        except ImportError:
            print("⚠️ ChromaDB non disponible, utilisation d'une structure simple")
            # Structure simple de fallback
            return {
                "texts": texts,
                "embeddings": embeddings,
                "metadatas": metadatas or [],
                "type": "simple"
            }
            
    except Exception as e:
        print(f"❌ Erreur création base vectorielle: {e}")
        return None

def query_db(collection, model=None, question: str = "", top_k: int = 3) -> Dict:
    """Interroger la base de données vectorielle"""
    try:
        if collection is None:
            return {"documents": [], "metadatas": []}
        
        # Si c'est une vraie collection ChromaDB
        if hasattr(collection, 'query'):
            if model is not None:
                try:
                    query_embedding = model.encode([question])[0].tolist()
                    results = collection.query(
                        query_embeddings=[query_embedding], 
                        n_results=min(top_k, collection.count() if hasattr(collection, 'count') else top_k)
                    )
                    return results
                except Exception as e:
                    print(f"⚠️ Erreur requête avec embedding: {e}")
            
            # Fallback: recherche textuelle simple
            try:
                results = collection.query(
                    query_texts=[question],
                    n_results=min(top_k, 10)
                )
                return results
            except Exception as e:
                print(f"⚠️ Erreur requête textuelle: {e}")
        
        # Si c'est notre structure simple
        elif isinstance(collection, dict) and collection.get("type") == "simple":
            # Recherche textuelle basique
            texts = collection.get("texts", [])
            metadatas = collection.get("metadatas", [])
            
            # Recherche par mots-clés
            question_words = question.lower().split()
            scored_docs = []
            
            for i, text in enumerate(texts):
                text_lower = text.lower()
                score = sum(1 for word in question_words if word in text_lower)
                if score > 0:
                    scored_docs.append((score, i, text))
            
            # Trier par score et prendre les meilleurs
            scored_docs.sort(reverse=True)
            top_docs = scored_docs[:top_k]
            
            return {
                "documents": [[doc[2] for doc in top_docs]],
                "metadatas": [[metadatas[doc[1]] if doc[1] < len(metadatas) else {} for doc in top_docs]]
            }
        
        return {"documents": [], "metadatas": []}
        
    except Exception as e:
        print(f"❌ Erreur requête base vectorielle: {e}")
        return {"documents": [], "metadatas": []}