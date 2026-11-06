// POST /api/chat — answers questions about BICUL using only the website's content.
// Needs ANTHROPIC_API_KEY in the Vercel project's environment variables. Without it the
// endpoint returns 503 and the chat widget falls back to answering from /kb.json in the browser.
import Anthropic from "@anthropic-ai/sdk";
import kb from "../../data/kb.json";

export const prerender = false;

const MODEL = process.env.CHAT_MODEL || "claude-sonnet-5-5";

const KB_EN = kb.map((c) => `### ${c.en.title}\nURL: ${c.path}\n${c.en.text}`).join("\n\n");

const tok = (s) => s.toLowerCase().split(/[^a-z0-9']+/).filter((w) => w.length > 3);
function luganda(q, n = 8) {
  const qs = new Set(tok(q));
  return kb.map((c) => ({ c, s: tok(c.lg.title + " " + c.lg.text + " " + c.en.title + " " + c.en.text).filter((w) => qs.has(w)).length }))
    .filter((x) => x.s > 0).sort((a, b) => b.s - a.s).slice(0, n)
    .map(({ c }) => `### ${c.lg.title}\nURL: /lg${c.path}\n${c.lg.text}`).join("\n\n");
}

function system(lang, q) {
  const lgRef = luganda(q);
  return `You are the BICUL assistant on the official website of Buganda Investment and Commercial Undertaking Ltd (BICUL), the investment arm of the Buganda Kingdom in Uganda.

Rules:
- Answer ONLY from the BICUL website content below. If the answer is not there, say you could not find it on the BICUL website and suggest contacting info@bicul.co.ug or +256 708 400 208. Never invent names, numbers, dates, prices, land sizes or contacts.
- Reply in ${lang === "lg" ? "Luganda" : "English"} unless the visitor clearly writes in the other language; then reply in the visitor's language. When replying in Luganda, write natural, respectful Luganda and keep personal names, organisation names, emails and phone numbers exactly as written.
- Be concise: 2–6 sentences or a short list. Use plain text with optional **bold** and "- " bullets.
- When useful, end with one relevant page link in Markdown, e.g. [Jeza Agriculture Land](${lang === "lg" ? "/lg" : ""}/invest/opportunities/jeza-agriculture-land). Use ${lang === "lg" ? "the /lg prefix (Luganda pages)" : "paths without the /lg prefix (English pages)"}.
- Be warm and respectful of the Kingdom (Kabaka, Katikkiro, Nnaabagereka are titles; keep them).

# BICUL website content (English)
${KB_EN}
${lgRef ? `\n# Matching Luganda text from the website (use its wording when replying in Luganda)\n${lgRef}` : ""}`;
}

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });

export async function POST({ request }) {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) return json({ error: "chat_unavailable" }, 503);
  let body;
  try { body = await request.json(); } catch { return json({ error: "bad_request" }, 400); }
  const lang = body.lang === "lg" ? "lg" : "en";
  const messages = (Array.isArray(body.messages) ? body.messages : [])
    .filter((m) => (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
    .slice(-8)
    .map((m) => ({ role: m.role, content: m.content.slice(0, 1200) }));
  while (messages.length && messages[0].role !== "user") messages.shift();
  if (!messages.length || messages.at(-1).role !== "user") return json({ error: "bad_request" }, 400);

  try {
    const client = new Anthropic({ apiKey: key });
    const res = await client.messages.create({
      model: MODEL,
      max_tokens: 700,
      system: [{ type: "text", text: system(lang, messages.at(-1).content), cache_control: { type: "ephemeral" } }],
      messages,
    });
    const reply = res.content.filter((b) => b.type === "text").map((b) => b.text).join("\n").trim();
    return json({ reply });
  } catch (e) {
    console.error("chat error", e?.status, e?.message);
    return json({ error: "upstream" }, 502);
  }
}

export function GET() {
  return json({ ok: true, ai: Boolean(process.env.ANTHROPIC_API_KEY) });
}
