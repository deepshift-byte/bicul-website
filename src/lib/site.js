import en from "../data/en.json";
import lg from "../data/lg.json";
import { ui, href } from "../i18n/ui.js";

export const DATA = { en, lg };
export const t = (lang) => ui[lang];
export const data = (lang) => DATA[lang];

// getStaticPaths helpers: English at the root, Luganda under /lg
export const langParams = () => [{ params: { lang: undefined } }, { params: { lang: "lg" } }];
export const langOf = (param) => (param === "lg" ? "lg" : "en");
export function withLangs(itemsFn) {
  const out = [];
  for (const lang of ["en", "lg"]) {
    for (const p of itemsFn(lang)) out.push({ params: { lang: lang === "lg" ? "lg" : undefined, ...p.params }, props: { ...(p.props || {}), lang } });
  }
  return out;
}

export { href };

// Navigation tree (labels from ui strings)
export function nav(lang) {
  const u = ui[lang];
  const h = (p) => href(lang, p);
  return [
    { label: u.about, items: [
      { label: u.whoWeAre, href: h("/about") },
      { label: u.leadership, href: h("/leadership") },
    ] },
    { label: u.ourWork, items: [
      ...DATA[lang].divisions.map((d) => ({ label: d.title, href: h(`/our-work/${d.slug}`) })),
      { label: u.initiatives, href: h("/our-work/initiatives") },
    ] },
    { label: u.invest, items: [
      { label: u.whyInvest, href: h("/invest") },
      { label: u.opportunities, href: h("/invest/opportunities") },
    ] },
    { label: u.partnerships, items: [
      { label: u.socialImpact, href: h("/partnerships") },
      { label: u.partners, href: h("/partnerships/partners") },
      { label: u.subsidiaries, href: h("/partnerships/subsidiaries") },
      { label: u.partnershipDocs, href: h("/partnerships/guidelines") },
    ] },
    { label: u.newsMedia, items: [
      { label: u.news, href: h("/news") },
      { label: u.publications, href: h("/publications") },
      { label: u.gallery, href: h("/gallery") },
    ] },
    { label: u.contact, href: h("/contact") },
  ];
}

// Text helpers
const EMOJI = /^[\p{Extended_Pictographic}‍️\p{Emoji_Modifier}\s]+/u;
export const stripEmoji = (s) => (s || "").replace(EMOJI, "");

export function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
// [text](url) -> <a>, newlines -> <br>
export function inline(s) {
  const parts = [];
  let last = 0;
  const re = /\[([^\]]+)\]\(([^)\s]+)\)/g;
  let m;
  const src = stripEmoji(s);
  while ((m = re.exec(src))) {
    parts.push(esc(src.slice(last, m.index)));
    const ext = /^https?:/.test(m[2]);
    parts.push(`<a href="${esc(m[2])}"${ext ? ' rel="noopener" target="_blank"' : ""}>${esc(m[1])}</a>`);
    last = m.index + m[0].length;
  }
  parts.push(esc(src.slice(last)));
  return parts.join("").replace(/\n/g, "<br>");
}

export function acres(text) {
  const m = /(\d[\d,]*)\s+(?:acres|yiika)|yiika\s+(\d[\d,]*)|Yiika\s+(\d[\d,]*)/.exec(text || "");
  return m ? (m[1] || m[2] || m[3]) : null;
}

export function sectorSlug(s) {
  return s.toLowerCase().replace(/&/g, "and").replace(/[^a-z]+/g, "-").replace(/(^-|-$)/g, "");
}

// Map English sector names (data keeps English keys) to display names
export const sectorLabel = (lang, s) => ui[lang].sectors[s] || s;

// Sector keys always come from the English data so filters match in both languages
export function opportunitySectors(lang) {
  return DATA.en.opportunities.map((o) => o.categories);
}
