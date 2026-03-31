import os
from pathlib import Path

def create_project_structure():
    """
    Génère l'arborescence complète et les fichiers de base pour le projet 'veille_bim_ia'.
    """
    # 1. Définition du dossier racine
    root_dir = Path("Vieille_techno")
    
    # 2. Définition des dossiers à créer
    directories = [
        "data",
        "core",
        "services",
        "tests"
    ]
    
    # 3. Définition des fichiers à créer (Chemin : Contenu par défaut)
    files = {
        ".env": "# ⚠️ SECRETS - NE JAMAIS COMMIT CE FICHIER\nGROQ_API_KEY=\nHUGGINGFACE_API_KEY=\n",
        ".gitignore": ".venv/\n.env\n__pycache__/\n*.pyc\ndata/*\n!data/.gitkeep\n",
        "main.py": '"""Point d\'entrée principal (Orchestrateur CLI)"""\n\nif __name__ == "__main__":\n    print("Lancement de la veille BIM...")\n',
        "app.py": '"""Dashboard Streamlit"""\nimport streamlit as st\n\nst.title("📊 Veille BIM & IA")\n',
        "core/__init__.py": "",
        "core/config.py": '"""Chargement sécurisé du .env avec Pydantic"""\n',
        "core/logger.py": '"""Configuration Loguru"""\n',
        "services/__init__.py": "",
        "services/fetcher.py": '"""Scraper & Lecteur de flux RSS (httpx, bs4)"""\n',
        "services/analyzer.py": '"""IA, NLP, Traduction et Scoring (Groq + PyTorch/CUDA)"""\n',
        "services/reporter.py": '"""Génération du rapport"""\n',
        "tests/__init__.py": "",
        "tests/test_fetcher.py": '"""Tests unitaires pour le fetcher"""\n',
        "tests/test_analyzer.py": '"""Tests unitaires pour l\'IA et la détection CUDA"""\n',
        "data/.gitkeep": "" # Astuce pour que git traque le dossier data même s'il est vide
    }

    print(f"🚀 Création du projet dans : {root_dir.absolute()}")

    # --- CRÉATION DES DOSSIERS ---
    for dir_name in directories:
        # root_dir / dir_name crée dynamiquement le bon chemin (Windows ou Linux)
        dir_path = root_dir / dir_name
        # exist_ok=True évite que le script plante si le dossier existe déjà
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Dossier créé : {dir_path}")

    # --- CRÉATION DES FICHIERS ---
    for file_name, content in files.items():
        file_path = root_dir / file_name
        # On ne crée le fichier que s'il n'existe pas déjà (pour ne pas écraser ton travail futur)
        if not file_path.exists():
            # encoding="utf-8" est crucial, surtout sous Windows, pour éviter les bugs avec les accents
            file_path.write_text(content, encoding="utf-8")
            print(f"📄 Fichier créé : {file_path}")
        else:
            print(f"⏭️  Ignoré (existe déjà) : {file_path}")

    print("\n✅ Arborescence générée avec succès !")
    print("👉 Prochaines étapes dans ton terminal :")
    print("1. cd Vieille_techno")
    print("2. uv init")
    print("3. uv add streamlit httpx beautifulsoup4 python-dotenv groq torch sentence-transformers pydantic loguru")
    print("4. uv add --dev ruff pytest")

if __name__ == "__main__":
    create_project_structure()