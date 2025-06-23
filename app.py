# app.py - Version optimisée pour Hugging Face Spaces

import os
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Optional

# === GESTION ROBUSTE DES IMPORTS ===
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    print("⚠️ python-dotenv non disponible, utilisation des variables d'environnement système")
    DOTENV_AVAILABLE = False

# === Imports FastAPI (obligatoires) ===
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# === Imports IA (optionnels) ===
OPENAI_AVAILABLE = False
SUPABASE_AVAILABLE = False
SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
    print("✅ OpenAI disponible")
except ImportError:
    print("⚠️ OpenAI non disponible")

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
    print("✅ Supabase disponible")
except ImportError:
    print("⚠️ Supabase non disponible")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    print("✅ SentenceTransformers disponible")
except ImportError:
    print("⚠️ SentenceTransformers non disponible")

# === CONFIGURATION ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# === INITIALISATION APP ===
app = FastAPI(
    title="Cocoon AI Assistant",
    description="API pour assistant créateur de contenu",
    version="1.0.0"
)

# CORS pour permettre les requêtes depuis votre frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, limitez aux domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === INITIALISATION SERVICES ===
supabase_client = None
model = None

if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connecté")
    except Exception as e:
        print(f"❌ Erreur Supabase: {e}")

if OPENAI_AVAILABLE and OPENAI_API_KEY:
    try:
        openai.api_key = OPENAI_API_KEY
        print("✅ OpenAI configuré")
    except Exception as e:
        print(f"❌ Erreur OpenAI: {e}")

# === FONCTIONS UTILITAIRES ===
def get_user_vault_path(user_id: str) -> str:
    """Créer le chemin vers le dossier vault de l'utilisateur"""
    base_path = os.path.join(tempfile.gettempdir(), "vaults")
    user_path = os.path.join(base_path, f"user_{user_id}")
    os.makedirs(user_path, exist_ok=True)
    return user_path

def load_ai_model():
    """Charger le modèle IA de manière paresseuse"""
    global model
    if model is None and SENTENCE_TRANSFORMERS_AVAILABLE:
        try:
            cache_dir = os.path.join(tempfile.gettempdir(), "hf_cache")
            os.makedirs(cache_dir, exist_ok=True)
            model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=cache_dir)
            print("✅ Modèle IA chargé")
        except Exception as e:
            print(f"⚠️ Erreur chargement modèle: {e}")
    return model

def create_simple_obsidian_structure(user_id: str, profile_data: dict):
    """Créer une structure Obsidian simple"""
    vault_path = get_user_vault_path(user_id)
    
    # Créer les dossiers principaux
    folders = [
        "Profile",
        "Content_Strategy", 
        "Goals_and_Metrics",
        "Resources_and_Skills",
        "AI_Context"
    ]
    
    for folder in folders:
        os.makedirs(os.path.join(vault_path, folder), exist_ok=True)
    
    # Créer le profil principal
    profile_content = f"""# 👤 Mon Profil Créateur

## 🎯 Informations de base
- **Expérience**: {profile_data.get('experienceLevel', 'Non défini')}
- **Objectif**: {profile_data.get('contentGoal', 'Non défini')}
- **Niche**: {profile_data.get('niche', 'Non défini')}
- **Localisation**: {profile_data.get('city', '')}, {profile_data.get('country', '')}

## 🏢 Business
- **Type**: {profile_data.get('businessType', 'Non défini')}
- **Description**: {profile_data.get('businessDescription', 'Non défini')}

## 🎯 Stratégie
- **Plateformes**: {', '.join(profile_data.get('platforms', []))}
- **Types de contenu**: {', '.join(profile_data.get('contentTypes', []))}
- **Audience**: {profile_data.get('targetGeneration', 'Non défini')}

## ⏰ Ressources
- **Temps disponible**: {profile_data.get('timeAvailable', 'Non défini')}
- **Ressources**: {profile_data.get('resources', 'Non défini')}
- **Défis**: {profile_data.get('mainChallenges', 'Non défini')}

## 💰 Monétisation
- **Intention**: {profile_data.get('monetizationIntent', 'Non défini')}

---
**Créé le**: {datetime.now().strftime('%Y-%m-%d à %H:%M')}
"""
    
    with open(os.path.join(vault_path, "Profile", "user_profile.md"), "w", encoding="utf-8") as f:
        f.write(profile_content)
    
    # Créer un dashboard simple
    dashboard_content = f"""# 🏠 Mon Dashboard Créateur

## 📊 Vue d'ensemble
- **Profil**: {profile_data.get('experienceLevel', 'Non défini')}
- **Objectif**: {profile_data.get('contentGoal', 'Non défini')}
- **Niche**: {profile_data.get('niche', 'Non défini')}

## 🎯 Navigation rapide
- [[Profile/user_profile|👤 Mon Profil]]
- [[Content_Strategy/content_goals|🎯 Mes Objectifs]]
- [[Goals_and_Metrics/success_metrics|📊 Mes Métriques]]

## 📈 Plateformes actives
{chr(10).join([f'- **{platform}**' for platform in profile_data.get('platforms', [])])}

---
**Dernière mise à jour**: {datetime.now().strftime('%Y-%m-%d à %H:%M')}
"""
    
    with open(os.path.join(vault_path, "Dashboard.md"), "w", encoding="utf-8") as f:
        f.write(dashboard_content)
    
    return vault_path

# === MODÈLES DE DONNÉES ===
class ProfileRequest(BaseModel):
    user_id: str
    profile_data: dict

class AskRequest(BaseModel):
    user_id: str
    question: str

class NoteRequest(BaseModel):
    user_id: str
    title: str
    content: str

# === ROUTES DE BASE ===
@app.get("/")
def root():
    """Page d'accueil avec statut des services"""
    return {
        "message": "🚀 Cocoon AI Assistant API",
        "status": "En ligne",
        "version": "1.0.0",
        "services": {
            "supabase": "✅" if supabase_client else "❌",
            "openai": "✅" if OPENAI_AVAILABLE and OPENAI_API_KEY else "❌",
            "ai_model": "✅" if model else "⏳ Non chargé",
            "sentence_transformers": "✅" if SENTENCE_TRANSFORMERS_AVAILABLE else "❌"
        },
        "environment": {
            "platform": "Hugging Face Spaces",
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/ping")
def ping():
    """Test de connexion simple"""
    return {"pong": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/health")
def health_check():
    """Vérification de santé complète"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "✅ Running",
            "supabase": "✅ Connected" if supabase_client else "❌ Not available",
            "openai": "✅ Available" if OPENAI_AVAILABLE and OPENAI_API_KEY else "❌ Not available",
            "ai_model": "✅ Ready" if model else "⏳ Not loaded"
        },
        "dependencies": {
            "supabase_lib": "✅" if SUPABASE_AVAILABLE else "❌",
            "openai_lib": "✅" if OPENAI_AVAILABLE else "❌", 
            "transformers_lib": "✅" if SENTENCE_TRANSFORMERS_AVAILABLE else "❌"
        }
    }
    
    # Déterminer le statut global
    critical_services = [OPENAI_AVAILABLE, SUPABASE_AVAILABLE]
    if not any(critical_services):
        health_status["status"] = "degraded"
        health_status["message"] = "Services IA non disponibles"
    
    return health_status

# === ROUTES PRINCIPALES ===
@app.post("/profile")
async def save_profile(req: ProfileRequest):
    """Sauvegarder le profil utilisateur"""
    try:
        print(f"📝 Sauvegarde profil pour: {req.user_id}")
        
        # Créer la structure Obsidian
        vault_path = create_simple_obsidian_structure(req.user_id, req.profile_data)
        
        # Sauvegarder les données brutes
        with open(os.path.join(vault_path, "user_profile.json"), "w", encoding="utf-8") as f:
            json.dump(req.profile_data, f, indent=2, ensure_ascii=False)
        
        # Synchroniser avec Supabase si disponible
        sync_status = "disabled"
        if supabase_client:
            try:
                supabase_client.table("vault_files").upsert({
                    "user_id": req.user_id,
                    "path": "Profile/user_profile.md",
                    "content": "Profil créé",
                    "updated_at": datetime.now().isoformat()
                }).execute()
                sync_status = "synced"
            except Exception as e:
                print(f"⚠️ Erreur sync Supabase: {e}")
                sync_status = "failed"
        
        return {
            "status": "✅ Profil sauvegardé avec succès",
            "message": "Votre vault Obsidian a été créé",
            "vault_path": vault_path,
            "sync_status": sync_status,
            "files_created": 3,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur sauvegarde: {str(e)}")

@app.post("/ask")
async def ask_ai(req: AskRequest):
    """Poser une question à l'IA"""
    try:
        if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
            return {
                "answer": "❌ Service IA non disponible. OpenAI n'est pas configuré.",
                "status": "error",
                "suggestion": "Configurez OPENAI_API_KEY dans les variables d'environnement"
            }
        
        # Charger le modèle si possible
        current_model = load_ai_model()
        
        # Réponse simple avec OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Modèle moins cher
            messages=[
                {
                    "role": "system", 
                    "content": "Tu es un assistant expert pour créateurs de contenu. Réponds en français de manière utile, concise et actionnable."
                },
                {"role": "user", "content": req.question}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return {
            "answer": response.choices[0].message.content,
            "status": "✅ Réponse générée",
            "model_used": "gpt-4o-mini",
            "has_context": current_model is not None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Erreur IA: {e}")
        return {
            "answer": "Désolé, je ne peux pas répondre pour le moment. Erreur technique.",
            "status": "error",
            "error_details": str(e)
        }

@app.post("/note")
async def save_note(req: NoteRequest):
    """Sauvegarder une note"""
    try:
        vault_path = get_user_vault_path(req.user_id)
        
        note_content = f"""# {req.title}

{req.content}

---
**Créé le**: {datetime.now().strftime('%Y-%m-%d à %H:%M')}
"""
        
        safe_filename = req.title.replace(" ", "_").replace("/", "_")
        note_path = os.path.join(vault_path, f"{safe_filename}.md")
        
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(note_content)
        
        return {
            "status": "✅ Note sauvegardée",
            "filename": f"{safe_filename}.md",
            "message": f"Note '{req.title}' créée avec succès"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{user_id}/status")
async def get_user_status(user_id: str):
    """Obtenir le statut d'un utilisateur"""
    try:
        vault_path = get_user_vault_path(user_id)
        
        # Compter les fichiers
        total_files = 0
        markdown_files = []
        
        if os.path.exists(vault_path):
            for root, dirs, files in os.walk(vault_path):
                for file in files:
                    if file.endswith(('.md', '.json')):
                        total_files += 1
                        if file.endswith('.md'):
                            rel_path = os.path.relpath(os.path.join(root, file), vault_path)
                            markdown_files.append(rel_path)
        
        profile_exists = os.path.exists(os.path.join(vault_path, "Profile", "user_profile.md"))
        
        return {
            "user_id": user_id,
            "vault_exists": os.path.exists(vault_path),
            "profile_exists": profile_exists,
            "total_files": total_files,
            "markdown_files": markdown_files[:10],  # Limiter l'affichage
            "vault_path": vault_path,
            "status": "✅ Utilisateur trouvé" if profile_exists else "⚠️ Profil non créé",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{user_id}/vault_structure")
async def get_vault_structure(user_id: str):
    """Récupérer la structure du vault utilisateur"""
    try:
        vault_path = get_user_vault_path(user_id)
        
        if not os.path.exists(vault_path):
            return {
                "error": "Vault non trouvé",
                "message": "Créez d'abord votre profil",
                "user_id": user_id
            }
        
        structure = {}
        for root, dirs, files in os.walk(vault_path):
            rel_path = os.path.relpath(root, vault_path)
            if rel_path == ".":
                rel_path = "root"
            
            structure[rel_path] = {
                "folders": dirs,
                "markdown_files": [f for f in files if f.endswith('.md')],
                "other_files": [f for f in files if not f.endswith('.md')],
                "total_files": len(files)
            }
        
        return {
            "user_id": user_id,
            "structure": structure,
            "total_folders": len(structure),
            "vault_path": vault_path,
            "status": "✅ Structure récupérée"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === ROUTES DE TEST ET DEBUG ===
@app.get("/test")
async def test_all_services():
    """Tester tous les services"""
    tests = {
        "timestamp": datetime.now().isoformat(),
        "results": {}
    }
    
    # Test création vault
    try:
        test_path = get_user_vault_path("test_user")
        tests["results"]["vault_creation"] = "✅ OK" if os.path.exists(test_path) else "❌ Failed"
    except Exception as e:
        tests["results"]["vault_creation"] = f"❌ Error: {e}"
    
    # Test OpenAI
    if OPENAI_AVAILABLE and OPENAI_API_KEY:
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            tests["results"]["openai"] = "✅ OK"
        except Exception as e:
            tests["results"]["openai"] = f"❌ Error: {e}"
    else:
        tests["results"]["openai"] = "❌ Not configured"
    
    # Test Supabase
    if supabase_client:
        try:
            # Test simple de connexion
            result = supabase_client.table("vault_files").select("id").limit(1).execute()
            tests["results"]["supabase"] = "✅ OK"
        except Exception as e:
            tests["results"]["supabase"] = f"❌ Error: {e}"
    else:
        tests["results"]["supabase"] = "❌ Not configured"
    
    return tests

# === GESTION GLOBALE DES ERREURS ===
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"❌ Erreur globale: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erreur interne du serveur",
            "message": str(exc),
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )

# === DÉMARRAGE ===
if __name__ == "__main__":
    print("🚀 Démarrage Cocoon AI Assistant pour Hugging Face Spaces...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)  # Port 7860 pour HF Spaces