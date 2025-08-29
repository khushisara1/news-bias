import os
import requests
import streamlit as st
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
BASE_URL = "https://newsapi.org/v2"

HEADERS = {"X-Api-Key": NEWSAPI_KEY or ""}

def _guard():
    # First try Streamlit secrets
    key = None
    try:
        key = st.secrets["NEWSAPI_KEY"]
    except Exception:
        key = os.getenv("NEWSAPI_KEY")  # fallback for local
    
    if not key:
        raise RuntimeError("NEWSAPI_KEY not found. Set it in .env or Streamlit secrets.")
    return key

def search_news(
    query: Optional[str] = None,
    category: Optional[str] = None,
    country: str = "us",
    page_size: int = 50,
) -> List[Dict]:
    """
    Prefer 'everything' for query; fallback to 'top-headlines' for category/country.
    """
    _guard()

    if query:
        url = f"{BASE_URL}/everything"
        params = {
            "q": query,
            "language": "en",
            "pageSize": page_size,
            "sortBy": "publishedAt",
        }
    else:
        url = f"{BASE_URL}/top-headlines"
        params = {
            "category": category or "general",
            "country": country,
            "pageSize": min(page_size, 100),
        }

    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("articles", [])