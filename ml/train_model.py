import os
import re
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "movies.csv")
MODEL_DIR = os.path.join(BASE_DIR, "ml", "model")
os.makedirs(MODEL_DIR, exist_ok=True)

movies = pd.read_csv(DATA_PATH).fillna("")

def clean(value):
    value = str(value).lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()

features = (
    movies["genres"].map(clean) + " " +
    movies["overview"].map(clean) + " " +
    movies["keywords"].map(clean) + " " +
    movies["cast"].map(clean) + " " +
    movies["director"].map(clean)
)

vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=50000)
matrix = vectorizer.fit_transform(features)
similarity = cosine_similarity(matrix)

movie_index = {str(row["id"]): i for i, row in movies.iterrows()}

joblib.dump(vectorizer, os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
joblib.dump(similarity, os.path.join(MODEL_DIR, "similarity_matrix.pkl"))
joblib.dump(movie_index, os.path.join(MODEL_DIR, "movie_index.pkl"))

print(f"Model trained on {len(movies)} movies.")
print(f"TF-IDF features: {matrix.shape[1]}")
