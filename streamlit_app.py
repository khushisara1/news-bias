
import os
import io
import json
import textwrap
from datetime import datetime
from typing import List, Dict, Any

import streamlit as st
from dotenv import load_dotenv

from news_client import search_news
from summarizer import summarize_articles
from storage import init_db, save_item, list_items, update_rating, delete_item
from utils import slugify, fmt_date

# Initialize session state for saved items and ratings
if 'saved_items' not in st.session_state:
    st.session_state.saved_items = {}
if 'ratings' not in st.session_state:
    st.session_state.ratings = {}
if 'show_saved' not in st.session_state:
    st.session_state.show_saved = False
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'feed'
if 'next_view' in st.session_state:
    st.session_state.current_view = st.session_state.next_view
    del st.session_state.next_view

load_dotenv()
st.set_page_config(page_title="Personalized News Digest", page_icon="🗞", layout="wide")

# ---------- INIT DB ----------
init_db()

# ---------- SESSION STATE ----------
if 'show_saved' not in st.session_state:
    st.session_state.show_saved = False
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'feed'

# ---------- SIDEBAR ----------
st.sidebar.title("🗞 Personalized News Digest")

# Navigation
view_options = {
    'feed': '📰 News Feed',
    'saved': '💾 Saved Articles'
}
selected_view = st.sidebar.radio(
    "Navigation",
    options=list(view_options.keys()),
    format_func=lambda x: view_options[x],
    key='current_view'
)

st.sidebar.markdown("---")

# Only show feed controls when in feed view
if st.session_state.current_view == 'feed':
    st.sidebar.caption("Pick interests & frequency, then generate a smart digest.")
    
    INTERESTS = [
        "Technology", "Business", "Science", "Health",
        "Entertainment", "Sports", "Politics", "World", "Finance", "Climate"
    ]
    countries = {"United States": "us"}
    
    freq = st.sidebar.selectbox("Delivery frequency", ["Daily", "Weekly"])
    selected_topics = st.sidebar.multiselect("Interests", INTERESTS, default=["Technology"])
    country = st.sidebar.selectbox("Region (Top Headlines)", list(countries.keys()), index=0)
    keywords = st.sidebar.text_input("Optional keywords (e.g. 'open source, Google')")
    limit = st.sidebar.slider("Max articles", min_value=5, max_value=50, value=20, step=5)
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Tip: Use keywords for deep-dive, or rely on categories + region for a broad digest.")
    
    # Feed actions
    col_a, col_b = st.sidebar.columns(2)
    fetch_btn = col_a.button("Fetch News")
    clear_btn = col_b.button("Clear Cache")
    
    if clear_btn:
        st.cache_data.clear()
        st.sidebar.success("Cache cleared.")
        st.rerun()  # Refresh to show cleared state

# ---------- HELPERS ----------
@st.cache_data(show_spinner=True, ttl=60*10)
def fetch_articles(topics: List[str], kw: str, country_code: str, limit: int) -> List[Dict]:
    all_articles: List[Dict] = []
    # If keywords present, do an /everything search
    if kw:
        all_articles += search_news(query=kw, page_size=limit)
    # Also fetch per category
    for t in topics:
        cat = t.lower() if t.lower() in {"business","entertainment","general","health","science","sports","technology"} else "general"
        all_articles += search_news(category=cat, country=country_code, page_size=min(limit, 20))
    # Deduplicate by URL
    seen = set()
    uniq = []
    for a in all_articles:
        url = a.get("url")
        if url and url not in seen:
            seen.add(url)
            uniq.append(a)
    return uniq[:limit]

def export_markdown(digest_items: List[Dict]) -> bytes:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Personalized News Digest — {now}", ""]
    for d in digest_items:
        lines.append(f"## {d['title']}")
        lines.append(f"Source: {d.get('source','')}, Published: {d.get('published_at','')}")
        if d.get("summary"):
            lines.append("")
            lines.append(textwrap.fill(d['summary'], width=100))
        lines.append("")
        if d.get("url"):
            lines.append(f"[Read more]({d['url']})")
        lines.append("\n---\n")
    md = "\n".join(lines)
    return md.encode("utf-8")

def export_json(digest_items: List[Dict]) -> bytes:
    return json.dumps(digest_items, indent=2).encode("utf-8")

# ---------- MAIN ----------
if st.session_state.current_view == 'feed':
    st.title("📰 News Feed")
    st.caption("Select interests and generate a categorized, summarized feed. Save and rate articles to view them later.")
    
    if not fetch_btn and not clear_btn and 'articles' in st.session_state:
        fetch_btn = True  # Show existing articles if any
    with st.spinner("Fetching articles…"):
        articles = fetch_articles(selected_topics, keywords.strip(), countries[country], limit)

    if not articles:
        st.warning("No articles returned. Try different interests/keywords.")
    else:
        with st.spinner("Summarizing with Gemini…"):
            summaries = summarize_articles(articles)

        cards = []
        for idx, a in enumerate(articles):
            title = a.get("title") or "Untitled"
            url = a.get("url") or ""
            source = (a.get("source") or {}).get("name", "")
            author = a.get("author") or ""
            published = fmt_date(a.get("publishedAt",""))
            desc = a.get("description") or ""
            img = a.get("urlToImage")
            summary = summaries[idx] if idx < len(summaries) else ""

            col1, col2 = st.columns([1,2])
            with col1:
                if img:
                    st.image(img, use_column_width=True)
                st.caption(source or "—")
                st.caption(published)
            with col2:
                st.subheader(title)
                if desc:
                    st.write(desc)
                if summary:
                    st.markdown(f"*Summary:* {summary}")
                if url:
                    st.link_button("Read full article", url, type="primary")

                # Save & rate controls
                cat = ", ".join(selected_topics) or "General"
                item_key = f"{slugify(title)}_{idx}"
                
                # Initialize rating in session state if not exists
                if item_key not in st.session_state.ratings:
                    st.session_state.ratings[item_key] = 0
                
                # Rating slider
                new_rating = st.slider(
                    "Rate this article", 
                    0, 5, 
                    st.session_state.ratings[item_key],
                    key=f"rating_{item_key}",
                    help="Rate this article (0-5)"
                )
                
                # Update rating in session state when changed
                if new_rating != st.session_state.ratings[item_key]:
                    st.session_state.ratings[item_key] = new_rating
                
                # Prepare item data
                to_save = {
                    "slug": slugify(title),
                    "title": title,
                    "url": url,
                    "source": source,
                    "author": author,
                    "published_at": published,
                    "category": cat,
                    "summary": summary,
                    "rating": st.session_state.ratings[item_key],
                }
                
                # Save button with feedback
                if st.button("Save to My Digest", key=f"save_{item_key}"):
                    save_item(to_save)
                    # Update session state
                    st.session_state.saved_items[item_key] = to_save
                    st.success(f"✓ Saved '{title}'")

            st.divider()
            cards.append(to_save)

        # Export controls
        if cards:
            st.subheader("Export Digest")
            c1, c2 = st.columns(2)
            with c1:
                md_bytes = export_markdown(cards)
                st.download_button("Download Markdown", data=md_bytes, file_name="news_digest.md", mime="text/markdown")
            with c2:
                json_bytes = export_json(cards)
                st.download_button("Download JSON", data=json_bytes, file_name="news_digest.json", mime="application/json")

# Saved Articles View
else:
    st.title("💾 Saved Articles")
    
    # Get all categories from saved items
    saved_categories = list(set([item[7] for item in list_items()]))
    
    # Filter and search
    col1, col2 = st.columns([2, 1])
    with col1:
        search_query = st.text_input("Search saved articles", "", placeholder="Search by title, source, or keyword")
    with col2:
        filter_cat = st.selectbox("Filter by category", ["All"] + saved_categories, key="filter_cat")
    
    # Get and filter saved items
    rows = list_items(category=filter_cat if filter_cat != "All" else None)
    
    if search_query:
        search_lower = search_query.lower()
        rows = [row for row in rows if 
               search_lower in (row[2] or "").lower() or  # title
               search_lower in (row[3] or "").lower() or  # source
               search_lower in (row[8] or "").lower()]    # summary
    
    if not rows:
        st.info("No saved articles yet. Save articles from the News Feed to see them here!")
        if st.button("Go to News Feed", key="go_to_feed_empty"):
            st.session_state.next_view = 'feed'
            st.rerun()
    else:
        # Sort by rating (highest first) and then by date (newest first)
        rows.sort(key=lambda x: (-(x[9] or 0), x[6] or ""), reverse=True)
        
        for row in rows:
            _id, slug, title, url, source, author, published_at, category, summary, rating = row
            item_key = f"saved_{_id}"
            
            # Initialize session state for this item if not exists
            if item_key not in st.session_state.ratings:
                st.session_state.ratings[item_key] = rating or 0
            
            with st.container(border=True):
                # Header with title and source
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"### {title}")
                    st.caption(f"📰 {source or 'Unknown source'} • 📅 {published_at or 'No date'} • 🏷 {category or 'Uncategorized'}")
                
                with col2:
                    if url:
                        st.link_button("🌐 Open Article", url, use_container_width=True)
                
                # Article preview
                if summary:
                    st.markdown("---")
                    st.markdown(summary)
                
                # Actions
                st.markdown("---")
                col_a, col_b, col_c = st.columns([3, 1, 1])
                
                with col_a:
                    # Rating with stars
                    st.write("Your rating:")
                    rating_cols = st.columns(6)
                    for i in range(1, 6):
                        with rating_cols[i-1]:
                            if st.button("★" * i, key=f"rate_{id}{i}"):
                                st.session_state.ratings[item_key] = i
                                update_rating(_id, i)
                                st.rerun()
                    
                    # Display current rating
                    current_rating = st.session_state.ratings[item_key] or 0
                    if current_rating > 0:
                        st.caption(f"Rated: {'★' * current_rating}")
                
                with col_b:
                    if st.button("Go to News Feed", key=f"go_to_feed_saved_{_id}"):
                        st.session_state["next_view"] = "feed"
                        st.rerun()
                
                with col_c:
                    if st.button("🔙 Back to Feed", key=f"back_{_id}", use_container_width=True):
                        st.session_state["next_view"] = 'feed'
                        st.rerun()
                
                st.markdown("---")