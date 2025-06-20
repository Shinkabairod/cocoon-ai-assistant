import os

def load_vault(vault_path="vault"):
    documents = []
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md") or file.endswith(".txt"):
                full_path = os.path.join(root, file)
                with open(full_path, "r", encoding="utf-8") as f:
                    text = f.read()
                    documents.append({
                        "filename": file,
                        "text": text
                    })
    return documents

def get_user_vault_path(user_id: str) -> str:
    return f"vaults/user_{user_id}"