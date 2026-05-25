import pandas as pd
import streamlit as st
from models import load_models, recommend
from helpers import check_valid_url, fetch_fallback_poster
import os

# MODEL INIT
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs') # Assumption: in same pwd as outputs
knn, rf, feat, df = load_models(OUTPUT_DIR)

AVAILABLE_GENRES = [
    'Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 'Crime',
    'Documentary', 'Drama', 'Family', 'Fantasy', 'History', 'Horror',
    'Music', 'Mystery', 'Romance', 'Sci-Fi', 'Sport', 'Thriller', 'War', 'Western'
]

if 'watch_history' not in st.session_state:
    st.session_state.watch_history = {}


# STREAMLIT START
st.title("Movie Recommender")
liked_genres = st.multiselect(
    "What genres do you enjoy?",
    options=AVAILABLE_GENRES
)

valid_movies = df['Title'].dropna().unique().tolist()

st.divider()

st.subheader("Add Movies You've Watched")

col1, col2, col3 = st.columns([3, 2, 1])

with col1:
    movie_to_add = st.selectbox(
        "Select a movie:", 
        options=[""] + valid_movies,
        index=0,
        key="movie_input"
    )
with col2:
    rating_to_add = st.slider("Your rating:", 1, 5, 4, key="rating_input")
with col3:
    st.write("")
    st.write("")
    if st.button("Add Movie", use_container_width=True):
        if movie_to_add:
            st.session_state.watch_history[movie_to_add] = rating_to_add
            st.rerun() # Refresh

if st.session_state.watch_history:
    st.write("### Watch History")
    
    history_df = pd.DataFrame([
        {"Movie": title, "Rating": "⭐" * rating} 
        for title, rating in st.session_state.watch_history.items()
    ])
    
    st.dataframe(history_df, hide_index=True, use_container_width=True)
    
    if st.button("Clear History"):
        st.session_state.watch_history = {}
        st.rerun()

st.divider()


# GET RECOMMENDATION
st.subheader("Get Recommendations")
top_k = st.slider("Num. of Recommendations: ", 5, 20, 10)

if st.button("Recommend", type="primary"):
    if not liked_genres:
        st.warning("Please select at least one genre!")
    elif not st.session_state.watch_history:
        st.warning("Please add at least one rated movie to your history!")
    else:
        results = recommend(liked_genres, st.session_state.watch_history, top_k, knn, rf, feat, df)

        for _, row in results.iterrows():
            st.subheader(row['Title'])
            col1, col2 = st.columns([1, 3])
            with col1:
                if row['Poster'] and str(row['Poster']).strip() != "" and check_valid_url(row['Poster']):
                    st.image(row['Poster'], width=120)
                else:
                    poster = fetch_fallback_poster(row['Title'])
                    if poster:
                        st.image(poster, width=120)
                    else:
                        st.caption(row['Title'])
            with col2:
                st.write(f"IMDb Rating: {row['IMDb Score']:.1f} | {row['Genre']}")
                st.write(f"Match: {row['similarity']:.0%}")
                st.write(row['Summary'][:200] + "...")
            st.divider()

