import csv
import os
from sqlalchemy.orm import Session
from backend.database import Base, engine, SessionLocal
from backend.models import Movie, User
from backend.auth import hash_password

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "movies.csv")

Base.metadata.create_all(bind=engine)
db: Session = SessionLocal()

try:
    existing_titles = {title for (title,) in db.query(Movie.title).all()}
    imported_count = 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["title"] in existing_titles:
                continue
            db.add(Movie(
                title=row["title"],
                genres=row["genres"],
                overview=row["overview"],
                keywords=row["keywords"],
                cast=row["cast"],
                director=row["director"],
                rating=float(row["rating"]),
                vote_count=int(row.get("vote_count") or 0),
                poster_url=row.get("poster_url") or "",
            ))
            existing_titles.add(row["title"])
            imported_count += 1
    if imported_count:
        db.commit()
        print(f"Imported {imported_count} movies.")

    if not db.query(User).filter_by(email="admin@example.com").first():
        db.add(User(
            name="Administrator",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            is_admin=True,
        ))
        db.commit()
        print("Demo admin created.")

finally:
    db.close()
