import os

def write_file(user_path, relative_path, content):
    full_path = os.path.join(user_path, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

def write_profile_to_obsidian(user_id: str, data: dict):
    base_path = os.path.join("vaults", f"user_{user_id}")
    os.makedirs(base_path, exist_ok=True)
    print(f"[WRITE] Creating Obsidian structure for user: {user_id}")

    # === Profile Folder ===
    write_file(base_path, "Profile/user_profile.md", f"""
# 👤 User Profile
- Experience Level: {data.get("experienceLevel", "")}
- Main Goal: {data.get("contentGoal", "")}
- Location: {data.get("country", "")}, {data.get("city", "")}
""")

    write_file(base_path, "Profile/business_profile.md", f"""
# 🏢 Business Profile
- Type: {data.get("businessType", "")}
- Description: {data.get("businessDescription", "")}
- Niche: {data.get("niche", "")}
""")

    write_file(base_path, "Profile/creator_personality.md", "# ✨ Creator Personality\nTo be discovered...")

    # === Content Strategy ===
    write_file(base_path, "Content_Strategy/content_goals.md", f"""
# 🎯 Content Goals
- Goal: {data.get("contentGoal", "")}
- Niche: {data.get("niche", "")}
""")

    write_file(base_path, "Content_Strategy/platforms_and_audience.md", f"""
# 📣 Platforms & Audience
- Platforms: {", ".join(data.get("platforms", []))}
- Target Generation: {data.get("targetGeneration", "")}
- Time Available: {data.get("timeAvailable", "")}
- Monetization Intent: {data.get("monetizationIntent", "")}
""")

    write_file(base_path, "Content_Strategy/content_types_and_niche.md", f"""
# 📦 Content Types & Niche
- Types: {", ".join(data.get("contentTypes", []))}
- Challenges: {data.get("mainChallenges", "")}
""")

    write_file(base_path, "Content_Strategy/social_accounts.md", "# 🔗 Social Accounts\nAdd your accounts here.")

    # === Resources & Skills ===
    write_file(base_path, "Resources_and_Skills/current_challenges.md", f"""
# ❗ Current Challenges
{data.get("mainChallenges", "")}
""")

    write_file(base_path, "Resources_and_Skills/available_resources.md", f"""
# 🛠️ Available Resources
{data.get("resources", "")}
""")

    write_file(base_path, "Resources_and_Skills/learning_preferences.md", "# 📚 Learning Preferences\nTo define.")

    write_file(base_path, "Resources_and_Skills/existing_skills.md", "# 💡 Existing Skills\nList them here.")

    # === Goals & Metrics ===
    write_file(base_path, "Goals_and_Metrics/impact_goals.md", "# 🌍 Impact Goals\nTo define.")

    write_file(base_path, "Goals_and_Metrics/success_metrics.md", "# 📈 Success Metrics\nTo define.")

    write_file(base_path, "Goals_and_Metrics/monetization_strategy.md", "# 💰 Monetization Strategy\nTo define.")

    # === AI Context ===
    write_file(base_path, "AI_Context/onboarding_summary.md", f"""
# 🤖 AI Onboarding Summary
This file summarizes the user context.

## Overview
- Goal: {data.get("contentGoal", "")}
- Experience: {data.get("experienceLevel", "")}
- Niche: {data.get("niche", "")}
- Audience: {data.get("targetGeneration", "")}
- Platforms: {", ".join(data.get("platforms", []))}

## Intentions
- Monetization: {data.get("monetizationIntent", "")}
- Available Time: {data.get("timeAvailable", "")}

## Notes
Automatically generated. Use for AI context.
""")