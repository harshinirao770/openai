# AI Movie Recommendation System

A final-year AI/ML project with:

- FastAPI REST backend
- SQLAlchemy database layer
- SQLite local database
- JWT authentication
- Movie search
- Genre preferences
- Ratings
- Watchlist
- Recommendation history
- Content-based recommendation using TF-IDF + cosine similarity
- Personalized hybrid recommendation scoring
- Streamlit frontend
- Admin statistics endpoint

## Architecture

User -> Streamlit -> FastAPI -> SQLAlchemy/SQLite
                              |
                              +-> Recommendation Engine
                                      |
                                      +-> TF-IDF
                                      +-> Cosine Similarity
                                      +-> User Preferences
                                      +-> User Ratings
                                      +-> Movie Rating

## Python

Recommended: Python 3.11 on Windows.

## Setup

```powershell
py -3.11 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create sample data and ML model:

```powershell
python seed_data.py
python ml/train_model.py
```

Start backend:

```powershell
uvicorn backend.main:app --reload
```

Start frontend in a second terminal:

```powershell
.\venv\Scripts\activate
streamlit run frontend/app.py
```

Backend:
http://127.0.0.1:8000

Swagger:
http://127.0.0.1:8000/docs

Frontend:
http://localhost:8501

Default demo admin:
email: admin@example.com
password: admin123

Change this password for real deployment.
