import requests
import streamlit as st

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Movie Recommender", page_icon="🎬", layout="wide")

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

def headers():
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}

def api(method, path, **kwargs):
    return requests.request(method, API + path, headers=headers(), timeout=20, **kwargs)

st.title("🎬 AI Movie Recommendation System")
st.caption("Personalized recommendations using machine learning")

with st.sidebar:
    st.header("Account")
    if not st.session_state.token:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", use_container_width=True):
                r = requests.post(API + "/auth/login", json={"email": email, "password": password}, timeout=20)
                if r.ok:
                    data = r.json()
                    st.session_state.token = data["access_token"]
                    st.session_state.user = data["user"]
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Login failed"))

        with tab2:
            name = st.text_input("Name")
            email2 = st.text_input("Email", key="reg_email")
            password2 = st.text_input("Password", type="password", key="reg_password")
            if st.button("Create account", use_container_width=True):
                r = requests.post(API + "/auth/register", json={"name": name, "email": email2, "password": password2}, timeout=20)
                if r.ok:
                    st.success("Account created. Login now.")
                else:
                    st.error(r.json().get("detail", "Registration failed"))
    else:
        st.success(f"Welcome, {st.session_state.user['name']}")
        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()

if not st.session_state.token:
    st.info("Login or register from the sidebar to use personalized recommendations.")
    st.stop()

# Preferences
st.subheader("🎯 Your Preferences")
genre_options = ["Action", "Adventure", "Animation", "Comedy", "Crime", "Drama", "Fantasy", "Romance", "Sci-Fi", "Thriller"]
prefs = st.multiselect("Favorite genres", genre_options)

if st.button("Save Preferences"):
    r = api("PUT", "/users/preferences", json={"genres": prefs})
    if r.ok:
        st.success("Preferences saved.")
    else:
        st.error(r.text)

# Search
st.subheader("🔎 Search Movies")
search = st.text_input("Search by title, genre, keyword, or description")
r = api("GET", "/movies", params={"q": search, "limit": 50})
movies = r.json() if r.ok else []

if movies:
    options = {f"{m['title']} ⭐ {m['rating']}": m["id"] for m in movies}
    selected_label = st.selectbox("Select a movie to find similar movies", ["None"] + list(options.keys()))

    if st.button("🤖 Recommend Movies", use_container_width=True):
        params = {"limit": 10}
        if selected_label != "None":
            params["movie_id"] = options[selected_label]
        r = api("GET", "/recommendations", params=params)
        if r.ok:
            recs = r.json()
            st.subheader("✨ Personalized Recommendations")
            cols = st.columns(2)
            for i, movie in enumerate(recs):
                with cols[i % 2]:
                    with st.container(border=True):
                        st.markdown(f"### 🎬 {movie['title']}")
                        st.write(f"**Genres:** {movie['genres']}")
                        st.write(f"**Rating:** ⭐ {movie['rating']}")
                        st.write(f"**Director:** {movie['director']}")
                        st.write(movie["overview"])
                        st.caption(f"AI recommendation score: {movie['recommendation_score']:.3f}")
                        if st.button("❤️ Watchlist", key=f"wl_{movie['id']}"):
                            wr = api("POST", f"/movies/{movie['id']}/watchlist")
                            if wr.ok:
                                st.success("Added.")
                            else:
                                st.error(wr.text)
                        score = st.slider("Your rating", 0.0, 10.0, 8.0, 0.5, key=f"rate_{movie['id']}")
                        if st.button("⭐ Rate", key=f"ratebtn_{movie['id']}"):
                            rr = api("POST", f"/movies/{movie['id']}/rate", json={"score": score})
                            if rr.ok:
                                st.success("Rating saved.")
                            else:
                                st.error(rr.text)
        else:
            st.error(r.text)

# Watchlist
st.subheader("❤️ My Watchlist")
wr = api("GET", "/users/watchlist")
if wr.ok:
    watchlist = wr.json()
    if watchlist:
        for movie in watchlist:
            st.write(f"**{movie['title']}** — {movie['genres']} — ⭐ {movie['rating']}")
    else:
        st.info("Your watchlist is empty.")

# History
with st.expander("🕘 Recommendation History"):
    hr = api("GET", "/users/history")
    if hr.ok:
        for item in hr.json()[:20]:
            st.write(f"{item['movie']['title']} — score {item['score']:.3f}")

# Admin
if st.session_state.user.get("is_admin"):
    st.divider()
    st.subheader("🛠️ Admin Dashboard")
    sr = api("GET", "/admin/stats")
    if sr.ok:
        data = sr.json()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Users", data["users"])
        c2.metric("Movies", data["movies"])
        c3.metric("Ratings", data["ratings"])
        c4.metric("Recommendations", data["recommendation_events"])
