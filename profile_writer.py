# profile_writer.py - Version améliorée avec plus de fonctionnalités

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# === Configuration ===
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ ERREUR: Clés Supabase manquantes dans le fichier .env")

supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

class ObsidianVaultManager:
    """Gestionnaire avancé pour les vaults Obsidian"""
    
    def __init__(self, user_id: str, base_path=None):
        self.user_id = user_id
        self.base_path = base_path or os.path.join(tempfile.gettempdir(), "vaults", f"user_{user_id}")
        os.makedirs(self.base_path, exist_ok=True)
        self.files_created = []  # Tracker des fichiers créés
        
    def write_file(self, relative_path, content, metadata=None):
        """Écrire un fichier avec métadonnées YAML optionnelles"""
        full_path = os.path.join(self.base_path, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Ajouter les métadonnées YAML en en-tête si fournies
        if metadata:
            yaml_front = "---\n"
            for key, value in metadata.items():
                if isinstance(value, list):
                    yaml_front += f"{key}: {json.dumps(value)}\n"
                else:
                    yaml_front += f"{key}: {value}\n"
            yaml_front += "---\n\n"
            content = yaml_front + content.strip()
        
        content = content.strip() + "\n"

        # Écrire le fichier local
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Synchroniser avec Supabase
        try:
            supabase_client.table("vault_files").upsert({
                "user_id": self.user_id,
                "path": relative_path,
                "content": content,
                "file_type": relative_path.split('.')[-1],
                "metadata": metadata or {},
                "updated_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            print(f"⚠️ Erreur sync Supabase pour {relative_path}: {e}")
        
        # Tracker le fichier créé
        self.files_created.append((relative_path, content))
        return relative_path, content

    def create_dashboard(self, data):
        """Créer un dashboard principal pour l'utilisateur"""
        # Calculer quelques stats
        platforms = data.get("platforms", [])
        content_types = data.get("contentTypes", [])
        
        dashboard_content = f"""# 🏠 Mon Dashboard Créateur

> **Bienvenue dans votre espace de création de contenu !**  
> Utilisez ce dashboard comme point central pour naviguer dans votre stratégie.

## 📊 Vue d'ensemble rapide

| Aspect | Information |
|--------|-------------|
| **Expérience** | {data.get("experienceLevel", "Non défini")} |
| **Objectif principal** | {data.get("contentGoal", "Non défini")} |
| **Niche** | {data.get("niche", "Non défini")} |
| **Localisation** | {data.get("city", "")}, {data.get("country", "")} |
| **Plateformes** | {len(platforms)} plateforme(s) active(s) |
| **Types de contenu** | {len(content_types)} type(s) de contenu |

## 🎯 Navigation rapide

### 👤 Mon Profil
- [[Profile/user_profile|📋 Profil Complet]]
- [[Profile/business_profile|🏢 Profil Business]]
- [[Profile/creator_personality|✨ Personnalité de Créateur]]

### 🎯 Ma Stratégie
- [[Content_Strategy/content_goals|🎯 Objectifs de Contenu]]
- [[Content_Strategy/platforms_and_audience|📣 Plateformes & Audience]]
- [[Content_Strategy/content_calendar|📅 Calendrier de Publication]]

### 🛠️ Mes Ressources
- [[Resources_and_Skills/current_challenges|❗ Défis Actuels]]
- [[Resources_and_Skills/available_resources|🛠️ Ressources Disponibles]]
- [[Resources_and_Skills/my_resources/|📁 Mes Ressources Personnelles]]

### 📊 Suivi & Métriques
- [[Goals_and_Metrics/success_metrics|📈 Métriques de Succès]]
- [[Goals_and_Metrics/performance_tracker|📊 Suivi de Performance]]
- [[Goals_and_Metrics/monthly_review|📅 Révision Mensuelle]]

## 📈 Plateformes actives
{self._format_platforms_detailed(platforms)}

## 🎨 Types de contenu
{self._format_content_types(content_types)}

## ⏰ Informations de session
- **Profil créé**: {datetime.now().strftime("%Y-%m-%d à %H:%M")}
- **Dernière mise à jour**: {datetime.now().strftime("%Y-%m-%d à %H:%M")}
- **Version du vault**: 2.0

## 🚀 Actions rapides
- [ ] Compléter mon profil à 100%
- [ ] Définir mes 3 premiers objectifs SMART
- [ ] Planifier ma première semaine de contenu
- [ ] Analyser mes concurrents principaux

---

> 💡 **Conseil**: Utilisez ce dashboard quotidiennement pour rester focalisé sur vos objectifs !
"""
        
        metadata = {
            "type": "dashboard",
            "user_id": self.user_id,
            "created": datetime.now().isoformat(),
            "version": "2.0"
        }
        
        return self.write_file("Dashboard.md", dashboard_content, metadata)

    def _format_platforms_detailed(self, platforms):
        """Formater les plateformes avec des détails"""
        if not platforms:
            return "- ❌ Aucune plateforme définie\n  - [ ] Choisir vos plateformes principales"
        
        platform_details = {
            "YouTube": "🎥 Vidéos longues, tutoriels, vlogs",
            "Instagram": "📸 Photos, stories, reels",
            "TikTok": "🎵 Vidéos courtes, tendances",
            "LinkedIn": "💼 Contenu professionnel, articles",
            "Twitter": "🐦 Micro-contenu, discussions",
            "Facebook": "👥 Communauté, événements"
        }
        
        result = ""
        for platform in platforms:
            description = platform_details.get(platform, "📱 Plateforme sociale")
            result += f"- **{platform}**: {description}\n"
        
        return result

    def _format_content_types(self, content_types):
        """Formater les types de contenu"""
        if not content_types:
            return "- ❌ Aucun type de contenu défini"
        
        type_details = {
            "video": "🎥 Contenu vidéo engageant",
            "reels": "📱 Courtes vidéos virales",
            "posts": "📝 Publications texte/image",
            "stories": "📖 Contenu éphémère",
            "podcast": "🎙️ Contenu audio",
            "blog": "✍️ Articles de blog"
        }
        
        result = ""
        for content_type in content_types:
            description = type_details.get(content_type, "📄 Type de contenu")
            result += f"- **{content_type.title()}**: {description}\n"
        
        return result

    def create_enhanced_profile(self, data):
        """Créer un profil utilisateur enrichi"""
        files_created = []
        
        # === 1. Profil principal enrichi ===
        profile_completion = self._calculate_completion(data)
        
        profile_content = f"""# 👤 Mon Profil Créateur Complet

> **Completion du profil: {profile_completion}%**  
> {"🟢 Profil complet !" if profile_completion >= 80 else "🟡 Profil en cours de completion" if profile_completion >= 50 else "🔴 Profil à compléter"}

## 🎯 Informations essentielles

### 🏷️ Identité créateur
- **Niveau d'expérience**: {data.get("experienceLevel", "Non défini")}
- **Objectif principal**: {data.get("contentGoal", "Non défini")}
- **Localisation**: {data.get("city", "Non défini")}, {data.get("country", "Non défini")}

### 🏢 Profil professionnel
- **Type d'activité**: {data.get("businessType", "Non défini")}
- **Description**: {data.get("businessDescription", "Non défini")}
- **Niche**: {data.get("niche", "Non défini")}

### 🎨 Préférences créatives
- **Types de contenu préférés**: {", ".join(data.get("contentTypes", []))}
- **Plateformes cibles**: {", ".join(data.get("platforms", []))}
- **Audience cible**: {data.get("targetGeneration", "Non défini")}

### ⏰ Contraintes et ressources
- **Temps disponible**: {data.get("timeAvailable", "Non défini")}
- **Intention de monétisation**: {data.get("monetizationIntent", "Non défini")}
- **Ressources disponibles**: {data.get("resources", "Non défini")}

### 🚧 Défis et obstacles
{data.get("mainChallenges", "Aucun défi spécifique identifié")}

## 📈 Plan de développement

### 🎯 Objectifs à court terme (1-3 mois)
- [ ] Définir une routine de création
- [ ] Établir une présence cohérente sur {", ".join(data.get("platforms", ["vos plateformes"]))}
- [ ] Créer {data.get("timeAvailable", "X heures")} de contenu par semaine

### 🚀 Objectifs à long terme (6-12 mois)
- [ ] Développer une communauté engagée
- [ ] Établir une stratégie de monétisation
- [ ] Devenir une référence dans {data.get("niche", "votre niche")}

### 📝 Notes d'évolution personnelle
<!-- Utilisez cet espace pour noter vos réflexions, apprentissages et évolutions -->

**Dernière mise à jour**: {datetime.now().strftime("%Y-%m-%d")}
"""
        
        metadata = {
            "type": "profile",
            "completion": profile_completion,
            "experience_level": data.get("experienceLevel"),
            "niche": data.get("niche"),
            "last_updated": datetime.now().isoformat()
        }
        
        files_created.append(self.write_file("Profile/user_profile.md", profile_content, metadata))

        # === 2. Stratégie de contenu intelligente ===
        strategy_content = f"""# 📋 Ma Stratégie de Contenu Personnalisée

## 🎯 Vision et mission

### 🌟 Ma mission de créateur
> Je veux {data.get("contentGoal", "créer du contenu de qualité")} dans le domaine de {data.get("niche", "ma spécialité")} pour aider {data.get("targetGeneration", "mon audience")} à {self._generate_mission_completion(data)}.

### 🎥 Ma spécialité de contenu
**Niche principale**: {data.get("niche", "À définir")}
**Types de contenu**: {", ".join(data.get("contentTypes", []))}

## 🎯 Stratégie par plateforme

{self._generate_platform_strategy(data)}

## 📅 Planning de création

### ⏰ Temps disponible
**{data.get("timeAvailable", "Temps non défini")}** par semaine

### 📊 Répartition suggérée
{self._generate_time_allocation(data)}

## 🎭 Audience et engagement

### 👥 Audience principale
- **Génération cible**: {data.get("targetGeneration", "Non défini")}
- **Centres d'intérêt**: {data.get("niche", "Votre domaine")}
- **Plateformes de prédilection**: {", ".join(data.get("platforms", []))}

### 💡 Types de contenu à créer
{self._generate_content_suggestions(data)}

## 💰 Stratégie de monétisation

**Intention actuelle**: {data.get("monetizationIntent", "Non définie")}

### 🎯 Opportunités identifiées
{self._generate_monetization_suggestions(data)}

## 📈 Métriques de succès à suivre
- **Croissance d'audience**: +X followers/mois
- **Engagement**: X% d'engagement moyen
- **Reach**: X vues/impressions par post
- **Conversion**: X% de clics sur call-to-action

---
**Créé le**: {datetime.now().strftime("%Y-%m-%d à %H:%M")}
"""
        
        files_created.append(self.write_file("Content_Strategy/master_strategy.md", strategy_content))

        # === 3. Tracker de ressources et compétences ===
        resources_content = f"""# 🛠️ Mes Ressources et Compétences

## 🎬 Inventaire de mes ressources

### 📱 Matériel disponible
{data.get("resources", "Non défini")}

### 🔧 Outils et logiciels
{self._recommend_tools(data)}

## 🧠 Compétences actuelles

### ✅ Ce que je maîtrise déjà
- [ ] Création de contenu pour {", ".join(data.get("platforms", ["mes plateformes"]))}
- [ ] Connaissance de ma niche ({data.get("niche", "à définir")})
- [ ] Communication avec {data.get("targetGeneration", "mon audience")}

### 📚 Compétences à développer
{self._generate_learning_plan(data)}

## 🚧 Défis identifiés et solutions

### ❗ Défis principaux
{data.get("mainChallenges", "Aucun défi spécifique identifié")}

### 💡 Plans d'action suggérés
{self._generate_challenge_solutions(data)}

## 📖 Mon plan d'apprentissage personnalisé

### 🎯 Priorité 1 (ce mois)
- [ ] Maîtriser un nouvel outil de création
- [ ] Analyser 5 concurrents dans ma niche
- [ ] Créer un template de contenu réutilisable

### 🚀 Priorité 2 (dans 3 mois)
- [ ] Développer une signature visuelle cohérente
- [ ] Mettre en place un système de programmation
- [ ] Lancer une première campagne de monétisation

### 🌟 Priorité 3 (dans 6 mois)
- [ ] Diversifier mes sources de revenus
- [ ] Collaborer avec d'autres créateurs
- [ ] Lancer un produit/service personnel

---
**Dernière mise à jour**: {datetime.now().strftime("%Y-%m-%d")}
"""
        
        files_created.append(self.write_file("Resources_and_Skills/skills_tracker.md", resources_content))

        # === 4. Template de suivi performance ===
        metrics_content = f"""# 📊 Suivi de Performance et Métriques

## 🎯 Mes objectifs SMART

### 🚀 Objectifs de croissance
- [ ] **Followers**: Atteindre _____ followers d'ici _____ 
- [ ] **Engagement**: Maintenir ____% d'engagement moyen
- [ ] **Reach**: Obtenir _____ vues/impressions par semaine

### 💰 Objectifs de monétisation
- [ ] **Revenus**: Générer ____€ par mois d'ici _____
- [ ] **Conversions**: ____% de taux de conversion sur mes CTA
- [ ] **Partenariats**: Décrocher ____ collaborations par mois

## 📈 Tableau de bord par plateforme

{self._create_metrics_template(data.get("platforms", []))}

## 💰 Suivi de la monétisation

**Intention actuelle**: {data.get("monetizationIntent", "Non définie")}

### 💡 Sources de revenus potentielles
- [ ] **Partenariats marques**: ___€/mois
- [ ] **Produits propres**: ___€/mois  
- [ ] **Formations/consulting**: ___€/mois
- [ ] **Affiliations**: ___€/mois
- [ ] **Sponsoring**: ___€/mois

## 📅 Révisions et optimisations

### 📊 Révision hebdomadaire
**Tous les lundis**
- [ ] Analyser les performances de la semaine
- [ ] Identifier les contenus les plus performants
- [ ] Ajuster la stratégie pour la semaine suivante

### 📈 Révision mensuelle  
**Le 1er de chaque mois**
- [ ] Bilan des objectifs du mois écoulé
- [ ] Analyse des tendances et insights
- [ ] Définition des objectifs du mois suivant
- [ ] Optimisation de la stratégie globale

### 🎯 Révision trimestrielle
**Tous les 3 mois**
- [ ] Évaluation complète de la stratégie
- [ ] Redéfinition des objectifs long terme
- [ ] Analyse de la concurrence
- [ ] Planification des prochains trimestres

---
**Template créé le**: {datetime.now().strftime("%Y-%m-%d")}
"""
        
        files_created.append(self.write_file("Goals_and_Metrics/performance_tracker.md", metrics_content))

        # === 5. Calendrier de contenu template ===
        calendar_content = f"""# 📅 Mon Calendrier de Contenu

## 🗓️ Planning hebdomadaire type

### 📋 Structure recommandée pour {data.get("timeAvailable", "votre temps disponible")}

| Jour | Plateforme | Type de contenu | Temps estimé | Statut |
|------|------------|-----------------|--------------|---------|
| Lundi | {", ".join(data.get("platforms", ["À définir"])[:2])} | Contenu éducatif | 1h | [ ] |
| Mardi | {", ".join(data.get("platforms", ["À définir"])[:2])} | Behind-the-scenes | 30min | [ ] |
| Mercredi | {", ".join(data.get("platforms", ["À définir"])[:2])} | Contenu divertissant | 45min | [ ] |
| Jeudi | {", ".join(data.get("platforms", ["À définir"])[:2])} | Tips & conseils | 1h | [ ] |
| Vendredi | {", ".join(data.get("platforms", ["À définir"])[:2])} | Contenu communauté | 30min | [ ] |
| Samedi | Repos | Planification semaine suivante | 30min | [ ] |
| Dimanche | Repos | Analyse performances | 30min | [ ] |

## 🎯 Thématiques mensuelles

### 📋 Idées de thèmes par mois
- **Janvier**: Nouveaux départs et résolutions
- **Février**: Amour et relations (Saint-Valentin)
- **Mars**: Renouveau et printemps
- **Avril**: Développement personnel
- **Mai**: Productivité et organisation
- **Juin**: Été et vacances
- **Juillet**: Voyages et découvertes
- **Août**: Détente et bien-être
- **Septembre**: Retour aux affaires
- **Octobre**: Halloween et créativité
- **Novembre**: Gratitude et bilan
- **Décembre**: Fêtes et retrospective

## 📝 Templates de contenu

### 🎬 Template vidéo/post éducatif
1. **Hook** (5 premières secondes): Question ou statistique choc
2. **Promise** (10 secondes): Ce que va apprendre l'audience  
3. **Deliver** (30-45 secondes): Contenu principal
4. **CTA** (5 dernières secondes): Action à faire

### 📸 Template post inspirationnel
1. **Visuel** impactant lié au message
2. **Story** personnelle ou cas d'étude
3. **Lesson** à retenir
4. **Question** pour engager les commentaires

### 🎪 Template behind-the-scenes
1. **Setup** du contexte de création
2. **Process** de travail en cours
3. **Challenges** rencontrés
4. **Results** ou apprentissages

---
**Planning créé le**: {datetime.now().strftime("%Y-%m-%d")}
"""
        
        files_created.append(self.write_file("Content_Strategy/content_calendar.md", calendar_content))

        return files_created

    def _calculate_completion(self, data):
        """Calculer le pourcentage de completion du profil"""
        total_fields = 12
        completed_fields = sum(1 for key in [
            "experienceLevel", "contentGoal", "country", "city", 
            "businessType", "niche", "platforms", "targetGeneration",
            "timeAvailable", "contentTypes", "mainChallenges", "resources"
        ] if data.get(key) and data.get(key) != "")
        return round((completed_fields / total_fields) * 100)

    def _generate_mission_completion(self, data):
        """Générer la fin de la phrase de mission"""
        goal = data.get("contentGoal", "")
        if "share knowledge" in goal.lower() or "partager" in goal.lower():
            return "apprendre et grandir dans leur domaine"
        elif "entertain" in goal.lower() or "divertir" in goal.lower():
            return "se divertir et passer de bons moments"
        elif "inspire" in goal.lower() or "inspirer" in goal.lower():
            return "s'inspirer et réaliser leurs rêves"
        else:
            return "atteindre leurs objectifs"

    def _generate_platform_strategy(self, data):
        """Générer une stratégie par plateforme"""
        platforms = data.get("platforms", [])
        if not platforms:
            return "- ⚠️ Aucune plateforme définie. Choisissez 1-3 plateformes principales."
        
        strategies = {
            "YouTube": "🎥 **Vidéos longues** (5-15min) - Tutoriels, vlogs, contenu éducatif approfondi",
            "Instagram": "📸 **Mix de formats** - Posts carrousels, Reels (30s), Stories quotidiennes",
            "TikTok": "🎵 **Contenu viral court** (15-60s) - Tendances, challenges, tips rapides",
            "LinkedIn": "💼 **Contenu professionnel** - Articles, posts réflexifs, partage d'expertise",
            "Twitter": "🐦 **Micro-contenu** - Threads éducatifs, opinions, engagement temps réel",
            "Facebook": "👥 **Communauté** - Posts longs, événements, groupes de discussion"
        }
        
        result = ""
        for platform in platforms:
            if platform in strategies:
                result += f"### {platform}\n{strategies[platform]}\n\n"
        
        return result

    def _generate_content_suggestions(self, data):
        """Générer des suggestions de contenu basées sur le profil"""
        content_types = data.get("contentTypes", [])
        niche = data.get("niche", "votre domaine")
        
        suggestions = []
        if "video" in content_types:
            suggestions.append(f"- 🎥 **Vidéos éducatives** sur {niche}")
            suggestions.append(f"- 📹 **Tutoriels pratiques** dans votre spécialité")
        if "reels" in content_types:
            suggestions.append(f"- 📱 **Reels/Shorts** avec tips rapides sur {niche}")
            suggestions.append(f"- 🎬 **Behind-the-scenes** de votre processus créatif")
        if "posts" in content_types:
            suggestions.append(f"- 📝 **Posts informatifs** avec carrousels")
            suggestions.append(f"- 📊 **Infographies** sur les tendances de {niche}")
            
        if not suggestions:
            suggestions = [
                f"- 📚 Contenu éducatif sur {niche}",
                "- 💡 Partage de tips et astuces",
                "- 🎯 Réponses aux questions de l'audience"
            ]
            
        return "\n".join(suggestions)

    def _generate_time_allocation(self, data):
        """Suggérer une répartition du temps"""
        time_available = data.get("timeAvailable", "")
        
        if "5h" in time_available or "5 h" in time_available:
            return """
- 🎬 **Création de contenu**: 3h/semaine (60%)
- 📝 **Planification et recherche**: 1h/semaine (20%)
- 📊 **Analyse et engagement**: 1h/semaine (20%)
"""
        elif "10h" in time_available or "10 h" in time_available:
            return """
- 🎬 **Création de contenu**: 6h/semaine (60%)
- 📝 **Planification et recherche**: 2h/semaine (20%)
- 📊 **Analyse et engagement**: 1h/semaine (10%)
- 🤝 **Networking et collaborations**: 1h/semaine (10%)
"""
        else:
            return """
- 🎬 **Création de contenu**: 60% de votre temps
- 📝 **Planification et recherche**: 25% de votre temps
- 📊 **Analyse et optimisation**: 15% de votre temps
"""

    def _generate_learning_plan(self, data):
        """Générer un plan d'apprentissage personnalisé"""
        level = data.get("experienceLevel", "")
        platforms = data.get("platforms", [])
        
        plans = []
        
        if level == "beginner":
            plans.extend([
                "- 📚 **Bases de la création de contenu** (storytelling, composition)",
                "- 🎯 **Comprendre son audience** (personas, engagement)",
                "- 🛠️ **Maîtriser les outils de base** (Canva, apps mobiles)"
            ])
        elif level == "intermediate":
            plans.extend([
                "- 📈 **Stratégies d'engagement avancées** (algorithmes, timing)",
                "- 💰 **Techniques de monétisation** (affiliations, produits)",
                "- 🤖 **Automation et outils IA** (programmation, analyse)"
            ])
        else:  # advanced
            plans.extend([
                "- 🚀 **Scaling et délégation** (équipe, processus)",
                "- 💼 **Business development** (partenariats, diversification)",
                "- 📊 **Analytics avancées** (ROI, attribution)"
            ])
        
        # Ajouter des apprentissages spécifiques aux plateformes
        if "YouTube" in platforms:
            plans.append("- 🎬 **Maîtrise YouTube** (SEO, thumbnails, retention)")
        if "Instagram" in platforms:
            plans.append("- 📸 **Instagram mastery** (Reels, algorithme, hashtags)")
        
        return "\n".join(plans)

    def _generate_challenge_solutions(self, data):
        """Générer des solutions aux défis identifiés"""
        challenges = data.get("mainChallenges", "").lower()
        solutions = []
        
        if "time" in challenges or "temps" in challenges:
            solutions.extend([
                "- ⏰ **Batch creation**: Créer plusieurs contenus en une session",
                "- 📅 **Templates réutilisables**: Gagner du temps sur la structure",
                "- 🤖 **Automation**: Programmer à l'avance avec des outils"
            ])
        
        if "idea" in challenges or "idée" in challenges or "créativité" in challenges:
            solutions.extend([
                "- 💡 **Banque d'idées**: Tenir une liste permanente d'idées",
                "- 🔍 **Veille concurrentielle**: S'inspirer (sans copier) des autres",
                "- 📚 **Consommation variée**: Diversifier ses sources d'inspiration"
            ])
        
        if "engagement" in challenges or "audience" in challenges:
            solutions.extend([
                "- 💬 **Interaction authentique**: Répondre rapidement aux commentaires",
                "- 🎯 **Contenu de valeur**: Toujours apporter quelque chose à l'audience",
                "- 📊 **Analyse des performances**: Comprendre ce qui fonctionne"
            ])
        
        if not solutions:
            solutions = [
                "- 🎯 **Commencer petit**: Focus sur une plateforme et un type de contenu",
                "- 📈 **Mesurer et ajuster**: Tester, analyser, optimiser",
                "- 🤝 **Chercher du support**: Rejoindre des communautés de créateurs"
            ]
        
        return "\n".join(solutions)

    def _generate_monetization_suggestions(self, data):
        """Générer des suggestions de monétisation"""
        intent = data.get("monetizationIntent", "").lower()
        niche = data.get("niche", "votre domaine")
        level = data.get("experienceLevel", "")
        
        suggestions = []
        
        if "yes" in intent or "oui" in intent:
            if level == "beginner":
                suggestions.extend([
                    f"- 🤝 **Micro-partenariats** avec des marques de {niche}",
                    "- 🔗 **Marketing d'affiliation** avec des produits que vous utilisez",
                    "- 💰 **Tip jar** ou dons de votre communauté"
                ])
            else:
                suggestions.extend([
                    f"- 📚 **Formations en ligne** sur {niche}",
                    f"- 💼 **Consulting/coaching** dans votre expertise",
                    "- 🛍️ **Produits physiques ou digitaux** propres",
                    "- 🎯 **Partenariats premium** avec des grandes marques"
                ])
        else:
            suggestions.extend([
                "- 🌱 **Focus croissance** avant monétisation",
                "- 📈 **Construire l'audience** et l'engagement d'abord",
                "- 💎 **Créer de la valeur** pour établir la confiance"
            ])
        
        return "\n".join(suggestions)

    def _recommend_tools(self, data):
        """Recommander des outils selon le profil"""
        platforms = data.get("platforms", [])
        content_types = data.get("contentTypes", [])
        level = data.get("experienceLevel", "")
        
        tools = []
        
        # Outils de base
        tools.append("### 🎨 Création visuelle")
        if level == "beginner":
            tools.extend([
                "- **Canva** (gratuit) - Templates et design facile",
                "- **InShot** (mobile) - Montage vidéo simple"
            ])
        else:
            tools.extend([
                "- **Adobe Creative Suite** - Outils professionnels",
                "- **Figma** - Design collaboratif",
                "- **DaVinci Resolve** (gratuit) - Montage vidéo avancé"
            ])
        
        # Outils spécifiques aux plateformes
        tools.append("\n### 📱 Gestion des réseaux sociaux")
        tools.extend([
            "- **Buffer/Hootsuite** - Programmation multi-plateformes",
            "- **Later** - Spécialisé Instagram",
            "- **TubeBuddy** - Optimisation YouTube"
        ])
        
        # Outils d'analyse
        tools.append("\n### 📊 Analytics et suivi")
        tools.extend([
            "- **Google Analytics** - Suivi du trafic web",
            "- **Sprout Social** - Analytics réseaux sociaux",
            "- **Notion/Airtable** - Organisation et planning"
        ])
        
        return "\n".join(tools)

    def _create_metrics_template(self, platforms):
        """Créer un template de métriques par plateforme"""
        if not platforms:
            return "⚠️ Aucune plateforme définie - Choisissez d'abord vos plateformes principales"
            
        template = ""
        for platform in platforms:
            template += f"""### 📊 {platform}

| Métrique | Objectif | Actuel | Progression |
|----------|----------|---------|-------------|
| Followers/Abonnés | _____ | _____ | [ ] |
| Engagement rate | ____% | ____% | [ ] |
| Vues moyennes | _____ | _____ | [ ] |
| Croissance mensuelle | ____% | ____% | [ ] |
| Reach moyen | _____ | _____ | [ ] |

**Notes {platform}:**
<!-- Ajoutez vos observations spécifiques à cette plateforme -->

"""
        return template

def write_profile_to_obsidian(user_id: str, data: dict, base_path=None):
    """Fonction principale améliorée pour créer un vault Obsidian complet"""
    print(f"🚀 Création du vault Obsidian pour l'utilisateur {user_id}")
    
    manager = ObsidianVaultManager(user_id, base_path)
    
    try:
        # Créer le dashboard principal
        print("📊 Création du dashboard...")
        manager.create_dashboard(data)
        
        # Créer le profil enrichi avec toutes les sections
        print("👤 Création du profil enrichi...")
        manager.create_enhanced_profile(data)
        
        # Sauvegarder les données brutes pour l'IA
        print("🤖 Sauvegarde des données pour l'IA...")
        raw_data_path = "AI_Context/raw_onboarding_data.json"
        raw_content = json.dumps(data, indent=2, ensure_ascii=False)
        manager.write_file(
            raw_data_path, 
            raw_content,
            {
                "type": "ai_context", 
                "format": "json",
                "created": datetime.now().isoformat()
            }
        )
        
        # Créer un fichier de contexte IA en markdown
        ai_context_content = f"""# 🤖 Contexte IA - Résumé Utilisateur

> Ce fichier contient un résumé structuré pour l'IA

## 👤 Profil utilisateur
- **ID**: {user_id}
- **Expérience**: {data.get("experienceLevel", "Non défini")}
- **Objectif**: {data.get("contentGoal", "Non défini")}
- **Niche**: {data.get("niche", "Non défini")}

## 🎯 Stratégie
- **Plateformes**: {", ".join(data.get("platforms", []))}
- **Types de contenu**: {", ".join(data.get("contentTypes", []))}
- **Audience**: {data.get("targetGeneration", "Non défini")}

## ⏰ Contraintes
- **Temps disponible**: {data.get("timeAvailable", "Non défini")}
- **Ressources**: {data.get("resources", "Non défini")}
- **Défis**: {data.get("mainChallenges", "Non défini")}

## 💰 Monétisation
- **Intention**: {data.get("monetizationIntent", "Non défini")}

---
*Généré automatiquement le {datetime.now().strftime("%Y-%m-%d à %H:%M")}*
"""
        
        manager.write_file("AI_Context/user_summary.md", ai_context_content)
        
        print(f"✅ Vault créé avec succès ! {len(manager.files_created)} fichiers générés")
        
        return manager.base_path, manager.files_created
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du vault: {e}")
        return manager.base_path, []