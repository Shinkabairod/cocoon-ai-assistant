import os
from datetime import datetime

def write_file(user_path, relative_path, content):
    full_path = os.path.join(user_path, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    return full_path

def write_profile_to_obsidian(user_id: str, data: dict, supabase_client=None):
    base_path = os.path.join(tempfile.gettempdir(), "vaults", f"user_{user_id}")
    os.makedirs(base_path, exist_ok=True)

    files = {
        "Profile/user_profile.md": f"# 👤 User Profile\n- Experience Level: {data.get('experienceLevel', '')}\n- Main Goal: {data.get('contentGoal', '')}\n- Location: {data.get('country', '')}, {data.get('city', '')}",
        "Profile/business_profile.md": f"# 🏢 Business Profile\n- Type: {data.get('businessType', '')}\n- Description: {data.get('businessDescription', '')}\n- Niche: {data.get('niche', '')}",
        "Profile/creator_personality.md": "# ✨ Creator Personality\nTo be discovered...",
        "Content_Strategy/content_goals.md": f"# 🎯 Content Goals\n- Goal: {data.get('contentGoal', '')}\n- Niche: {data.get('niche', '')}",
        "Content_Strategy/platforms_and_audience.md": f"# 📣 Platforms & Audience\n- Platforms: {', '.join(data.get('platforms', []))}\n- Target Generation: {data.get('targetGeneration', '')}\n- Time Available: {data.get('timeAvailable', '')}\n- Monetization Intent: {data.get('monetizationIntent', '')}",
        "Content_Strategy/content_types_and_niche.md": f"# 📦 Content Types & Niche\n- Types: {', '.join(data.get('contentTypes', []))}\n- Challenges: {data.get('mainChallenges', '')}",
        "Content_Strategy/social_accounts.md": "# 🔗 Social Accounts\nAdd your accounts here.",
        "Resources_and_Skills/current_challenges.md": f"# ❗ Current Challenges\n{data.get('mainChallenges', '')}",
        "Resources_and_Skills/available_resources.md": f"# 🛠️ Available Resources\n{data.get('resources', '')}",
        "Resources_and_Skills/learning_preferences.md": "# 📚 Learning Preferences\nTo define.",
        "Resources_and_Skills/existing_skills.md": "# 💡 Existing Skills\nList them here.",
        "Goals_and_Metrics/impact_goals.md": "# 🌍 Impact Goals\nTo define.",
        "Goals_and_Metrics/success_metrics.md": "# 📈 Success Metrics\nTo define.",
        "Goals_and_Metrics/monetization_strategy.md": "# 💰 Monetization Strategy\nTo define.",
        "AI_Context/onboarding_summary.md": f"# 🤖 AI Onboarding Summary\n## Overview\n- Goal: {data.get('contentGoal', '')}\n- Experience: {data.get('experienceLevel', '')}\n- Niche: {data.get('niche', '')}\n- Audience: {data.get('targetGeneration', '')}\n- Platforms: {', '.join(data.get('platforms', []))}\n## Intentions\n- Monetization: {data.get('monetizationIntent', '')}\n- Available Time: {data.get('timeAvailable', '')}\n## Notes\nAutomatically generated. Use for AI context."
    }

    for relative_path, content in files.items():
        write_file(base_path, relative_path, content)
        if supabase_client:
            supabase_client.table("user_files").upsert({
                "user_id": user_id,
                "path": relative_path,
                "content": content.strip(),
                "created_at": datetime.utcnow().isoformat()
            }).execute()