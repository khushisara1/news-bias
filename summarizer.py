import os
from typing import List, Dict
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st

load_dotenv()

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found. Set it in .env or Streamlit secrets.")

genai.configure(api_key=GEMINI_API_KEY)
MODEL = genai.GenerativeModel("gemini-1.5-flash")
SUMMARY_PROMPT = """You are a helpful news editor. For each article, write a crisp 2–3 line summary.
- Be neutral and factual
- Avoid sensationalism
- Include the 'so what' in one short sentence
Return results as bullet points."""

def summarize_articles(articles: List[Dict]) -> List[str]:
    """
    Batch summarize by sending compact text to Gemini to save tokens.
    """
    if not articles:
        return []

    bullets_input = []
    for i,a in enumerate(articles, start=1):
        title = a.get("title","").strip()
        desc = a.get("description") or ""
        content = a.get("content") or ""
        url = a.get("url","")
        compact = f"{i}. {title}\n{desc}\n{content}\nSource: {url}\n"
        bullets_input.append(compact)

    prompt = SUMMARY_PROMPT + "\n\n" + "\n".join(bullets_input[:20])  # cap per batch
    resp = MODEL.generate_content(prompt)
    text = (resp.text or "").strip()

    # Split lines into summaries (fallback: repeat trimmed lines)
    lines = [l.strip("-• ").strip() for l in text.split("\n") if l.strip()]
    # best-effort mapping: pad/truncate to len(articles)
    if len(lines) < len(articles):
        lines += ["(summary unavailable)"] * (len(articles)-len(lines))
    return lines[:len(articles)]