import pandas as pd
import streamlit as st
from models import load_models, recommend
from helpers import check_valid_url, fetch_fallback_poster
import os
import base64

# Set Page Config
st.set_page_config(page_title="Movie Recommender", layout="centered")

# --- MODEL INIT ---
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')
knn, rf, feat, df = load_models(OUTPUT_DIR)

AVAILABLE_GENRES = [
    'Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 'Crime',
    'Documentary', 'Drama', 'Family', 'Fantasy', 'History', 'Horror',
    'Music', 'Mystery', 'Romance', 'Sci-Fi', 'Sport', 'Thriller', 'War', 'Western'
]
# Get unique, non-null directors & sort alphabetically
AVAILABLE_DIRECTORS = sorted([str(d) for d in df['Director'].dropna().unique() if str(d).strip() != ''])

# --- SESSION STATE (Disinkronkan dengan kebutuhan Backend) ---
if 'watch_history' not in st.session_state:
    st.session_state.watch_history = {}
if 'preferred_directors' not in st.session_state:
    st.session_state.preferred_directors = []
if 'liked_genres' not in st.session_state:
    st.session_state.liked_genres = []
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None
if 'survey_shown' not in st.session_state:
    st.session_state.survey_shown = False

# --- SYSTEM RESET FUNCTION ---
def reset_application():
    st.session_state.watch_history = {}
    st.session_state.liked_genres = []
    st.session_state.preferred_directors = []
    st.session_state.current_step = 1
    st.session_state.recommendations = None
    st.session_state.survey_shown = False
    st.rerun()

# --- HELPERS ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

@st.dialog("Quick Feedback Survey")
def show_survey_dialog():
    st.write("After you see the results, please fill out a quick survey for our assignment!")
    st.link_button("Google Forms Link", "https://forms.gle/sVSpvgcVsJtaq7iC9", type="secondary")
    st.session_state.survey_shown = True

# Definisikan 4 warna gradasi baru Anda di sini
# Menggunakan sudut 135deg agar gradasi bergerak diagonal dari kiri atas ke kanan bawah
gradient_style = "linear-gradient(135deg, #180161 0%, #4F1787 40%, #EB3678 75%, #FB773C 100%)"

try:
    img_path = os.path.join(os.path.dirname(__file__), 'Movie Wall BG.jpeg')
    img_base64 = get_base64_of_bin_file(img_path)
    bg_css = f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        /* Menggabungkan 4 warna gradasi (dengan opacity 0.6 agar gambar di bawahnya samar terlihat) + Gambar Latar Belakang */
        background-image: linear-gradient(135deg, rgba(24, 1, 97, 0.6) 0%, rgba(79, 23, 135, 0.6) 40%, rgba(235, 54, 120, 0.6) 75%, rgba(251, 119, 60, 0.6) 100%), url("data:image/jpeg;base64,{img_base64}");
        background-size: cover; 
        background-position: center; 
        background-attachment: fixed;
    }}
    </style>
    """
    st.markdown(bg_css, unsafe_allow_html=True)
except:
    # JIKA GAMBAR GAGAL DIMUAT: Langsung menampilkan gradasi solid murni dari 4 warna pilihan Anda
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background: {gradient_style};
        background-attachment: fixed;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- CUSTOM CSS FOR FIGMA GLASSMORPHISM LOOK ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
    
    html, body, [data-testid="stWidgetLabel"], h1, h2, h3, h4, p, span, li {
        font-family: 'Poppins', sans-serif !important;
        color: #FFFFFF !important;
        text-shadow: none !important;
    }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-radius: 24px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        padding: 30px; 
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
    }
    
    .movie-summary {
        color: rgba(255, 255, 255, 0.8) !important;
        font-weight: 400 !important;
        font-size: 0.95rem !important;
    }

    div.stButton > button {
        width: 100% !important;
        height: 48px !important;
        background-color: rgba(255, 255, 255, 0.12) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        color: #FFFFFF !important;
        border-radius: 20px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
    }
    
    div.stButton > button:hover {
        background-color: rgba(255, 255, 255, 0.25) !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
    }

    /* Dropdown input selection style */
    div[data-baseweb="select"] > div {
        background-color: rgba(0, 0, 0, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
    }

    div[data-baseweb="select"] * {
        color: #FFFFFF !important;
    }
    
    /* Menjaga teks pencarian di dalam selectbox agar tetap terlihat putih saat mengetik */
    input[data-testid="stSelectboxInput"] {
        color: #FFFFFF !important;
    }
    
    div[data-testid="stToast"] {
        background-color: #210B36 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- NAVIGATION LOGIC ---
def next_step(): st.session_state.current_step += 1
def prev_step(): st.session_state.current_step -= 1

# --- HEADER & RESTART ---
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.markdown('<h2 style="margin:0px; color:#FFFFFF;">Movie <span style="color:#EB3678;">Recommender</span></h2>', unsafe_allow_html=True)
with head_col2:
    st.markdown("""
        <style>
        div.stButton > button[key="app_reset_btn"] {
            background-color: rgba(235, 54, 120, 0.2) !important;
            border: 2px solid #EB3678 !important; color: #FFFFFF !important;
            font-size: 13px !important; height: 38px !important; font-weight: 700 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    if st.button("Restart Application", key="app_reset_btn", use_container_width=True):
        reset_application()

st.write("---")

# --- INDIKATOR STEP ---
cols_step = st.columns(3)
step_names = ["1. Preferences", "2. Watched History", "3. Results"]
for i, name in enumerate(step_names):
    step_num = i + 1
    is_active = st.session_state.current_step == step_num
    border_color = "#FB773C" if is_active else "rgba(255,255,255,0.2)"
    
    cols_step[i].markdown(f"""
        <div style="text-align:center; border-bottom: 5px solid {border_color}; padding-bottom:8px;">
            <span style="color: #FFFFFF !important; font-weight: 800 !important; font-size: 1.1rem !important; display: block;">
                {name}
            </span>
        </div>
    """, unsafe_allow_html=True)
st.write("")

# ==========================================
# HALAMAN 1: PREFERENCES
# ==========================================
if st.session_state.current_step == 1:
    st.markdown('<div class="glass-card"><h2>What kind of movie interests you?</h2><p style="color: rgba(255,255,255,0.7) !important; font-weight:600; margin-bottom:0px;">Pick genres you enjoy. The more selections made, the better the recommendations.</p></div>', unsafe_allow_html=True)
    
    st.markdown("""
        <style>
        div.stButton > button[key^="btn_"] {
            width: 100% !important; height: 40px !important; border-radius: 20px !important;
            font-size: 14px !important; font-weight: 600 !important; padding: 0px 10px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    cols = st.columns(4)
    for i, genre in enumerate(AVAILABLE_GENRES):
        col = cols[i % 4]
        is_sel = genre in st.session_state.liked_genres
        
        bg_color = "rgba(255, 255, 255, 0.35)" if is_sel else "rgba(255, 255, 255, 0.08)"
        border_color = "rgba(255, 255, 255, 0.8)" if is_sel else "rgba(255, 255, 255, 0.15)"
        
        if col.button(genre, key=f"btn_{genre}", use_container_width=True):
            if is_sel: 
                st.session_state.liked_genres.remove(genre)
            else: 
                st.session_state.liked_genres.append(genre)
            st.rerun()

    if st.session_state.liked_genres:
        st.write("---")
        st.markdown("### 🍿 Selected Genres:")
        
        st.markdown("""
            <style>
            div.stButton > button[key^="del_"] {
                background-color: #EB3678 !important; color: white !important; border: none !important; 
                height: 36px !important; font-weight: 700 !important; border-radius: 20px !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        pop_cols = st.columns(4)
        for i, g in enumerate(st.session_state.liked_genres):
            if pop_cols[i % 4].button(f"{g}  ❌", key=f"del_{g}"):
                st.session_state.liked_genres.remove(g)
                st.rerun()
    st.write("---")
    st.markdown('<h3>Preferred Directors (Optional)</h3><p style="color:#d1d5db; font-size:14px;">Select your favorite directors to highlight their movies in the results.</p>', unsafe_allow_html=True)
    
    if 'Director' in df.columns:
        
        selected_directors = st.multiselect(
            "Choose directors:",
            options=AVAILABLE_DIRECTORS,
            default=st.session_state.preferred_directors,
            key="director_select",
            label_visibility="collapsed"
        )
        
        if selected_directors != st.session_state.preferred_directors:
            st.session_state.preferred_directors = selected_directors
            st.rerun()

# ==========================================
# HALAMAN 2: WATCHED HISTORY
# ==========================================
elif st.session_state.current_step == 2:
    st.markdown('<div class="glass-card"><h2>Add Movies You\'ve Watched</h2></div>', unsafe_allow_html=True)
    
    valid_movies = df['Title'].dropna().unique().tolist()
    
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("<b style='font-size:1.1rem; color:#FFFFFF;'>Search & Select Movie:</b>", unsafe_allow_html=True)
        # Menghapus label_visibility="collapsed" agar input focus untuk pengetikan bekerja lebih stabil
        movie_to_add = st.selectbox("Pilih Film", options=[""] + valid_movies, label_visibility="visible", key="movie_input")
    with c2:
        st.markdown("<b style='font-size:1.1rem; color:#FFFFFF;'>Give Rating (1-5):</b>", unsafe_allow_html=True)
        st.write("") # Spacer agar sejajar dengan selectbox
        rating_to_add = st.slider("Rating", 1, 5, 4, key="rating_input_slider")
    
    st.write("")
    st.markdown("""
        <style>
        div.stButton > button[key="add_movie_btn"] { background-color: #FB773C !important; color: white !important; border: none !important; font-size:16px !important; font-weight:800 !important; height:45px !important;}
        </style>
    """, unsafe_allow_html=True)
    
    if st.button("➕ Add Movie to List", key="add_movie_btn", use_container_width=True):
        if movie_to_add:
            st.session_state.watch_history[movie_to_add] = rating_to_add
            st.toast(f"Successfully added {movie_to_add}!")
            st.rerun()

    if st.session_state.watch_history:
        st.write("---")
        st.markdown("### 📋 Watch History List")
        history_df = pd.DataFrame([{"Movie Title": t, "Your Rating": "⭐" * r} for t, r in st.session_state.watch_history.items()])
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Clear All History", key="clear_all"):
            st.session_state.watch_history = {}
            st.rerun()

# ==========================================
# HALAMAN 3: RESULT (Fix Urutan Kemiripan)
# ==========================================
elif st.session_state.current_step == 3:
    st.markdown('<div class="glass-card"><h2>Recommendations for You</h2></div>', unsafe_allow_html=True)
    
    st.markdown("<b style='font-size:1.1rem;'>Set number of recommendations:</b>", unsafe_allow_html=True)
    top_k = st.slider("Jumlah", 5, 20, 10, label_visibility="collapsed", key="top_k_slider")

    st.write("")
    st.markdown("""
        <style>
        div.stButton > button[key="recommend_btn"] { 
            background: linear-gradient(90deg, #EB3678, #FB773C) !important; 
            color: white !important; border: none !important; font-size: 18px !important; font-weight: 800 !important; height: 50px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("✨ Generate Recommendation", key="recommend_btn", use_container_width=True, type="primary"):
        if not st.session_state.liked_genres or not st.session_state.watch_history:
            st.error("Data preferences atau watch history kamu masih kosong! Silakan kembali ke step sebelumnya.")
        else:
            if not st.session_state.survey_shown:
                show_survey_dialog()
            with st.spinner("Searching matching movies..."):
                results = recommend(st.session_state.liked_genres, st.session_state.watch_history, top_k, knn, rf, feat, df)
                results = results.sort_values(by='similarity', ascending=False)
                st.session_state.recommendations = results

    # --- SORT CONTROLS & DISPLAY (runs whenever recommendations exist) ---
    with st.spinner("Loading Results..."):
        if st.session_state.recommendations is not None:
            results = st.session_state.recommendations.copy()

            st.write("---")

            sort_col1, sort_col2 = st.columns([2, 1])
            with sort_col1:
                sort_by = st.selectbox(
                    "Sort by:",
                    options=["Similarity", "Release Date", "Director"],
                    key="sort_by_select"
                )
            with sort_col2:
                sort_asc = st.checkbox("Ascending", value=False, key="sort_asc_check")

            # Apply sort
            sort_map = {
                "Similarity": "similarity",
                "Release Date": "Release Date",
                "Director": "Director",
            }
            sort_col = sort_map[sort_by]

            if sort_col in results.columns:
                if sort_col == "Release Date":
                    sortable = pd.to_datetime(results[sort_col], format='%d %b %Y', errors='coerce')
                    results = results.assign(_sort_key=sortable).sort_values('_sort_key', ascending=sort_asc).drop(columns='_sort_key')
                else:
                    results = results.sort_values(by=sort_col, ascending=sort_asc)

                st.write("---")
                for _, row in results.iterrows():
                    movie_genres = [g.strip() for g in str(row['Genre']).split(',')]
                    genres_fmted = []
                    has_genre_match = False
                    for g in movie_genres:
                        if g in st.session_state.liked_genres:
                            has_genre_match = True
                            genres_fmted.append(f"<span style='background-color: #EB3678; color: white; padding: 2px 8px; border-radius: 6px; font-weight: bold;'>{g}</span>")
                        else:
                            genres_fmted.append(g)

                    if has_genre_match:
                        st.markdown('<div class="glass-card" style="border: 2px solid #EB3678 !important; box-shadow: 0 0 20px rgba(235, 54, 120, 0.3) !important;">', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                    col_img, col_txt = st.columns([1, 2.5])
                    
                    with col_img:
                        poster_url = row['Poster']
                        if poster_url and str(poster_url).strip() != "" and check_valid_url(poster_url):
                            st.image(poster_url, use_container_width=True)
                        else:
                            poster = fetch_fallback_poster(row['Title'])
                            if poster: st.image(poster, use_container_width=True)
                            else: st.info("No Poster Available")
                    
                    with col_txt:
                        has_preferred_director = False
                        if 'Director' in row and st.session_state.preferred_directors:
                            if any(pref_dir in str(row['Director']) for pref_dir in st.session_state.preferred_directors):
                                has_preferred_director = True

                        if has_preferred_director:
                            st.markdown("<span style='background: linear-gradient(135deg, #EB3678, #FB773C); color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;'>🎬 Preferred Director</span><br><br>", unsafe_allow_html=True)

                        st.markdown(f"<h3 style='margin-top:0px; color:#FB773C !important; font-weight:800;'>{row['Title']}</h3>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size:0.95rem; margin-bottom:5px; color:#FFFFFF !important;'>⭐ <b>IMDb Rating:</b> {row['IMDb Score']:.1f} | 🎭 <b>Genre:</b> {", ".join(genres_fmted)}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size:0.95rem; margin-bottom:15px; color:#FFFFFF !important;'>🎯 <b>Match Score:</b> <span style='color:#EB3678; font-weight:800;'>{row['similarity']:.0%}</span></p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='movie-summary'>{row['Summary'][:180]}...</p>", unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)


# --- FOOTER STICKY NAVIGATION ---
st.write("---")
n_col1, n_col2, n_col3 = st.columns([1, 4, 1])

st.markdown("""
    <style>
    div.stButton > button[key="back_btn"], div.stButton > button[key="next_btn"] {
        background-color: #4F1787 !important; color: white !important; border: 2px solid #EB3678 !important; font-weight: 800 !important; height: 42px !important; font-size:15px !important;
    }
    </style>
""", unsafe_allow_html=True)

with n_col1:
    if st.session_state.current_step > 1:
        st.button("⬅ Back", key="back_btn", on_click=prev_step)

with n_col3:
    if st.session_state.current_step < 3:
        st.button("Next ➡", key="next_btn", on_click=next_step)
