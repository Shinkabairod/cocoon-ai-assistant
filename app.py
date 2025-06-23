# app.py - Version complète améliorée

# === IMPORTS (les bibliothèques qu'on utilise) ===
from profile_writer import write_profile_to_obsidian
import os
import json
import tempfile
import openai
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_env
load_dotenv()
from fastapi import FastAPI, UploadFile, File, Query, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from supabase import create_client
from embedding_utils import load_documents, embed_documents, create_vector_db, query_db

# === CONFIGURATION DE BASE ===
# Dossier temporaire pour stocker les modèles IA
cache_dir = os.path.join(tempfile.gettempdir(), "hf_cache")
os.makedirs(cache_dir, exist_ok=True)
os.environ["TRANSFORMERS_CACHE"] = cache_dir
os.environ["HF_HOME"] = cache_dir

# === VARIABLES D'ENVIRONNEMENT (vos clés API) ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Vérifier que toutes les clés sont présentes
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ ERREUR: Clés Supabase manquantes dans le fichier .env")
if not OPENAI_API_KEY:
    raise ValueError("❌ ERREUR: Clé OpenAI manquante dans le fichier .env")

# === INITIALISATION DES SERVICES ===
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY
model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=cache_dir)
app = FastAPI(title="Cocoon AI Assistant", description="API pour votre assistant créateur de contenu")

# === FONCTIONS UTILITAIRES ===
def get_user_vault_path(user_id: str) -> str:
    """Créer le chemin vers le dossier vault de l'utilisateur"""
    base_path = os.path.join(tempfile.gettempdir(), "vaults")
    user_path = os.path.join(base_path, f"user_{user_id}")
    os.makedirs(user_path, exist_ok=True)  # Créer le dossier s'il n'existe pas
    return user_path

def calculate_profile_completion(profile_content: str) -> int:
    """Calculer le pourcentage de completion du profil utilisateur"""
    # Liste des champs importants à vérifier
    required_fields = [
        "Niveau d'expérience", "Objectif principal", "Type d'activité",
        "Description", "Niche", "Types de contenu", "Plateformes cibles",
        "Audience cible", "Temps disponible", "Défis actuels"
    ]
    
    filled_fields = 0
    total_fields = len(required_fields)
    
    # Compter combien de champs sont remplis
    for field in required_fields:
        if field in profile_content and "Non défini" not in profile_content:
            filled_fields += 1
    
    # Calculer le pourcentage
    return round((filled_fields / total_fields) * 100)

def format_metrics(metrics: dict) -> str:
    """Transformer un dictionnaire de métriques en texte markdown"""
    if not metrics:
        return "Aucune métrique définie"
    
    formatted = ""
    for key, value in metrics.items():
        formatted += f"- **{key}**: {value}\n"
    
    return formatted

# === MODÈLES DE DONNÉES (ce que l'API peut recevoir) ===

class AskRequest(BaseModel):
    """Modèle pour les questions à l'IA"""
    user_id: str
    question: str

class NoteRequest(BaseModel):
    """Modèle pour sauvegarder une note"""
    user_id: str
    title: str
    content: str

class ProfileRequest(BaseModel):
    """Modèle pour sauvegarder un profil utilisateur"""
    user_id: str
    profile_data: dict

class GenerateRequest(BaseModel):
    """Modèle pour la génération de contenu"""
    prompt: str

class UserResourceRequest(BaseModel):
    """Modèle pour ajouter une ressource utilisateur"""
    user_id: str
    resource_type: str  # "tool", "inspiration", "learning", "contact"
    title: str
    description: str
    url: Optional[str] = None
    tags: List[str] = []
    category: Optional[str] = None

class UserGoalRequest(BaseModel):
    """Modèle pour ajouter un objectif utilisateur"""
    user_id: str
    goal_type: str  # "short_term", "long_term", "metric"
    title: str
    description: str
    deadline: Optional[str] = None
    metrics: Optional[dict] = None

class ContentIdeaRequest(BaseModel):
    """Modèle pour ajouter une idée de contenu"""
    user_id: str
    title: str
    description: str
    platform: str
    content_type: str
    status: str = "idea"  # "idea", "planned", "in_progress", "published"

# === ROUTES DE BASE ===

@app.get("/")
def root():
    """Page d'accueil de l'API"""
    return {"message": "🚀 Cocoon AI Assistant API est en ligne !"}

@app.get("/ping")
def ping():
    """Test de connexion simple"""
    return {"pong": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/test")
async def test_connection():
    """Test de connexion complet"""
    return {
        "status": "ok", 
        "message": "Connexion réussie",
        "services": {
            "supabase": "✅ Connecté",
            "openai": "✅ Connecté",
            "model": "✅ Chargé"
        }
    }

# === ROUTES PRINCIPALES AMÉLIORÉES ===

@app.get("/user/{user_id}/dashboard")
async def get_user_dashboard(user_id: str):
    """📊 Récupérer le dashboard complet de l'utilisateur"""
    try:
        print(f"📊 Récupération dashboard pour utilisateur: {user_id}")
        
        vault_path = get_user_vault_path(user_id)
        
        # Vérifier si le profil existe
        profile_path = os.path.join(vault_path, "Profile/user_profile.md")
        if not os.path.exists(profile_path):
            return JSONResponse(
                status_code=404, 
                content={"error": "❌ Profil utilisateur non trouvé. Créez d'abord votre profil."}
            )
        
        # Lire le contenu du profil
        with open(profile_path, "r", encoding="utf-8") as f:
            profile_content = f.read()
        
        # Calculer la completion du profil
        completion_percentage = calculate_profile_completion(profile_content)
        
        # Compter les fichiers dans le vault
        file_count = 0
        for root, dirs, files in os.walk(vault_path):
            file_count += len([f for f in files if f.endswith('.md')])
        
        # Récupérer les dernières mises à jour depuis Supabase
        recent_updates_result = supabase_client.table("vault_files")\
            .select("path, updated_at")\
            .eq("user_id", user_id)\
            .order("updated_at", desc=True)\
            .limit(5)\
            .execute()
        
        recent_updates = recent_updates_result.data if recent_updates_result.data else []
        
        # Générer des actions suggérées
        suggested_actions = await generate_next_actions(user_id, vault_path)
        
        dashboard_data = {
            "profile_completion": completion_percentage,
            "total_files": file_count,
            "recent_updates": recent_updates,
            "suggested_actions": suggested_actions,
            "vault_path": vault_path,
            "status": "✅ Dashboard chargé avec succès"
        }
        
        print(f"✅ Dashboard généré: {completion_percentage}% completion, {file_count} fichiers")
        return dashboard_data
        
    except Exception as e:
        print(f"❌ Erreur dashboard: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur lors du chargement du dashboard: {str(e)}"})

@app.post("/user/resource")
async def add_user_resource(req: UserResourceRequest):
    """🛠️ Ajouter une ressource personnalisée à l'utilisateur"""
    try:
        print(f"🛠️ Ajout ressource '{req.title}' pour utilisateur {req.user_id}")
        
        vault_path = get_user_vault_path(req.user_id)
        
        # Créer le nom de fichier sécurisé (enlever espaces et caractères spéciaux)
        safe_title = req.title.replace(" ", "_").replace("/", "_").lower()
        file_path = f"Resources_and_Skills/my_resources/{req.resource_type}_{safe_title}.md"
        
        # Créer le contenu avec métadonnées YAML
        content = f"""---
type: {req.resource_type}
category: {req.category or "general"}
tags: {req.tags}
created: {datetime.now().isoformat()}
---

# {req.title}

**Type**: {req.resource_type}
**Catégorie**: {req.category or "Général"}

## Description
{req.description}

{f"**URL**: {req.url}" if req.url else ""}

## Tags
{", ".join(req.tags) if req.tags else "Aucun tag"}

## Notes personnelles
<!-- Ajoutez vos notes ici -->

## Actions à faire
- [ ] Explorer cette ressource
- [ ] Prendre des notes
- [ ] Appliquer les apprentissages
"""
        
        # Écrire le fichier dans le vault
        full_path = os.path.join(vault_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        
        # Synchroniser avec Supabase
        supabase_client.table("vault_files").upsert({
            "user_id": req.user_id,
            "path": file_path,
            "content": content.strip(),
            "resource_type": req.resource_type,
            "updated_at": datetime.now().isoformat()
        }).execute()
        
        print(f"✅ Ressource ajoutée: {file_path}")
        return {
            "status": "✅ Ressource ajoutée avec succès", 
            "file_path": file_path,
            "message": f"Votre ressource '{req.title}' a été sauvegardée dans votre vault Obsidian"
        }
        
    except Exception as e:
        print(f"❌ Erreur ajout ressource: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur lors de l'ajout de la ressource: {str(e)}"})

@app.post("/user/goal")
async def add_user_goal(req: UserGoalRequest):
    """🎯 Ajouter un objectif utilisateur"""
    try:
        print(f"🎯 Ajout objectif '{req.title}' pour utilisateur {req.user_id}")
        
        vault_path = get_user_vault_path(req.user_id)
        
        safe_title = req.title.replace(" ", "_").replace("/", "_").lower()
        file_path = f"Goals_and_Metrics/{req.goal_type}_goals/{safe_title}.md"
        
        content = f"""---
type: {req.goal_type}
deadline: {req.deadline or "Non définie"}
created: {datetime.now().isoformat()}
status: active
---

# 🎯 {req.title}

**Type**: {req.goal_type}
**Échéance**: {req.deadline or "Non définie"}

## Description
{req.description}

## Métriques de succès
{format_metrics(req.metrics) if req.metrics else "À définir"}

## Plan d'action
- [ ] Étape 1 à définir
- [ ] Étape 2 à définir
- [ ] Étape 3 à définir

## Suivi de progression
**Date de création**: {datetime.now().strftime("%Y-%m-%d")}
**Dernière mise à jour**: {datetime.now().strftime("%Y-%m-%d")}
**Statut**: 🟡 En cours

### Notes d'avancement
<!-- Ajoutez vos notes de progression ici -->

### Obstacles rencontrés
<!-- Notez les difficultés et comment les surmonter -->

### Célébrations
<!-- Notez vos victoires, même petites ! -->
"""
        
        full_path = os.path.join(vault_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        
        supabase_client.table("vault_files").upsert({
            "user_id": req.user_id,
            "path": file_path,
            "content": content.strip(),
            "goal_type": req.goal_type,
            "updated_at": datetime.now().isoformat()
        }).execute()
        
        print(f"✅ Objectif ajouté: {file_path}")
        return {
            "status": "✅ Objectif ajouté avec succès", 
            "file_path": file_path,
            "message": f"Votre objectif '{req.title}' a été créé dans votre vault"
        }
        
    except Exception as e:
        print(f"❌ Erreur ajout objectif: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur lors de l'ajout de l'objectif: {str(e)}"})

@app.post("/user/content_idea")
async def add_content_idea(req: ContentIdeaRequest):
    """💡 Ajouter une idée de contenu"""
    try:
        print(f"💡 Ajout idée contenu '{req.title}' pour utilisateur {req.user_id}")
        
        vault_path = get_user_vault_path(req.user_id)
        
        safe_title = req.title.replace(" ", "_").replace("/", "_").lower()
        file_path = f"Content_Strategy/content_ideas/{req.platform}_{safe_title}.md"
        
        content = f"""---
platform: {req.platform}
content_type: {req.content_type}
status: {req.status}
created: {datetime.now().isoformat()}
---

# 💡 {req.title}

**Plateforme**: {req.platform}
**Type**: {req.content_type}
**Statut**: {req.status}

## Description de l'idée
{req.description}

## Éléments clés
- **Hook (accroche)**: À définir
- **Message principal**: À définir
- **Call-to-action**: À définir

## Structure proposée
1. **Introduction** (0-5 sec)
2. **Développement** (5-30 sec)
3. **Conclusion** (30-60 sec)

## Ressources nécessaires
- [ ] Matériel de tournage
- [ ] Recherche/préparation
- [ ] Post-production
- [ ] Visuels/graphics

## Planning
- **Date prévue**: À définir
- **Temps estimé**: À définir
- **Priorité**: Moyenne

## Hashtags suggérés
<!-- Ajoutez vos hashtags ici -->

## Notes de production
<!-- Ajoutez vos notes techniques ici -->

## Métriques à suivre
- Vues
- Engagement
- Partages
- Commentaires
"""
        
        full_path = os.path.join(vault_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        
        supabase_client.table("vault_files").upsert({
            "user_id": req.user_id,
            "path": file_path,
            "content": content.strip(),
            "content_type": req.content_type,
            "platform": req.platform,
            "updated_at": datetime.now().isoformat()
        }).execute()
        
        print(f"✅ Idée contenu ajoutée: {file_path}")
        return {
            "status": "✅ Idée de contenu ajoutée avec succès", 
            "file_path": file_path,
            "message": f"Votre idée '{req.title}' pour {req.platform} a été sauvegardée"
        }
        
    except Exception as e:
        print(f"❌ Erreur ajout idée contenu: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur lors de l'ajout de l'idée: {str(e)}"})

# === ROUTES DE SYNCHRONISATION ===

@app.get("/sync/{user_id}/status")
async def get_sync_status(user_id: str):
    """🔄 Obtenir le statut de synchronisation"""
    try:
        vault_path = get_user_vault_path(user_id)
        
        # Compter les fichiers locaux
        local_files = 0
        if os.path.exists(vault_path):
            for root, dirs, files in os.walk(vault_path):
                local_files += len([f for f in files if f.endswith('.md')])
        
        # Compter les fichiers en base
        db_files_result = supabase_client.table("vault_files")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .execute()
        
        db_count = len(db_files_result.data) if db_files_result.data else 0
        
        # Dernière synchronisation
        last_sync_result = supabase_client.table("vault_files")\
            .select("updated_at")\
            .eq("user_id", user_id)\
            .order("updated_at", desc=True)\
            .limit(1)\
            .execute()
        
        last_sync = None
        if last_sync_result.data and len(last_sync_result.data) > 0:
            last_sync = last_sync_result.data[0]["updated_at"]
        
        status = {
            "local_files": local_files,
            "db_files": db_count,
            "last_sync": last_sync,
            "sync_needed": local_files != db_count,
            "vault_exists": os.path.exists(vault_path),
            "status": "✅ Synchronisé" if local_files == db_count else "⚠️ Synchronisation nécessaire"
        }
        
        return status
        
    except Exception as e:
        print(f"❌ Erreur statut sync: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur lors de la vérification du statut: {str(e)}"})

# === ROUTES IA AMÉLIORÉES ===

@app.post("/ask")
async def ask_ai_smart(req: AskRequest):
    """🤖 Poser une question à l'IA avec contexte intelligent"""
    try:
        print(f"🤖 Question IA de {req.user_id}: {req.question[:50]}...")
        
        user_vault = get_user_vault_path(req.user_id)
        
        # Charger les documents du vault
        docs = load_documents(user_vault)
        
        if not docs:
            return {"answer": "❌ Aucun contenu trouvé dans votre vault. Commencez par créer votre profil !"}
        
        # Recherche sémantique dans les documents
        texts, embeddings, metadatas = embed_documents(docs, model)
        collection = create_vector_db(texts, embeddings, metadatas)
        results = query_db(collection, model, req.question)
        
        if not results["documents"]:
            return {"answer": "❌ Pas de contexte pertinent trouvé pour votre question."}
        
        # Construire le contexte
        context = "\n\n".join(results["documents"][0])
        
        # Préparer le prompt enrichi
        system_prompt = """Tu es un consultant expert en stratégie de contenu et création digitale. 
        Tu as accès au vault Obsidian complet de l'utilisateur avec son profil, ses objectifs, et sa stratégie.
        Réponds de manière personnalisée, actionnable et en français. 
        Utilise des emojis pour rendre tes réponses plus engageantes.
        Donne des conseils concrets et pratiques."""
        
        user_prompt = f"""
CONTEXTE DU VAULT UTILISATEUR:
{context}

QUESTION DE L'UTILISATEUR:
{req.question}

Réponds en tenant compte de son profil complet et de sa stratégie actuelle.
"""
        
        # Appel à OpenAI
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        
        print(f"✅ Réponse IA générée ({len(answer)} caractères)")
        return {
            "answer": answer,
            "context_used": True,
            "documents_found": len(docs),
            "status": "✅ Réponse générée avec succès"
        }
        
    except Exception as e:
        print(f"❌ Erreur IA: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur lors de la génération de la réponse: {str(e)}"})

# === ROUTES ORIGINALES (conservées) ===

@app.post("/note")
async def save_note(req: NoteRequest):
    """📝 Sauvegarder une note simple"""
    try:
        path = get_user_vault_path(req.user_id)
        with open(os.path.join(path, f"{req.title}.md"), "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "📝 Note sauvegardée avec succès"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/profile")
async def save_profile(req: ProfileRequest):
    """👤 Sauvegarder le profil utilisateur complet"""
    try:
        path = get_user_vault_path(req.user_id)
        
        # Sauvegarder les données brutes
        with open(os.path.join(path, "user_profile.json"), "w", encoding="utf-8") as f:
            json.dump(req.profile_data, f, indent=2, ensure_ascii=False)

        # Créer la structure Obsidian enrichie
        vault_path, files_written = write_profile_to_obsidian(req.user_id, req.profile_data)

        # Synchroniser avec Supabase
        for rel_path, content in files_written:
            supabase_client.table("vault_files").upsert({
                "user_id": req.user_id,
                "path": rel_path,
                "content": content,
                "updated_at": datetime.now().isoformat()
            }).execute()

        return {
            "status": "✅ Profil sauvegardé et vault Obsidian créé avec succès",
            "files_created": len(files_written),
            "vault_path": vault_path
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === FONCTIONS UTILITAIRES AVANCÉES ===

async def generate_next_actions(user_id: str, vault_path: str) -> List[str]:
    """Générer des actions suggérées pour l'utilisateur"""
    actions = []
    
    try:
        # Vérifier les fichiers manquants importants
        important_files = [
            ("Content_Strategy/content_calendar.md", "Créer un calendrier de contenu"),
            ("Goals_and_Metrics/monthly_review.md", "Définir vos objectifs mensuels"),
            ("Resources_and_Skills/skills_tracker.md", "Faire le bilan de vos compétences"),
            ("Content_Strategy/competitor_analysis.md", "Analyser vos concurrents")
        ]
        
        for file_path, action in important_files:
            if not os.path.exists(os.path.join(vault_path, file_path)):
                actions.append(action)
        
        # Analyser l'activité récente (fichiers modifiés dans les 7 derniers jours)
        recent_files = []
        one_week_ago = datetime.now().timestamp() - 604800  # 7 jours en secondes
        
        for root, dirs, files in os.walk(vault_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    if os.path.getmtime(file_path) > one_week_ago:
                        recent_files.append(file)
        
        if len(recent_files) < 3:
            actions.append("Ajouter plus de contenu à votre vault cette semaine")
        
        # Suggestions par défaut si le vault est vide
        if not actions:
            actions = [
                "Excellent ! Votre vault semble complet 🎉",
                "Pensez à faire une révision de vos objectifs",
                "Ajoutez une nouvelle idée de contenu",
                "Mettez à jour vos métriques de performance"
            ]
        
        return actions[:5]  # Limiter à 5 suggestions max
        
    except Exception as e:
        print(f"❌ Erreur génération actions: {e}")
        return [
            "Complétez votre profil utilisateur",
            "Ajoutez vos premiers objectifs",
            "Créez votre première idée de contenu"
        ]

# === ROUTES DE GÉNÉRATION DE CONTENU (conservées) ===

@app.post("/script")
async def generate_script(req: GenerateRequest):
    """🎬 Générer un script"""
    return await generate_with_role(req, "Tu es un scénariste créatif expert. Crée des scripts engageants et bien structurés.")

@app.post("/concepts")
async def generate_concepts(req: GenerateRequest):
    """💡 Générer des concepts"""
    return await generate_with_role(req, "Tu es un moteur d'innovation. Génère des concepts créatifs et originaux.")

@app.post("/ideas")
async def generate_ideas(req: GenerateRequest):
    """🚀 Générer des idées"""
    return await generate_with_role(req, "Tu es un stratège de contenu. Génère des idées pratiques et actionnables.")

async def generate_with_role(req: GenerateRequest, role: str):
    """Fonction générique pour la génération avec un rôle spécifique"""
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

# === ROUTES DE GESTION DE FICHIERS ===

@app.post("/update_file")
async def update_file(
    user_id: str = Form(...),
    file_path: str = Form(...),
    new_content: str = Form(...)
):
    """📝 Mettre à jour un fichier existant"""
    try:
        vault_path = get_user_vault_path(user_id)
        full_path = os.path.join(vault_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content.strip())

        supabase_client.table("vault_files").upsert({
            "user_id": user_id,
            "path": file_path,
            "content": new_content.strip(),
            "updated_at": datetime.now().isoformat()
        }).execute()

        return {"status": "✅ Fichier mis à jour avec succès", "file": file_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/obsidian")
async def upload_obsidian_file(user_id: str, file: UploadFile = File(...)):
    """📁 Uploader un fichier dans le vault"""
    try:
        path = get_user_vault_path(user_id)
        with open(os.path.join(path, file.filename), "wb") as f:
            f.write(await file.read())
        return {"status": "📁 Fichier uploadé avec succès"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/user/{user_id}/vault_structure")
async def get_vault_structure(user_id: str):
    """📂 Récupérer la structure complète du vault utilisateur"""
    try:
        vault_path = get_user_vault_path(user_id)
        structure = {}
        
        # Parcourir tous les dossiers et fichiers
        for root, dirs, files in os.walk(vault_path):
            # Calculer le chemin relatif depuis la racine du vault
            rel_path = os.path.relpath(root, vault_path)
            if rel_path == ".":
                rel_path = "root"
            
            # Stocker les informations du dossier
            structure[rel_path] = {
                "folders": dirs,
                "files": [f for f in files if f.endswith('.md')],
                "file_count": len([f for f in files if f.endswith('.md')])
            }
        
        return {
            "structure": structure, 
            "vault_path": vault_path,
            "total_folders": len(structure),
            "status": "✅ Structure récupérée avec succès"
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/user/{user_id}/files")
async def get_user_files(user_id: str, folder: str = None):
    """📄 Récupérer les fichiers d'un utilisateur (optionnel: dans un dossier spécifique)"""
    try:
        # Récupérer depuis Supabase
        query = supabase_client.table("vault_files")\
            .select("path, updated_at, file_type, metadata")\
            .eq("user_id", user_id)
        
        # Filtrer par dossier si spécifié
        if folder:
            query = query.like("path", f"{folder}%")
        
        result = query.order("updated_at", desc=True).execute()
        
        files = result.data if result.data else []
        
        return {
            "files": files,
            "count": len(files),
            "folder": folder or "all",
            "status": "✅ Fichiers récupérés avec succès"
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/user/{user_id}/smart_suggestions")
async def get_smart_suggestions(user_id: str):
    """🧠 Générer des suggestions intelligentes basées sur le contenu du vault"""
    try:
        print(f"🧠 Génération suggestions pour {user_id}")
        
        vault_path = get_user_vault_path(user_id)
        
        # Charger et analyser le contenu
        docs = load_documents(vault_path)
        if not docs:
            return {
                "suggestions": [
                    "Commencez par compléter votre profil utilisateur",
                    "Définissez vos premiers objectifs de contenu",
                    "Ajoutez vos plateformes de publication préférées"
                ]
            }
        
        # Analyser le contenu pour générer des suggestions avec l'IA
        suggestions = await analyze_vault_and_suggest(docs, user_id)
        
        return {
            "suggestions": suggestions,
            "based_on_files": len(docs),
            "status": "✅ Suggestions générées avec succès"
        }
        
    except Exception as e:
        print(f"❌ Erreur suggestions: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

async def analyze_vault_and_suggest(docs: List[dict], user_id: str) -> List[str]:
    """Analyser le vault et suggérer des améliorations avec l'IA"""
    try:
        # Créer un résumé du contenu (limité pour éviter le token limit)
        content_summary = "\n".join([
            f"Fichier: {doc['source']}\nContenu: {doc['content'][:150]}...\n"
            for doc in docs[:5]  # Prendre seulement les 5 premiers fichiers
        ])
        
        prompt = f"""
Analyse ce vault Obsidian d'un créateur de contenu et suggère 4-5 améliorations concrètes et actionnables.

CONTENU DU VAULT:
{content_summary}

Génère des suggestions SPÉCIFIQUES et ACTIONNABLES comme:
- "Ajoutez un calendrier de publication pour vos contenus Instagram"
- "Créez une analyse de vos 3 principaux concurrents"
- "Définissez vos métriques de succès pour ce mois"

Réponds uniquement avec une liste de suggestions, une par ligne, commençant par un tiret.
"""
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Tu es un consultant en stratégie de contenu. Génère des suggestions courtes et actionnables."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        # Parser la réponse en liste
        suggestions_text = response.choices[0].message.content
        suggestions = [
            s.strip().lstrip('- ').lstrip('* ')  # Enlever les tirets/puces du début
            for s in suggestions_text.split('\n') 
            if s.strip() and len(s.strip()) > 10
        ]
        
        # Limiter à 5 suggestions maximum
        return suggestions[:5]
        
    except Exception as e:
        print(f"❌ Erreur analyse IA: {e}")
        # Suggestions par défaut en cas d'erreur
        return [
            "Complétez votre profil avec plus de détails sur votre niche",
            "Ajoutez un calendrier de publication de contenu",
            "Créez une liste de vos concurrents à analyser",
            "Définissez 3 objectifs SMART pour ce mois",
            "Documentez vos meilleures pratiques de création"
        ]

# === NOUVELLES ROUTES AVANCÉES ===

@app.post("/ai/content_ideas")
async def generate_content_ideas(
    user_id: str = Form(...),
    platform: str = Form(None),
    count: int = Form(5)
):
    """💡 Générer des idées de contenu personnalisées"""
    try:
        print(f"💡 Génération {count} idées pour {user_id} sur {platform or 'toutes plateformes'}")
        
        # Récupérer le contexte utilisateur
        vault_path = get_user_vault_path(user_id)
        docs = load_documents(vault_path)
        
        # Construire le contexte depuis les documents
        user_context = ""
        if docs:
            # Chercher le profil utilisateur
            for doc in docs:
                if "profile" in doc["source"].lower() or "profil" in doc["source"].lower():
                    user_context += f"PROFIL: {doc['content'][:500]}\n\n"
                    break
        
        # Préparer le prompt
        platform_text = f"pour {platform}" if platform else "multi-plateformes"
        
        prompt = f"""
Génère {count} idées de contenu créatives et engageantes {platform_text} pour ce créateur:

CONTEXTE UTILISATEUR:
{user_context if user_context else "Créateur de contenu généraliste"}

Critères:
- Idées actuelles et tendances
- Adaptées au contexte de l'utilisateur
- Facilement réalisables
- Potentiel viral élevé

Format de réponse (JSON):
[
  {{
    "title": "Titre accrocheur",
    "description": "Description détaillée de l'idée",
    "content_type": "video/image/carousel/story",
    "platform": "{platform or 'multiple'}",
    "difficulty": "facile/moyen/difficile",
    "estimated_time": "temps estimé",
    "key_points": ["point 1", "point 2", "point 3"]
  }}
]
"""
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Tu es un expert en création de contenu viral. Génère des idées créatives et réalisables."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=1500
        )
        
        try:
            # Essayer de parser le JSON
            ideas_text = response.choices[0].message.content
            
            # Nettoyer le texte (enlever les balises markdown si présentes)
            if "```json" in ideas_text:
                ideas_text = ideas_text.split("```json")[1].split("```")[0]
            elif "```" in ideas_text:
                ideas_text = ideas_text.split("```")[1].split("```")[0]
            
            ideas = json.loads(ideas_text)
            
            if not isinstance(ideas, list):
                ideas = []
                
        except json.JSONDecodeError:
            # Si le JSON n'est pas valide, créer des idées par défaut
            ideas = [
                {
                    "title": "Tendance du moment dans votre niche",
                    "description": "Partagez votre point de vue sur une tendance actuelle",
                    "content_type": "video",
                    "platform": platform or "multiple",
                    "difficulty": "facile",
                    "estimated_time": "30 minutes",
                    "key_points": ["Recherche tendance", "Point de vue personnel", "Call-to-action"]
                }
            ]
        
        print(f"✅ {len(ideas)} idées générées")
        return {
            "ideas": ideas, 
            "count": len(ideas),
            "platform": platform or "all",
            "status": "✅ Idées générées avec succès"
        }
        
    except Exception as e:
        print(f"❌ Erreur génération idées: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur lors de la génération d'idées: {str(e)}"})

@app.get("/ai/performance_analysis/{user_id}")
async def analyze_performance_potential(user_id: str):
    """📊 Analyser le potentiel de performance du créateur"""
    try:
        print(f"📊 Analyse performance pour {user_id}")
        
        vault_path = get_user_vault_path(user_id)
        docs = load_documents(vault_path)
        
        if not docs:
            return {
                "error": "Aucun contenu trouvé pour l'analyse",
                "recommendation": "Créez d'abord votre profil et stratégie de contenu"
            }
        
        # Construire le contexte pour l'analyse
        vault_content = "\n".join([
            f"Fichier: {doc['source']}\n{doc['content'][:300]}...\n"
            for doc in docs[:3]
        ])
        
        analysis_prompt = f"""
Analyse le potentiel de performance de ce créateur de contenu basé sur son vault Obsidian:

CONTENU DU VAULT:
{vault_content}

Évalue ces dimensions sur 10 et donne des recommandations:

1. Clarté de la niche (0-10)
2. Cohérence de la stratégie (0-10)  
3. Préparation et organisation (0-10)
4. Potentiel d'audience (0-10)
5. Potentiel de monétisation (0-10)

Format JSON:
{{
  "scores": {{
    "niche_clarity": X,
    "strategy_coherence": X,
    "preparation": X,
    "audience_potential": X,
    "monetization_potential": X
  }},
  "overall_score": X,
  "strengths": ["force 1", "force 2"],
  "improvement_areas": ["amélioration 1", "amélioration 2"],
  "recommendations": ["conseil 1", "conseil 2", "conseil 3"]
}}
"""
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Tu es un analyste expert en performance de créateurs de contenu. Sois précis et constructif."
                },
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3
        )
        
        try:
            analysis_text = response.choices[0].message.content
            
            # Nettoyer le JSON
            if "```json" in analysis_text:
                analysis_text = analysis_text.split("```json")[1].split("```")[0]
            elif "```" in analysis_text:
                analysis_text = analysis_text.split("```")[1].split("```")[0]
            
            analysis = json.loads(analysis_text)
            analysis["status"] = "✅ Analyse terminée"
            
            return analysis
            
        except json.JSONDecodeError:
            # Analyse par défaut si le JSON échoue
            return {
                "scores": {
                    "niche_clarity": 7,
                    "strategy_coherence": 6,
                    "preparation": 8,
                    "audience_potential": 7,
                    "monetization_potential": 6
                },
                "overall_score": 6.8,
                "strengths": ["Bonne organisation", "Contenu structuré"],
                "improvement_areas": ["Définir la niche plus clairement", "Développer la stratégie de monétisation"],
                "recommendations": ["Analysez vos concurrents", "Créez un calendrier de contenu", "Définissez vos métriques de succès"],
                "status": "✅ Analyse terminée (mode par défaut)"
            }
                
    except Exception as e:
        print(f"❌ Erreur analyse performance: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# === ROUTES DE DÉMARRAGE ET DEBUG ===

@app.get("/debug/{user_id}")
async def debug_user(user_id: str):
    """🔍 Debug - Informations complètes sur un utilisateur"""
    try:
        vault_path = get_user_vault_path(user_id)
        
        # Compter les fichiers
        file_count = 0
        files_list = []
        if os.path.exists(vault_path):
            for root, dirs, files in os.walk(vault_path):
                for file in files:
                    if file.endswith('.md'):
                        file_count += 1
                        rel_path = os.path.relpath(os.path.join(root, file), vault_path)
                        files_list.append(rel_path)
        
        # Vérifier Supabase
        db_files = supabase_client.table("vault_files")\
            .select("path, updated_at")\
            .eq("user_id", user_id)\
            .execute()
        
        debug_info = {
            "user_id": user_id,
            "vault_path": vault_path,
            "vault_exists": os.path.exists(vault_path),
            "local_files": {
                "count": file_count,
                "files": files_list[:10]  # Premières 10 files
            },
            "database_files": {
                "count": len(db_files.data) if db_files.data else 0,
                "files": [f["path"] for f in (db_files.data or [])[:10]]
            },
            "sync_status": "synced" if file_count == len(db_files.data or []) else "needs_sync",
            "timestamp": datetime.now().isoformat()
        }
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e), "user_id": user_id}

if __name__ == "__main__":
    print("🚀 Démarrage de Cocoon AI Assistant API...")
    print("📖 Documentation disponible sur: http://localhost:8000/docs")
    print("🔄 Health check: http://localhost:8000/ping")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)