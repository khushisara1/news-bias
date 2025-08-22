import os
import io
import json
import textwrap
from datetime import datetime
from typing import List, Dict

import streamlit as st
from dotenv import load_dotenv

from news_client import search_news
from summarizer import summarize_articles
from storage import init_db, save_item, list_items, update_rating, delete_item
from utils import slugify, fmt_date

load_dotenv()
st.set_page_config(page_title="Personalized News Digest", page_icon="🗞️", layout="wide")

# ---------- INIT DB ----------
init_db()

# ---------- SIDEBAR ----------
st.sidebar.title("🗞️ Personalized News Digest")
st.sidebar.caption("Pick interests & frequency, then generate a smart digest.")

INTERESTS = [
    "Technology", "Business", "Science", "Health",
    "Entertainment", "Sports", "Politics", "World",
    "Startup", "AI", "Finance", "Climate"
]
countries = {
    "United States": "us", "India": "in", "United Kingdom": "gb",
    "Canada": "ca", "Australia": "au", "Singapore": "sg", "Germany": "de"
}
freq = st.sidebar.selectbox("Delivery frequency", ["Daily", "Weekly"])
selected_topics = st.sidebar.multiselect("Interests", INTERESTS, default=["Technology","AI"])
country = st.sidebar.selectbox("Region (Top Headlines)", list(countries.keys()), index=0)
keywords = st.sidebar.text_input("Optional keywords (e.g. 'open source, Google')")
limit = st.sidebar.slider("Max articles", min_value=5, max_value=50, value=20, step=5)

st.sidebar.markdown("---")
st.sidebar.caption("Tip: Use keywords for deep-dive, or rely on categories + region for a broad digest.")

# ---------- ACTIONS ----------
col_a, col_b = st.sidebar.columns(2)
fetch_btn = col_a.button("Fetch News")
clear_btn = col_b.button("Clear Cache")

if clear_btn:
    st.cache_data.clear()
    st.sidebar.success("Cache cleared.")

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
        lines.append(f"_Source:_ {d.get('source','')}, _Published:_ {d.get('published_at','')}")
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
st.title("🗞️ Personalized News Digest")
st.caption("Select interests and generate a categorized, summarized feed. Save, rate, and export your digest.")

if fetch_btn:
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
                    st.image(img, use_container_width=True)
                st.caption(source or "—")
                st.caption(published)
            with col2:
                st.subheader(title)
                if desc:
                    st.write(desc)
                if summary:
                    st.markdown(f"**Summary:** {summary}")
                if url:
                    st.link_button("Read full article", url, type="primary")

                # Save & rate controls
                with st.expander("Save & Rate"):
                    rating = st.slider("Rating", 0, 5, 0, key=f"rating_{idx}")
                    cat = ", ".join(selected_topics) or "General"
                    to_save = {
                        "slug": slugify(title),
                        "title": title,
                        "url": url,
                        "source": source,
                        "author": author,
                        "published_at": published,
                        "category": cat,
                        "summary": summary,
                        "rating": rating,
                    }
                    if st.button("Save to My Digest", key=f"save_{idx}"):
                        save_item(to_save)
                        st.success("Saved!")

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

st.markdown("---")
st.header("📁 Saved Digest")
filter_cat = st.selectbox("Filter by category", ["All"] + INTERESTS)
rows = list_items(category=filter_cat)
if not rows:
    st.info("No saved items yet.")
else:
    for row in rows:
        _id, slug, title, url, source, author, published_at, category, summary, rating = row
        with st.container(border=True):
            st.write(f"**{title}**")
            st.caption(f"{source or ''} — {published_at or ''} — {category or ''}")
            if summary:
                st.write(summary)
            if url:
                st.link_button("Open", url)
            r = st.slider("Update rating", 0, 5, rating or 0, key=f"r_{_id}")
            c1, c2 = st.columns(2)
            if c1.button("Save rating", key=f"ur_{_id}"):
                update_rating(_id, r)
                st.success("Rating updated.")
            if c2.button("Delete", type="secondary", key=f"del_{_id}"):
                delete_item(_id)
                st.warning("Deleted.")
