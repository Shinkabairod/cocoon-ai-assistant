# app.py - Version corrigée et simplifiée pour commencer

# === IMPORTS ===
import os
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Optional

# === CORRECTION : Import correct de dotenv ===
from dotenv import load_dotenv
load_dotenv()

# === Imports FastAPI ===
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# === Imports pour l'IA (avec gestion d'erreurs) ===
try:
    import openai
    from sentence_transformers import SentenceTransformer
    from supabase import create_client
    AI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Modules IA non disponibles: {e}")
    AI_AVAILABLE = False

# === CONFIGURATION ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Vérifications avec messages clairs
if not SUPABASE_URL:
    print("❌ SUPABASE_URL manquant dans les variables d'environnement")
if not SUPABASE_KEY:
    print("❌ SUPABASE_KEY manquant dans les variables d'environnement")
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY manquant dans les variables d'environnement")

# === INITIALISATION SERVICES (avec protection) ===
app = FastAPI(title="Cocoon AI Assistant", description="API pour assistant créateur")

# Initialisation conditionnelle
supabase_client = None
model = None

if AI_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connecté")
    except Exception as e:
        print(f"❌ Erreur connexion Supabase: {e}")

if AI_AVAILABLE and OPENAI_API_KEY:
    try:
        openai.api_key = OPENAI_API_KEY
        print("✅ OpenAI configuré")
    except Exception as e:
        print(f"❌ Erreur configuration OpenAI: {e}")

# Modèle SentenceTransformer (optionnel au démarrage)
def load_ai_model():
    global model
    if not model and AI_AVAILABLE:
        try:
            cache_dir = os.path.join(tempfile.gettempdir(), "hf_cache")
            os.makedirs(cache_dir, exist_ok=True)
            model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=cache_dir)
            print("✅ Modèle IA chargé")
            return model
        except Exception as e:
            print(f"❌ Erreur chargement modèle: {e}")
            return None
    return model

# === FONCTIONS UTILITAIRES ===
def get_user_vault_path(user_id: str) -> str:
    """Créer le chemin vers le dossier vault de l'utilisateur"""
    base_path = os.path.join(tempfile.gettempdir(), "vaults")
    user_path = os.path.join(base_path, f"user_{user_id}")
    os.makedirs(user_path, exist_ok=True)
    return user_path

def safe_json_response(data, status_code=200):
    """Retourner une réponse JSON sécurisée"""
    try:
        return JSONResponse(content=data, status_code=status_code)
    except Exception as e:
        return JSONResponse(
            content={"error": f"Erreur de sérialisation: {str(e)}"}, 
            status_code=500
        )

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
    """Page d'accueil de l'API"""
    return {
        "message": "🚀 Cocoon AI Assistant API",
        "status": "En ligne",
        "services": {
            "supabase": "✅" if supabase_client else "❌",
            "openai": "✅" if OPENAI_API_KEY else "❌",
            "ai_model": "✅" if model else "⏳ Non chargé"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/ping")
def ping():
    """Test de connexion simple"""
    return {"pong": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/health")
def health_check():
    """Vérification de santé détaillée"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "✅ Running",
            "supabase": "✅ Connected" if supabase_client else "❌ Not connected",
            "openai": "✅ Configured" if OPENAI_API_KEY else "❌ Not configured",
            "ai_model": "✅ Loaded" if model else "⏳ Not loaded"
        },
        "environment": {
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            "temp_dir": tempfile.gettempdir()
        }
    }
    
    # Déterminer le statut global
    if not supabase_client or not OPENAI_API_KEY:
        health_status["status"] = "degraded"
    
    return health_status

# === ROUTES PRINCIPALES ===
@app.post("/profile")
async def save_profile(req: ProfileRequest):
    """Sauvegarder le profil utilisateur et créer le vault Obsidian"""
    try:
        print(f"📝 Sauvegarde profil pour utilisateur: {req.user_id}")
        
        # Créer le dossier utilisateur
        vault_path = get_user_vault_path(req.user_id)
        
        # Sauvegarder les données brutes en JSON
        profile_json_path = os.path.join(vault_path, "user_profile.json")
        with open(profile_json_path, "w", encoding="utf-8") as f:
            json.dump(req.profile_data, f, indent=2, ensure_ascii=False)
        
        # Créer une version markdown simple du profil
        profile_md_path = os.path.join(vault_path, "Profile")
        os.makedirs(profile_md_path, exist_ok=True)
        
        profile_content = f"""# 👤 Profil Utilisateur

## Informations de base
- **Expérience**: {req.profile_data.get('experienceLevel', 'Non défini')}
- **Objectif**: {req.profile_data.get('contentGoal', 'Non défini')}
- **Niche**: {req.profile_data.get('niche', 'Non défini')}
- **Localisation**: {req.profile_data.get('city', '')}, {req.profile_data.get('country', '')}

## Business
- **Type**: {req.profile_data.get('businessType', 'Non défini')}
- **Description**: {req.profile_data.get('businessDescription', 'Non défini')}

## Stratégie
- **Plateformes**: {', '.join(req.profile_data.get('platforms', []))}
- **Types de contenu**: {', '.join(req.profile_data.get('contentTypes', []))}
- **Audience**: {req.profile_data.get('targetGeneration', 'Non défini')}

## Ressources
- **Temps disponible**: {req.profile_data.get('timeAvailable', 'Non défini')}
- **Ressources**: {req.profile_data.get('resources', 'Non défini')}
- **Défis**: {req.profile_data.get('mainChallenges', 'Non défini')}

---
Créé le: {datetime.now().strftime('%Y-%m-%d à %H:%M')}
"""
        
        with open(os.path.join(profile_md_path, "user_profile.md"), "w", encoding="utf-8") as f:
            f.write(profile_content)
        
        # Synchroniser avec Supabase si disponible
        files_created = 2
        if supabase_client:
            try:
                supabase_client.table("vault_files").upsert({
                    "user_id": req.user_id,
                    "path": "Profile/user_profile.md",
                    "content": profile_content,
                    "updated_at": datetime.now().isoformat()
                }).execute()
                print("✅ Profil synchronisé avec Supabase")
            except Exception as e:
                print(f"⚠️ Erreur sync Supabase: {e}")
        
        return {
            "status": "✅ Profil sauvegardé avec succès",
            "message": "Votre profil a été créé dans votre vault Obsidian",
            "vault_path": vault_path,
            "files_created": files_created,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde profil: {e}")
        return JSONResponse(
            status_code=500, 
            content={
                "error": f"Erreur lors de la sauvegarde: {str(e)}",
                "user_id": req.user_id
            }
        )

@app.post("/note")
async def save_note(req: NoteRequest):
    """Sauvegarder une note simple"""
    try:
        vault_path = get_user_vault_path(req.user_id)
        
        # Créer le fichier note
        note_content = f"""# {req.title}

{req.content}

---
Créé le: {datetime.now().strftime('%Y-%m-%d à %H:%M')}
"""
        
        note_path = os.path.join(vault_path, f"{req.title.replace(' ', '_')}.md")
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(note_content)
        
        return {
            "status": "✅ Note sauvegardée",
            "message": f"Note '{req.title}' créée avec succès"
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/ask")
async def ask_simple(req: AskRequest):
    """Version simplifiée de l'assistant IA"""
    try:
        if not OPENAI_API_KEY:
            return {
                "answer": "❌ Service IA non configuré. Veuillez configurer OPENAI_API_KEY.",
                "status": "error"
            }
        
        # Charger le modèle si nécessaire
        current_model = load_ai_model()
        
        # Réponse simple avec OpenAI
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Tu es un assistant pour créateurs de contenu. Réponds en français de manière utile et concise."
                },
                {"role": "user", "content": req.question}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return {
            "answer": response.choices[0].message.content,
            "status": "✅ Réponse générée",
            "model_loaded": current_model is not None
        }
        
    except Exception as e:
        print(f"❌ Erreur IA: {e}")
        return JSONResponse(
            status_code=500, 
            content={
                "error": f"Erreur lors de la génération: {str(e)}",
                "answer": "Désolé, je ne peux pas répondre pour le moment."
            }
        )

@app.get("/user/{user_id}/status")
async def get_user_status(user_id: str):
    """Obtenir le statut d'un utilisateur"""
    try:
        vault_path = get_user_vault_path(user_id)
        
        # Compter les fichiers
        file_count = 0
        files_list = []
        
        if os.path.exists(vault_path):
            for root, dirs, files in os.walk(vault_path):
                for file in files:
                    if file.endswith('.md') or file.endswith('.json'):
                        file_count += 1
                        rel_path = os.path.relpath(os.path.join(root, file), vault_path)
                        files_list.append(rel_path)
        
        # Vérifier si le profil existe
        profile_exists = os.path.exists(os.path.join(vault_path, "Profile/user_profile.md"))
        
        return {
            "user_id": user_id,
            "vault_path": vault_path,
            "profile_exists": profile_exists,
            "total_files": file_count,
            "files": files_list[:10],  # Premières 10 files
            "status": "✅ Statut récupéré",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === GESTION DES ERREURS GLOBALES ===
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Gestionnaire d'erreurs global"""
    print(f"❌ Erreur globale: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erreur interne du serveur",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

# === DÉMARRAGE ===
if __name__ == "__main__":
    print("🚀 Démarrage de Cocoon AI Assistant...")
    print(f"📖 Documentation: http://localhost:8000/docs")
    print(f"❤️ Health check: http://localhost:8000/health")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)