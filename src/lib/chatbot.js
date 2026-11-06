// BICUL chatbot (client). Uses /api/chat (Claude, grounded on the site) when available,
// otherwise answers directly from the site's own knowledge base (/kb.json).

const LG_HINTS = /\b(ki|kiki|nga|oba|era|ani|wa|ba|bwa|lya|gya|kya|ku|mu|naye|nnyinza|ntya|lwaki|ddi|wa?ngi|obwakabaka|ekitongole|ensimbi|ettaka|bannamukago|amawulire|ssenkulu|tukwatagane|webale|gyebale|oli otya|ndi|nze|osobola|nsaba|njagala|mmanyi|ebikwata|kampuni|emikisa|okusiga|yiika|bannakyalo|abakozi)\b/i;
const EN_HINTS = /\b(the|what|who|how|where|when|which|is|are|do|does|can|i|you|about|land|invest|contact|email|phone|ceo|board|partner|news)\b/i;

const LOCAL = {
  en: { hi: "Hello! How can I help you with BICUL today?", thanks: "You're welcome. Anything else about BICUL?" },
  lg: { hi: "Ki kati! Nkuyambe ntya ku bikwata ku BICUL leero?", thanks: "Kale, tewali buzibu. Waliwo ekirala ky'oyagala okumanya ku BICUL?" },
};

const STOP = new Set(("a an the of and or to in on for is are was were be with by at from as that this it its what who how where when which do does can i you me my our we about tell please " +
  "ki kiki nga oba era ani wa ba bwa lya gya kya ku mu naye ntya ddi nze ndi osobola nsaba njagala mmanyi ebikwata nnyinza " +
  "bicul buganda kingdom obwakabaka ltd limited").split(" "));

const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[’']/g, "'");
const tokens = (s) => norm(s).split(/[^a-z0-9']+/).filter((w) => w.length > 1 && !STOP.has(w));

function esc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function md(text) {
  const blocks = esc(text.trim()).split(/\n{2,}/);
  return blocks.map((b) => {
    const lines = b.split("\n");
    const linkify = (s) => s
      .replace(/\[([^\]]+)\]\(((?:https?:\/\/|\/|mailto:|tel:)[^)\s]+)\)/g, (m, t, u) => `<a href="${u}"${u.startsWith("http") ? ' target="_blank" rel="noopener"' : ""}>${t}</a>`)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|\s)(info@bicul\.co\.ug|[a-z]+@bicul\.co\.ug)/g, '$1<a href="mailto:$2">$2</a>');
    if (lines.every((l) => /^\s*[-•*]\s+/.test(l))) return "<ul>" + lines.map((l) => `<li>${linkify(l.replace(/^\s*[-•*]\s+/, ""))}</li>`).join("") + "</ul>";
    return `<p>${lines.map(linkify).join("<br>")}</p>`;
  }).join("");
}

export function initChatbot() {
  const root = document.querySelector(".cb");
  if (!root) return;
  const pageLang = root.dataset.lang === "lg" ? "lg" : "en";
  const S = JSON.parse(root.querySelector("[data-cb-strings]").textContent);
  const fab = root.querySelector("[data-cb-open]");
  const panel = root.querySelector(".cb__panel");
  const log = root.querySelector("[data-cb-log]");
  const form = root.querySelector("[data-cb-form]");
  const input = root.querySelector("[data-cb-input]");
  const suggest = root.querySelector("[data-cb-suggest]");
  const history = [];
  let kb = null;
  let apiAvailable = true;
  let busy = false;

  try { if (sessionStorage.getItem("bicul-chat-opened")) root.dataset.opened = "true"; } catch (e) {}

  const add = (role, html, links) => {
    const el = document.createElement("div");
    el.className = `cb-msg cb-msg--${role}`;
    el.innerHTML = html;
    if (links && links.length) {
      const l = document.createElement("div");
      l.className = "cb-msg__links";
      l.innerHTML = `<span>${esc(S.sources)}</span>` + links.map((x) => `<a href="${x.href}">${esc(x.title)}</a>`).join("");
      el.appendChild(l);
    }
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  };

  const open = () => {
    panel.hidden = false;
    fab.setAttribute("aria-expanded", "true");
    root.dataset.opened = "true";
    try { sessionStorage.setItem("bicul-chat-opened", "1"); } catch (e) {}
    if (!log.children.length) {
      add("bot", md(S.greeting));
      suggest.innerHTML = S.suggestions.map((q) => `<button type="button">${esc(q)}</button>`).join("");
    }
    setTimeout(() => input.focus(), 30);
  };
  const close = () => { panel.hidden = true; fab.setAttribute("aria-expanded", "false"); fab.focus(); };
  fab.addEventListener("click", () => (panel.hidden ? open() : close()));
  root.querySelector("[data-cb-close]").addEventListener("click", close);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) close(); });
  suggest.addEventListener("click", (e) => { if (e.target.tagName === "BUTTON") ask(e.target.textContent); });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
  input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 120) + "px"; });
  form.addEventListener("submit", (e) => { e.preventDefault(); const q = input.value.trim(); if (q) ask(q); });

  function detectLang(q) {
    const lg = LG_HINTS.test(q), en = EN_HINTS.test(q);
    if (lg && !en) return "lg";
    if (en && !lg) return "en";
    return pageLang;
  }
  const pathFor = (lang, p) => (lang === "lg" ? "/lg" + p : p);

  async function loadKb() {
    if (kb) return kb;
    const r = await fetch("/kb.json");
    kb = await r.json();
    // precompute token bags for both languages
    for (const c of kb) {
      c._t = {};
      for (const l of ["en", "lg"]) {
        const bag = new Map();
        for (const w of tokens(c[l].title + " " + c[l].title + " " + c[l].text)) bag.set(w, (bag.get(w) || 0) + 1);
        c._t[l] = bag;
      }
      c._kw = (c.kw || "").split(",").map((x) => norm(x).trim()).filter(Boolean);
    }
    return kb;
  }

  function search(q, lang) {
    const qs = tokens(q);
    const raw = " " + norm(q).replace(/[^a-z0-9' ]+/g, " ").replace(/\s+/g, " ") + " ";
    const kwScore = (c) => c._kw.reduce((a, k) => a + ((k.length > 5 ? raw.includes(k) : raw.includes(" " + k + " ")) ? 14 + k.split(" ").length * 3 : 0), 0);
    if (!qs.length && !kb.some((c) => kwScore(c) > 0)) return [];
    const N = kb.length;
    const df = (w) => kb.filter((c) => c._t.en.has(w) || c._t.lg.has(w) || [...c._t.en.keys(), ...c._t.lg.keys()].some((k) => k.startsWith(w) && w.length > 3)).length || 1;
    const scored = kb.map((c) => {
      let s = 0;
      for (const w of qs) {
        const idf = Math.log(1 + N / df(w));
        for (const l of ["en", "lg"]) {
          let tf = c._t[l].get(w) || 0;
          if (!tf && w.length > 3) for (const [k, v] of c._t[l]) if (k.startsWith(w) || w.startsWith(k) && k.length > 3) tf += v * .6;
          s += (tf ? (1 + Math.log(tf)) * idf : 0) * (l === lang ? 1 : .8);
        }
        if (norm(c[lang].title).includes(w)) s += 2 * idf;
      }
      s += kwScore(c);
      return { c, s };
    }).filter((x) => x.s > 0).sort((a, b) => b.s - a.s);
    return scored;
  }

  function excerpt(text, q) {
    const qs = tokens(q);
    const isList = text.split("\n").filter((l) => l.startsWith("- ")).length > 3;
    const parts = (isList ? text.split("\n") : text.split(/(?<=[.!?])\s+(?=[A-Z“"(])|\n/)).map((x) => x.trim()).filter(Boolean);
    const df = (w) => parts.filter((p) => norm(p).includes(w)).length || 1;
    const ranked = parts.map((p, i) => ({ p, i, s: qs.reduce((a, w) => a + (norm(p).includes(w.length > 4 ? w.slice(0, -2) : w) ? 1 / df(w) : 0), 0) }));
    let pick = ranked.filter((x) => x.s > 0).sort((a, b) => b.s - a.s || a.i - b.i).slice(0, isList ? 6 : 4).sort((a, b) => (isList ? b.s - a.s : 0) || a.i - b.i).map((x) => x.p);
    if (!pick.length) pick = parts.slice(0, 3);
    if (text.length <= 900) return text;
    const out = pick.join("\n");
    return out.length > 700 ? out.slice(0, 680).replace(/\s+\S*$/, "") + "…" : out;
  }

  async function offlineAnswer(q, lang) {
    await loadKb();
    const hits = search(q, lang);
    if (!hits.length || hits[0].s < 1.2) return { html: md(S.noAnswer) };
    const top = hits[0].c;
    const body = excerpt(top[lang].text, q);
    const links = hits.slice(0, 3).filter((h, i) => i === 0 || h.s > hits[0].s * .45)
      .map((h) => ({ title: h.c[lang].title, href: pathFor(lang, h.c.path) }));
    return { html: md(`**${top[lang].title}**\n${body}`), links };
  }

  async function ask(q) {
    if (busy) return;
    busy = true;
    suggest.innerHTML = "";
    input.value = ""; input.style.height = "auto";
    add("user", md(q));
    const lang = detectLang(q);
    const nq = norm(q).trim();
    if (/^(hi|hello|hey|good (morning|afternoon|evening)|ki kati|oli otya|gyebale|gyebale ko|wasuze otya|osiibye otya)[!. ]*$/.test(nq)) {
      add("bot", md(LOCAL[lang].hi)); busy = false; return;
    }
    if (/^(thanks|thank you|webale|webale nnyo|mwebale)[!. ]*$/.test(nq)) {
      add("bot", md(LOCAL[lang].thanks)); busy = false; return;
    }
    const wait = add("bot", `<span class="cb-typing">${esc(S.thinking)}</span>`);
    history.push({ role: "user", content: q });
    try {
      let answered = false;
      if (apiAvailable) {
        try {
          const r = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lang, pageLang, path: location.pathname, messages: history.slice(-8) }) });
          if (r.ok) {
            const j = await r.json();
            if (j.reply) {
              wait.innerHTML = md(j.reply);
              history.push({ role: "assistant", content: j.reply });
              answered = true;
            }
          } else if (r.status === 503 || r.status === 404) {
            apiAvailable = false;
          }
        } catch (e) { apiAvailable = false; }
      }
      if (!answered) {
        const a = await offlineAnswer(q, lang);
        wait.remove();
        add("bot", a.html, a.links);
        history.push({ role: "assistant", content: a.html.replace(/<[^>]+>/g, " ") });
      }
    } catch (e) {
      wait.innerHTML = md(S.error);
    }
    log.scrollTop = log.scrollHeight;
    busy = false;
  }
}
