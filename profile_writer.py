import os
import tempfile
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# === Load .env ===
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# === Supabase Init ===
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")

supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

class ObsidianVaultManager:
    def __init__(self, user_id: str, base_path=None):
        self.user_id = user_id
        self.base_path = base_path or os.path.join(tempfile.gettempdir(), "vaults", f"user_{user_id}")
        os.makedirs(self.base_path, exist_ok=True)
        
    def write_file(self, relative_path, content, metadata=None):
        """Écrire un fichier avec métadonnées optionnelles"""
        full_path = os.path.join(self.base_path, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Ajouter les métadonnées YAML si fournies
        if metadata:
            yaml_front = "---\n"
            for key, value in metadata.items():
                yaml_front += f"{key}: {value}\n"
            yaml_front += "---\n\n"
            content = yaml_front + content.strip()
        
        content = content.strip() + "\n"

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Sync avec Supabase
        supabase_client.table("vault_files").upsert({
            "user_id": self.user_id,
            "path": relative_path,
            "content": content,
            "updated_at": datetime.now().isoformat()
        }).execute()
        
        return relative_path, content

    def create_dashboard(self, data):
        """Créer un dashboard principal pour l'utilisateur"""
        dashboard_content = f"""
# 🏠 Mon Dashboard Créateur

## 📊 Vue d'ensemble
- **Expérience**: {data.get("experienceLevel", "Non défini")}
- **Objectif principal**: {data.get("contentGoal", "Non défini")}
- **Niche**: {data.get("niche", "Non défini")}
- **Localisation**: {data.get("city", "")}, {data.get("country", "")}

## 🎯 Liens rapides
- [[Profile/user_profile|Mon Profil Complet]]
- [[Content_Strategy/content_goals|Mes Objectifs Content]]
- [[Resources_and_Skills/current_challenges|Mes Défis Actuels]]
- [[Goals_and_Metrics/success_metrics|Mes Métriques]]

## 📈 Plateformes actives
{self._format_platforms(data.get("platforms", []))}

## ⏰ Dernière mise à jour
{datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
        
        metadata = {
            "type": "dashboard",
            "user_id": self.user_id,
            "created": datetime.now().isoformat()
        }
        
        return self.write_file("Dashboard.md", dashboard_content, metadata)

    def _format_platforms(self, platforms):
        if not platforms:
            return "- Aucune plateforme définie"
        return "\n".join([f"- {platform}" for platform in platforms])

    def create_enhanced_profile(self, data):
        """Créer un profil enrichi avec suggestions IA"""
        files_created = []
        
        # === 1. Profil principal enrichi ===
        profile_content = f"""
# 👤 Profil Utilisateur Complet

## 🎯 Informations de base
- **Niveau d'expérience**: {data.get("experienceLevel", "")}
- **Objectif principal**: {data.get("contentGoal", "")}
- **Localisation**: {data.get("city", "")}, {data.get("country", "")}

## 🏢 Profil Business
- **Type d'activité**: {data.get("businessType", "")}
- **Description**: {data.get("businessDescription", "")}
- **Niche**: {data.get("niche", "")}

## 🎨 Préférences créatives
- **Types de contenu préférés**: {", ".join(data.get("contentTypes", []))}
- **Plateformes cibles**: {", ".join(data.get("platforms", []))}
- **Audience cible**: {data.get("targetGeneration", "")}

## ⏰ Contraintes et ressources
- **Temps disponible**: {data.get("timeAvailable", "")}
- **Intention de monétisation**: {data.get("monetizationIntent", "")}
- **Ressources disponibles**: {data.get("resources", "")}

## 🚧 Défis actuels
{data.get("mainChallenges", "")}

## 📝 Notes d'évolution
- [ ] Compléter les informations manquantes
- [ ] Définir des objectifs SMART
- [ ] Identifier les opportunités de croissance
"""
        
        metadata = {
            "type": "profile",
            "completion": self._calculate_completion(data),
            "last_updated": datetime.now().isoformat()
        }
        
        files_created.append(self.write_file("Profile/user_profile.md", profile_content, metadata))

        # === 2. Stratégie de contenu intelligente ===
        strategy_content = f"""
# 📋 Ma Stratégie de Contenu

## 🎯 Objectifs définis
- **Objectif principal**: {data.get("contentGoal", "")}
- **Niche**: {data.get("niche", "")}

## 🎥 Types de contenu à produire
{self._generate_content_suggestions(data)}

## 📅 Planning recommandé
Avec {data.get("timeAvailable", "temps non défini")} disponible par semaine :
{self._generate_time_allocation(data)}

## 🎯 Audience et plateformes
- **Génération cible**: {data.get("targetGeneration", "")}
- **Plateformes**: {", ".join(data.get("platforms", []))}

## 💡 Idées de contenu
- [ ] Contenu éducatif sur {data.get("niche", "votre domaine")}
- [ ] Behind-the-scenes de votre {data.get("businessType", "activité")}
- [ ] Conseils pratiques pour {data.get("targetGeneration", "votre audience")}
"""
        
        files_created.append(self.write_file("Content_Strategy/master_strategy.md", strategy_content))

        # === 3. Tracker de ressources et compétences ===
        skills_content = f"""
# 🛠️ Mes Ressources et Compétences

## 🎬 Ressources actuelles
{data.get("resources", "Non défini")}

## 🚧 Défis identifiés
{data.get("mainChallenges", "")}

## 📚 Plan d'apprentissage suggéré
{self._generate_learning_plan(data)}

## 💡 Compétences à développer
- [ ] Création de contenu pour {", ".join(data.get("platforms", []))}
- [ ] Stratégie d'audience {data.get("targetGeneration", "")}
- [ ] Optimisation pour {data.get("niche", "")}

## 🔧 Outils recommandés
{self._recommend_tools(data)}
"""
        
        files_created.append(self.write_file("Resources_and_Skills/skills_tracker.md", skills_content))

        # === 4. Template de suivi performance ===
        metrics_content = f"""
# 📊 Suivi de Performance

## 🎯 Objectifs SMART à définir
- [ ] Objectif de followers : ___
- [ ] Objectif d'engagement : ___%
- [ ] Objectif de revenus : ___€/mois

## 📈 Métriques par plateforme
{self._create_metrics_template(data.get("platforms", []))}

## 💰 Stratégie de monétisation
**Intention actuelle**: {data.get("monetizationIntent", "")}

### Opportunités identifiées :
- [ ] Partenariats marques
- [ ] Produits/services propres
- [ ] Formations/consulting
- [ ] Affiliations

## 📅 Révision mensuelle
- [ ] Analyser les performances
- [ ] Ajuster la stratégie
- [ ] Planifier le mois suivant
"""
        
        files_created.append(self.write_file("Goals_and_Metrics/performance_tracker.md", metrics_content))

        return files_created

    def _calculate_completion(self, data):
        """Calculer le pourcentage de completion du profil"""
        total_fields = 12
        completed_fields = sum(1 for key in [
            "experienceLevel", "contentGoal", "country", "city", 
            "businessType", "niche", "platforms", "targetGeneration",
            "timeAvailable", "contentTypes", "mainChallenges", "resources"
        ] if data.get(key))
        return round((completed_fields / total_fields) * 100)

    def _generate_content_suggestions(self, data):
        """Générer des suggestions de contenu basées sur le profil"""
        content_types = data.get("contentTypes", [])
        niche = data.get("niche", "votre domaine")
        
        suggestions = []
        if "video" in content_types:
            suggestions.append(f"- 🎥 Vidéos éducatives sur {niche}")
        if "reels" in content_types:
            suggestions.append(f"- 📱 Reels/Shorts tendances {niche}")
        if "posts" in content_types:
            suggestions.append(f"- 📝 Posts informatifs {niche}")
            
        return "\n".join(suggestions) if suggestions else "- À définir selon vos préférences"

    def _generate_time_allocation(self, data):
        """Suggérer une répartition du temps"""
        time_available = data.get("timeAvailable", "")
        if "5h" in time_available:
            return """
- 🎬 Création: 3h/semaine
- 📝 Planification: 1h/semaine  
- 📊 Analyse: 1h/semaine
"""
        return "- À définir selon votre temps disponible"

    def _generate_learning_plan(self, data):
        """Générer un plan d'apprentissage personnalisé"""
        level = data.get("experienceLevel", "")
        platforms = data.get("platforms", [])
        
        if level == "beginner":
            return """
- 📚 Bases de la création de contenu
- 🎯 Comprendre son audience
- 🛠️ Maîtriser les outils de base
"""
        elif level == "intermediate":
            return """
- 📈 Stratégies d'engagement avancées
- 💰 Techniques de monétisation
- 🤖 Automation et outils IA
"""
        return "- Plan d'apprentissage à personnaliser"

    def _recommend_tools(self, data):
        """Recommander des outils selon le profil"""
        platforms = data.get("platforms", [])
        tools = []
        
        if "YouTube" in platforms:
            tools.append("- 🎬 Editing: DaVinci Resolve (gratuit)")
        if "Instagram" in platforms:
            tools.append("- 📱 Stories: Canva, Later")
        if "TikTok" in platforms:
            tools.append("- 🎵 Editing: CapCut, InShot")
            
        tools.append("- 📊 Analytics: Google Analytics")
        tools.append("- 📅 Planning: Buffer, Hootsuite")
        
        return "\n".join(tools)

    def _create_metrics_template(self, platforms):
        """Créer un template de métriques par plateforme"""
        if not platforms:
            return "Aucune plateforme définie"
            
        template = ""
        for platform in platforms:
            template += f"""
### {platform}
- Followers: ___
- Engagement rate: ___%
- Vues moyennes: ___
- Croissance mensuelle: ___%

"""
        return template

def write_profile_to_obsidian(user_id: str, data: dict, base_path=None):
    """Fonction principale améliorée"""
    manager = ObsidianVaultManager(user_id, base_path)
    
    files_created = []
    
    # Créer le dashboard principal
    files_created.append(manager.create_dashboard(data))
    
    # Créer le profil enrichi
    files_created.extend(manager.create_enhanced_profile(data))
    
    # Sauvegarder les données brutes pour l'IA
    raw_data_path = "AI_Context/raw_onboarding_data.json"
    files_created.append(manager.write_file(
        raw_data_path, 
        json.dumps(data, indent=2, ensure_ascii=False),
        {"type": "ai_context", "format": "json"}
    ))
    
    return manager.base_path, files_created