from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import User, Movie, Rating, UserPreference, Watchlist, RecommendationHistory
from .auth import hash_password, verify_password, create_access_token, get_current_user, require_admin
from .recommender import recommender

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="AI Movie Recommendation System API",
    version="1.0.0",
    description="Final-year AI/ML movie recommendation backend",
    lifespan=lifespan,
)

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PreferenceRequest(BaseModel):
    genres: list[str]

class RatingRequest(BaseModel):
    score: float = Field(ge=0, le=10)

class MovieCreate(BaseModel):
    title: str
    genres: str = ""
    overview: str = ""
    keywords: str = ""
    cast: str = ""
    director: str = ""
    rating: float = Field(default=0, ge=0, le=10)
    vote_count: int = Field(default=0, ge=0)
    poster_url: str = ""

@app.get("/")
def root():
    return {"message": "AI Movie Recommendation System API", "docs": "/docs"}

@app.post("/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(409, "Email already registered")
    user = User(name=payload.name, email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Registration successful", "user_id": user.id}

@app.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "email": user.email, "is_admin": user.is_admin},
    }

@app.get("/users/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "is_admin": user.is_admin}

@app.get("/movies")
def list_movies(
    q: Optional[str] = None,
    genre: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Movie)
    if q:
        term = f"%{q.lower()}%"
        query = query.filter(
            or_(
                func.lower(Movie.title).like(term),
                func.lower(Movie.overview).like(term),
                func.lower(Movie.keywords).like(term),
                func.lower(Movie.genres).like(term),
            )
        )
    if genre:
        query = query.filter(func.lower(Movie.genres).like(f"%{genre.lower()}%"))
    movies = query.order_by(Movie.rating.desc()).limit(limit).all()
    return [movie_dict(m) for m in movies]

@app.get("/movies/{movie_id}")
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")
    return movie_dict(movie)

@app.put("/users/preferences")
def set_preferences(payload: PreferenceRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(UserPreference).filter_by(user_id=user.id).delete()
    unique = sorted(set(g.strip() for g in payload.genres if g.strip()))
    for genre in unique:
        db.add(UserPreference(user_id=user.id, genre=genre))
    db.commit()
    return {"genres": unique}

@app.get("/users/preferences")
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"genres": [p.genre for p in db.query(UserPreference).filter_by(user_id=user.id).all()]}

@app.post("/movies/{movie_id}/rate")
def rate_movie(movie_id: int, payload: RatingRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")

    rating = db.query(Rating).filter_by(user_id=user.id, movie_id=movie_id).first()
    if rating:
        rating.score = payload.score
    else:
        db.add(Rating(user_id=user.id, movie_id=movie_id, score=payload.score))
    db.commit()

    ratings = db.query(Rating).filter_by(movie_id=movie_id).all()
    if ratings:
        movie.rating = round(sum(r.score for r in ratings) / len(ratings), 2)
        movie.vote_count = len(ratings)
        db.commit()

    return {"message": "Rating saved", "score": payload.score}

@app.post("/movies/{movie_id}/watchlist")
def add_watchlist(movie_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(Movie, movie_id):
        raise HTTPException(404, "Movie not found")
    exists = db.query(Watchlist).filter_by(user_id=user.id, movie_id=movie_id).first()
    if not exists:
        db.add(Watchlist(user_id=user.id, movie_id=movie_id))
        db.commit()
    return {"message": "Added to watchlist"}

@app.delete("/movies/{movie_id}/watchlist")
def remove_watchlist(movie_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(Watchlist).filter_by(user_id=user.id, movie_id=movie_id).first()
    if item:
        db.delete(item)
        db.commit()
    return {"message": "Removed from watchlist"}

@app.get("/users/watchlist")
def get_watchlist(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Watchlist).filter_by(user_id=user.id).order_by(Watchlist.created_at.desc()).all()
    result = []
    for item in items:
        movie = db.get(Movie, item.movie_id)
        if movie:
            result.append(movie_dict(movie))
    return result

@app.get("/recommendations")
def recommendations(
    movie_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if movie_id and not db.get(Movie, movie_id):
        raise HTTPException(404, "Selected movie not found")

    results = recommender.recommend(db, user.id, movie_id, limit)
    for item in results:
        db.add(RecommendationHistory(
            user_id=user.id,
            movie_id=item["movie"].id,
            score=item["score"],
        ))
    db.commit()

    return [
        {
            **movie_dict(item["movie"]),
            "recommendation_score": item["score"],
            "in_watchlist": item["in_watchlist"],
        }
        for item in results
    ]

@app.get("/users/history")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(RecommendationHistory).filter_by(user_id=user.id).order_by(RecommendationHistory.created_at.desc()).limit(100).all()
    return [
        {"movie": movie_dict(db.get(Movie, row.movie_id)), "score": row.score, "created_at": row.created_at.isoformat()}
        for row in rows if db.get(Movie, row.movie_id)
    ]

@app.post("/admin/movies")
def create_movie(payload: MovieCreate, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    movie = Movie(**payload.model_dump())
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie_dict(movie)

@app.get("/admin/stats")
def admin_stats(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return {
        "users": db.query(User).count(),
        "movies": db.query(Movie).count(),
        "ratings": db.query(Rating).count(),
        "watchlist_items": db.query(Watchlist).count(),
        "recommendation_events": db.query(RecommendationHistory).count(),
    }

def movie_dict(movie: Movie):
    return {
        "id": movie.id,
        "title": movie.title,
        "genres": movie.genres,
        "overview": movie.overview,
        "keywords": movie.keywords,
        "cast": movie.cast,
        "director": movie.director,
        "rating": movie.rating,
        "vote_count": movie.vote_count,
        "poster_url": movie.poster_url,
    }
