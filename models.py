import joblib
import pandas as pd
import numpy as np
import streamlit as st
import os

N_CANDIDATES = 50

# Copied from google docs, modif. params
@st.cache_resource
def load_models(output_dir):
    knn  = joblib.load(os.path.join(output_dir, 'knn_model.pkl'))
    rf   = joblib.load(os.path.join(output_dir, 'rf_ranker.pkl'))
    feat = joblib.load(os.path.join(output_dir, 'feature_matrix.pkl'))
    df   = pd.read_csv(os.path.join(output_dir, 'movies_clean.csv'),
                       index_col='movie_id')
    return knn, rf, feat, df

# Copied & modified from `02_knn_model_enhanced.ipynb`
def get_knn_candidates(query_vec, watched_titles, n, knn_model, feat_df, clean_df):
    """
    Returns a DataFrame of n candidate movies, excluding already-watched titles.
    """
    distances, indices = knn_model.kneighbors([query_vec])
    distances = distances[0]
    indices   = indices[0]

    candidates = clean_df.iloc[indices].copy()
    candidates['cosine_distance'] = distances
    candidates['similarity']      = (1 - distances).round(4)

    # Exclude already-watched movies
    if watched_titles:
        pattern = '|'.join(watched_titles)
        candidates = candidates[
            ~candidates['Title'].str.contains(pattern, case=False, na=False)
        ]

    return candidates.head(n).reset_index()

# Copied from `02_knn_model_enhanced.ipynb`
def build_query_vector(liked_genres, watch_history, feat_df, clean_df):
    """
    Build a weighted query vector from user preferences.

    liked_genres  : list[str]  — e.g. ['Action', 'Sci-Fi']
    watch_history : dict       — {title_substring: rating_1_to_5}
    """
    vec = np.zeros(len(feat_df.columns))
    col_index = {c: i for i, c in enumerate(feat_df.columns)}

    # ── 1. Genre preferences ─────────────────────────────────────────────
    for genre in liked_genres:
        key = genre.lower().replace('-','_').replace(' ','_')
        col = f'genre_{key}'
        if col in col_index:
            vec[col_index[col]] = 1.0   # genre weight = 1.0 (matches feature matrix)

    # ── 2. Watch history — blend liked movies' feature vectors ───────────
    liked_vecs   = []
    disliked_vecs = []
    for title, rating in watch_history.items():
        match = clean_df[clean_df['Title'].str.contains(title, case=False, na=False)]
        if match.empty:
            continue
        movie_vec = feat_df.loc[match.index[0]].values.astype(float)
        if rating >= 4:
            liked_vecs.append(movie_vec * (rating / 5.0))  # weight by rating
        else:
            disliked_vecs.append(movie_vec)

    if liked_vecs:
        history_signal = np.mean(liked_vecs, axis=0)
        vec = vec + history_signal * 0.6   # blend: 60% history, rest genre prefs

    if disliked_vecs:
        dislike_signal = np.mean(disliked_vecs, axis=0)
        vec = vec - dislike_signal * 0.3   # steer away from disliked patterns
        vec = np.clip(vec, 0, None)        # no negative values

    # Normalize to unit vector for cosine similarity
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec

# Copied from `02_knn_model_enhanced.ipynb`
def recommend(liked_genres, watch_history, top_k,
              knn_model, rf_model, feat_df, clean_df):
    """
    Full two-stage recommendation pipeline.

    Parameters
    ----------
    liked_genres  : list[str]   — genres user selected, e.g. ['Action','Sci-Fi']
    watch_history : dict        — {title_substring: rating_1_to_5}
    top_k         : int         — number of final recommendations to return

    Returns
    -------
    DataFrame with columns: Title, Genre, Director, IMDb Score,
                             Summary, Poster, similarity, like_proba, final_rank
    """
    # Stage 1 — KNN candidates
    query_vec  = build_query_vector(liked_genres, watch_history, feat_df, clean_df)
    candidates = get_knn_candidates(query_vec,
                                     watched_titles=list(watch_history.keys()),
                                     n=N_CANDIDATES,
                                     knn_model=knn_model,
                                     feat_df=feat_df,
                                     clean_df=clean_df)

    if candidates.empty:
        return pd.DataFrame()

    # Stage 2 — RF re-ranking
    cand_features = feat_df.loc[candidates['movie_id']].values
    like_probas   = rf_model.predict_proba(cand_features)[:, 1]
    candidates['like_proba'] = like_probas

    # Combined score: 60% like_proba + 40% cosine similarity
    candidates['final_score'] = (
        0.6 * candidates['like_proba'] +
        0.4 * candidates['similarity']
    )

    result = (
        candidates
        .sort_values('final_score', ascending=False)
        .head(top_k)
        .reset_index(drop=True)
    )
    result.index += 1   # rank starts at 1
    result.index.name = 'rank'

    return result[['movie_id','Title','Genre','Director','Release Date', 'IMDb Score',
                   'Summary','Poster','similarity','like_proba','final_score']]

