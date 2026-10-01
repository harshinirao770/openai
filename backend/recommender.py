import os
import joblib
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from .models import Movie, Rating, UserPreference, Watchlist

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "ml", "model")
SIMILARITY_PATH = os.path.join(MODEL_DIR, "similarity_matrix.pkl")
INDEX_PATH = os.path.join(MODEL_DIR, "movie_index.pkl")

class Recommender:
    def __init__(self):
        self.similarity = None
        self.movie_index = None
        self.loaded = False
        self.load()

    def load(self):
        if os.path.exists(SIMILARITY_PATH) and os.path.exists(INDEX_PATH):
            self.similarity = joblib.load(SIMILARITY_PATH)
            self.movie_index = joblib.load(INDEX_PATH)
            self.loaded = True

    def reload(self):
        self.load()

    def recommend(self, db: Session, user_id: int, selected_movie_id=None, limit=10):
        movies = db.query(Movie).all()
        if not movies:
            return []

        prefs = [p.genre.lower() for p in db.query(UserPreference).filter_by(user_id=user_id).all()]
        ratings = db.query(Rating).filter_by(user_id=user_id).all()
        rated_ids = {r.movie_id for r in ratings}
        watch_ids = {w.movie_id for w in db.query(Watchlist).filter_by(user_id=user_id).all()}

        rating_map = {r.movie_id: r.score for r in ratings}
        results = []

        selected_idx = None
        if selected_movie_id and self.loaded:
            selected_idx = self.movie_index.get(str(selected_movie_id))

        for movie in movies:
            if movie.id in rated_ids:
                continue

            content_score = 0.0
            if selected_idx is not None:
                idx = self.movie_index.get(str(movie.id))
                if idx is not None:
                    content_score = float(self.similarity[selected_idx][idx])

            text = " ".join([
                movie.genres or "",
                movie.overview or "",
                movie.keywords or "",
                movie.cast or "",
                movie.director or "",
            ]).lower()

            pref_score = 0.0
            if prefs:
                matched = sum(1 for p in prefs if p in text)
                pref_score = matched / len(prefs)

            avg_rating = min(max(float(movie.rating or 0) / 10.0, 0), 1)
            popularity = min(np.log1p(movie.vote_count or 0) / np.log1p(10000), 1)

            # If no selected movie, content contribution is replaced by popularity.
            base_content = content_score if selected_movie_id else popularity

            final = (
                0.50 * base_content
                + 0.25 * pref_score
                + 0.15 * avg_rating
                + 0.10 * popularity
            )

            results.append({
                "movie": movie,
                "score": round(final, 5),
                "in_watchlist": movie.id in watch_ids,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

recommender = Recommender()
