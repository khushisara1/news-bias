# 🗞️ Personalized News Digest (Streamlit + NewsAPI + Gemini)

A dashboard to select interests & frequency, fetch news with NewsAPI, summarize with Gemini, and save/rate/export your digests.

## Features
- Topic & region selection
- Keyword search
- Gemini-based summaries (2–3 lines)
- Save items to SQLite
- Rate items (0–5 stars)
- Export digest as Markdown or JSON
- Caching for faster runs

## Setup

```bash
git clone <your-repo>
cd news_digest
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# fill NEWSAPI_KEY and GEMINI_API_KEY in .env
streamlit run streamlit_app.py
