import streamlit as st
import requests

try:
    TMDB_API_KEY = st.secrets["TMDB_API_KEY"]
except Exception:
    from dotenv import load_dotenv
    import os
    load_dotenv()
    TMDB_API_KEY = os.getenv("TMDB_API_KEY", None)

def fetch_fallback_poster(movie_title):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_title}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('results'):
            poster_path = data['results'][0].get('poster_path')
            
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
                
    except Exception as e:
        print(e)
        pass
    return None

def check_valid_url(url):
    """Pings the URL to check 404."""
    try:
        response = requests.head(url, timeout=3, allow_redirects=True)
        
        if response.status_code != 200:
            response = requests.get(url, stream=True, timeout=3)
            
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            return content_type.startswith('image/')
        return False
    except requests.RequestException:
        return False

