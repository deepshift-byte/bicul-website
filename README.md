# BICUL website

Bilingual (English / Luganda) website for **Buganda Investment and Commercial Undertaking Ltd (BICUL)**, the investment arm of the Buganda Kingdom. Built with [Astro](https://astro.build) and deployed on Vercel.

- English pages live at `/…`, Luganda pages at `/lg/…`. Every page exists in both languages; the EN | LG switch in the header keeps you on the same page.
- A visitor who picks Luganda is taken to the Luganda home page on their next visit.
- The **BICUL assistant** (floating button, bottom right) answers questions in English or Luganda using only the website's content.

## Content

All text was taken from the previous bicul.co.ug website (scraped November 2026); nothing was invented.

| File | What it holds |
| --- | --- |
| `src/data/en.json` | All English content (pages, opportunities, subsidiaries, partners, people, news, publications) |
| `src/data/lg.json` | The same content in Luganda |
| `src/i18n/ui.js` | Menu, button and label text in both languages |
| `src/data/kb.json`, `public/kb.json` | Chatbot knowledge base (both languages), generated from the content |
| `translations/review.csv` | Every English passage beside its Luganda translation, for review by a native speaker |
| `public/img`, `public/docs`, `public/media` | Photos (WebP), publication PDFs, home-page video |

`scripts/` contains the Python scripts used to scrape the old site, structure the content, apply the translation memory and build the knowledge base. They are kept for reference; edit `src/data/*.json` directly for day-to-day changes.

## Chatbot

The assistant works in two modes:

1. **With an Anthropic API key** — set `ANTHROPIC_API_KEY` in the Vercel project (Settings → Environment Variables) and redeploy. `/api/chat` then answers with Claude (`claude-sonnet-5-5` by default; override with `CHAT_MODEL`), grounded strictly on the website content, replying in the visitor's language.
2. **Without a key** — the widget answers in the browser by searching the knowledge base and quoting the matching page, with links.

`GET /api/chat` reports whether the AI mode is active.

## Develop

```bash
npm install
npm run dev      # http://localhost:4321
npm run build
```

Requires Node 20+.
