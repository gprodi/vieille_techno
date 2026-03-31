# 📚 CAHIER DE COURS : VEILLE BIM & IA🏗️ 

## 1. Arborescence du Projet

Voici la structure cible de notre outil. Elle respecte les standards de production Python.

veille_bim_ia/
├── .env                 # ⚠️ Secrets (clés API, non versionné)
├── .gitignore           # Fichiers ignorés par Git (venv, .env, __pycache__)
├── pyproject.toml       # 👑 Gère TOUT (dépendances, config Ruff, config Pytest)
├── uv.lock              # Fichier généré par uv (les versions figées)
├── main.py              # Orchestrateur CLI (Pour un lancement silencieux via CRON par ex)
├── app.py               # L'interface Streamlit (Dashboard interactif)
├── PROJECT_CONTEXT.md   # Ton cahier de cours
├── data/                # Base de données locale / État du système
│   └── seen_articles.json
├── core/                # Cœur du système (Configuration, Logs)
│   ├── __init__.py
│   ├── config.py        # Chargement sécurisé du .env avec Pydantic
│   └── logger.py        # Configuration Loguru
├── services/            # Logique métier modulaire
│   ├── __init__.py
│   ├── fetcher.py       # Scraper (httpx/bs4) & Lecteur de flux RSS
│   ├── analyzer.py      # IA, NLP, Traduction et Scoring (Groq + CUDA)
│   └── reporter.py      # Génération du rapport Markdown
└── tests/               # 🛡️ Les tests unitaires
    ├── __init__.py
    ├── test_fetcher.py  # Vérifie que le scraping fonctionne sur un site cible
    └── test_analyzer.py # Vérifie que CUDA est bien détecté

## 2. Stack Technique (Qualité Maximale)

* Langage : Python 3.10+ (Typage statique strict activé)

* Gestionnaire de paquets : uv (remplace pip et le requirements.txt)

* Interface Utilisateur : Streamlit (Dashboard) / Mode CLI via main.py.

* Scraping : httpx (asynchrone) + BeautifulSoup4.

* IA (Hybride) :

**Délégation (Cloud)** : API Groq (Modèles Llama 3 / Mixtral).

**Local (Edge)** : PyTorch + CUDA (Quadro K2200).

* Code Quality & Tooling :

**ruff** : Linter et Formatter ultra-rapide.

**loguru** : Gestion avancée et lisible des logs.

**pytest** : Framework de tests unitaires.

**pydantic** : Validation stricte des données (variables d'environnement et retours JSON de l'IA).


## 3. Commandes uv Essentielles

* Initialiser : uv init veille_bim_ia

* Ajouter une dépendance métier : uv add streamlit httpx beautifulsoup4 python-dotenv groq torch sentence-transformers pydantic loguru

* Ajouter une dépendance de développement (Ruff/Pytest) : uv add --dev ruff pytest

* Lancer l'orchestrateur (CLI) : uv run main.py

* Lancer le dashboard : uv run streamlit run app.py

## 4. Architecture Validée (Domain-Driven Design)

* core/ : L'infrastructure de base (Configuration, Sécurité, Logs). Totalement indépendant du métier.

* services/ : La logique métier pure. Le fetcher ramène la data, l'analyzer la comprend, le reporter la formate.

* data/ : Le stockage de l'état (ex: éviter de traiter deux fois le même article BIM).

* tests/ : L'assurance qualité.

## 5. Lexique Technique 

* BIM (Building Information Modeling) : Processus intelligent basé sur des modèles 3D (Revit, IFC, Jumeaux Numériques).

* Scraping Asynchrone : Interrogation simultanée de plusieurs sites web sans bloquer le CPU (Xeon).

* CUDA : Utilisation de la carte graphique NVIDIA pour l'IA.

* Typage Statique / MyPy : Déclaration explicite des types de variables (texte: str) pour attraper les bugs avant même l'exécution du code.

* Linter (Ruff) : Outil d'analyse statique du code qui traque les erreurs de syntaxe, les imports inutiles et force un style de code propre et unifié.

* Embedding (Plongement lexical) : Représentation mathématique d'un texte. Deux textes sémantiquement proches auront des vecteurs dont la "distance cosinus" est proche de 1.

* JSON Mode : Directive passée à une API de LLM garantissant que la sortie de l'IA sera un code JSON parsable par la machine, évitant le "bavardage" (hallucinations textuelles).

* CPU-Bound vs I/O-Bound : Le scraping est I/O-Bound (on attend que le réseau réponde -> on utilise asyncio). Le calcul d'un réseau de neurones sur GPU est CPU-Bound (la puce travaille à 100% -> on utilise des fonctions synchrones ou du multiprocessing).