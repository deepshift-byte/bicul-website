"""Produce site/src/data/{en,lg}.json and optimised images in site/public.
lg.json = en.json with every translatable string replaced from the translation memory."""
import json, os, re, sys, shutil, datetime
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from tm import collect, SKIPKEYS, NAME_TITLE_PARENTS

ROOT = "/home/claude/bicul"
SITE = f"{ROOT}/site"
S = json.load(open(f"{ROOT}/content/site_en.json"))
TM = json.load(open(f"{ROOT}/content/tm_lg.json"))

MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
          "lg": ["Janwali", "Febwali", "Marisi", "Apuli", "Maayi", "Juuni", "Julaayi", "Agusito", "Sebuttemba", "Okitobba", "Novemba", "Desemba"]}


def iso(d):
    if not d: return None
    return datetime.datetime.strptime(d, "%B %d, %Y").strftime("%Y-%m-%d")


def fmt(isod, lang):
    if not isod: return None
    y, m, d = isod.split("-")
    return f"{int(d)} {MONTHS[lang][int(m)-1]} {y}" if lang == "lg" else f"{MONTHS['en'][int(m)-1]} {int(d)}, {y}"


# ---------- images ----------
IMG_SRC = f"{ROOT}/data/images"
IMG_OUT = f"{SITE}/public/img"
os.makedirs(IMG_OUT, exist_ok=True)
used = set()
def walk_imgs(o, key=None):
    if isinstance(o, dict):
        for k, v in o.items(): walk_imgs(v, k)
    elif isinstance(o, list):
        for v in o: walk_imgs(v, key)
    elif isinstance(o, str) and re.search(r"\.(jpe?g|png|webp|gif)$", o, re.I) and os.path.exists(f"{IMG_SRC}/{o}"):
        used.add(o)
walk_imgs(S)
IMGMAP = {}
for f in sorted(used):
    src = f"{IMG_SRC}/{f}"
    im = Image.open(src)
    has_alpha = im.mode in ("RGBA", "LA", "P") and ("transparency" in im.info or im.mode in ("RGBA", "LA"))
    w, h = im.size
    base = re.sub(r"\.[^.]+$", "", f)
    longest = 1400
    if max(w, h) > longest:
        k = longest / max(w, h)
        im = im.resize((round(w * k), round(h * k)), Image.LANCZOS); w, h = im.size
    out = f"{base}.webp"
    im = im.convert("RGBA" if has_alpha else "RGB")
    im.save(f"{IMG_OUT}/{out}", "WEBP", quality=78, method=6)
    IMGMAP[f] = {"src": f"/img/{out}", "w": w, "h": h}

# ---------- enrich (dates, image meta) ----------
def enrich(o):
    if isinstance(o, dict):
        n = {}
        for k, v in o.items():
            if k == "date" and isinstance(v, str) and re.match(r"[A-Z][a-z]+ \d{1,2}, \d{4}", v):
                n["iso"] = iso(v)
            n[k] = enrich(v)
        return n
    if isinstance(o, list): return [enrich(v) for v in o]
    if isinstance(o, str) and o in IMGMAP: return IMGMAP[o]
    return o
E = enrich(S)

# ---------- translate ----------
def tr(o, path):
    if isinstance(o, dict):
        n = {}
        for k, v in o.items():
            if k in SKIPKEYS or k in ("iso", "w", "h") or (k == "title" and path and path[0] in NAME_TITLE_PARENTS):
                n[k] = v
            else:
                n[k] = tr(v, path + [k])
        return n
    if isinstance(o, list): return [tr(v, path) for v in o]
    if isinstance(o, str) and o.strip():
        if o not in TM: raise KeyError(f"untranslated: {o[:80]}")
        return TM[o]
    return o

# translation must be keyed on the un-enriched strings; enrichment only touches image/date fields
L = tr(E, [])
# fields kept out of the translation memory because they are names, translated here explicitly
L["contact"]["address"] = "Ekizimbe kya Bulange e Mengo, Omwaliiro ogwa Wansi"
for sec in L["impact"]["sections"]:
    if sec.get("name") == "The Mwanyi Terimba Campaign": sec["name"] = "Kaweefube wa Mwanyi Terimba"
json.dump(E, open(f"{SITE}/src/data/en.json", "w"), ensure_ascii=False)
json.dump(L, open(f"{SITE}/src/data/lg.json", "w"), ensure_ascii=False)

# ---------- static assets ----------
pub = f"{SITE}/public"
os.makedirs(f"{pub}/media", exist_ok=True); os.makedirs(f"{pub}/docs", exist_ok=True)
A = f"{ROOT}/assets"
shutil.copy(f"{A}/vid.mp4", f"{pub}/media/bulange-twekobe.mp4")
Image.open(f"{A}/vid.png").convert("RGB").save(f"{pub}/media/bulange-twekobe.webp", "WEBP", quality=80)
Image.open(f"{A}/0.png").convert("RGBA").save(f"{pub}/logo.png")
ic = Image.open(f"{A}/site-icon.jpg").convert("RGB")
ic.resize((180, 180)).save(f"{pub}/apple-touch-icon.png"); ic.resize((48, 48)).save(f"{pub}/favicon.png")
for f in os.listdir(A):
    if f.endswith(".pdf"): shutil.copy(f"{A}/{f}", f"{pub}/docs/{f}")
print("images", len(IMGMAP), "en/lg written")

# ---------- chatbot knowledge base (both languages, one chunk per page/item) ----------
def text_of(blocks):
    out = []
    for b in blocks or []:
        if b.get("t") in ("p", "h", "quote"): out.append(b["x"])
        elif b.get("t") in ("ul", "ol"): out += ["- " + i for i in b["items"]]
    return "\n".join(out)

LBL = {"en": {"Vision": "Vision", "Mission": "Mission", "Motto": "Motto", "Sector": "Sector", "Contact": "Contact", "Website": "Website", "Also": "Also", "Tel": "Tel"},
       "lg": {"Vision": "Ekirooto", "Mission": "Ekigendererwa", "Motto": "Omulamwa", "Sector": "Ekitundu", "Contact": "Tuukirira", "Website": "Omukutu", "Also": "Era", "Tel": "Essimu"}}
SECT_LG = {"Health": "Ebyobulamu", "Trade & Commerce": "Eby'obusuubuzi", "Media": "Ebyamawulire", "Real Estate": "Amayumba n'ettaka", "Tourism": "Eby'obulambuzi", "Agriculture": "Ebyobulimi", "Education": "Ebyenjigiriza"}
def chunks(D, lang):
    C = []
    T = LBL[lang]
    add = lambda cid, path, title, text: C.append({"id": cid, "path": path, "title": title, "text": re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)})
    H = D["home"]; A = D["about"]
    add("about", "/about", A["title"], "\n".join([H["who_text"]] + A["paras"] + [f"{T['Vision']}: {A['vision']}", f"{T['Mission']}: {A['mission']}", f"{T['Motto']}: {A['motto']}"]
        + [H["triple"]["title"] + ": " + H["triple"]["intro"]] + [f"- {i['title']}: {i['text']}" for i in H["triple"]["items"]]
        + [f"{s['value']} {s['label']}" for s in D["stats"]]))
    W = D["why"]
    add("why", "/invest", W["title"], "\n".join([W["lead"], W["question"]] + ["- " + r for r in W["reasons"]] + W["closing"]
        + [f"{W['ceo']['name']} – {W['ceo']['role']} – {W['ceo']['email']}"]))
    for dv in D["divisions"]:
        parts = [dv["lead"]] + dv["paras"]
        if dv.get("vision"): parts.append(f"{T['Vision']}: {dv['vision']}")
        if dv.get("mission"): parts.append(f"{T['Mission']}: {dv['mission']}")
        parts += ["- " + o for o in dv.get("objectives") or []]
        if dv.get("link"): parts.append(f"{dv['link']['label']}: {dv['link']['url']}")
        parts += [f"{T['Contact']}: {c['name']}, {c['role']}, {c['email']}" + (f", {c['tel']}" if c.get("tel") else "") for c in dv["contacts"]]
        add("div-" + dv["slug"], f"/our-work/{dv['slug']}", dv["title"], "\n".join(parts))
    I = D["impact"]
    add("impact", "/partnerships", I["title"], "\n".join([I["heading"]] + I["intro"] + [I["pillars_title"] + ": " + ", ".join(I["pillars"])]
        + [s["title"] + "\n" + text_of(s["blocks"]) for s in I["sections"]] + [I["closing_title"], I["closing"]]))
    for i, o in enumerate(D["opportunities"]):
        add("opp-" + o["slug"], f"/invest/opportunities/{o['slug']}", o["title"], f"{T['Sector']}: {', '.join(S['opportunities'][i]['categories'] if lang == 'en' else [SECT_LG[x] for x in S['opportunities'][i]['categories']])}\n" + "\n".join(o["summary"]))
    for o in D["programs"] + D["projects"]:
        add("init-" + o["slug"], f"/our-work/initiatives#{o['slug']}", o["title"], text_of(o["body"]))
    for p in D["publications"]:
        add("pub-" + p["slug"], "/publications", p["title"], text_of(p["body"]) + "\nPDF: /docs/" + p["downloads"][0]["file"])
    for s in D["subsidiaries"]:
        add("sub-" + s["slug"], f"/partnerships/subsidiaries/{s['slug']}", s["name"], text_of(s["body"]) + ("\n" + T["Website"] + ": " + s["website"] if s.get("website") else ""))
    add("partners", "/partnerships/partners", "Partners", ", ".join(p["name"] for p in D["partners"]))
    P = D["people"]
    add("board", "/leadership#board", "Board", P["board_intro"] + "\n" + "\n".join(f"- {p['name']}: {p['role']}" for p in P["board"]))
    add("advisory", "/leadership#advisory", "Advisory committee", "\n".join(f"- {p['name']}" for p in P["advisory"]))
    add("team", "/leadership#team", "Team", P["team_intro"] + "\n" + "\n".join(f"- {p['name']}: {p['role']}" for p in P["team"]))
    for n in D["news"]:
        add("news-" + n["slug"], f"/news/{n['slug']}", n["title"], (n.get("iso") or "") + "\n" + text_of(n["body"]))
    c = D["contact"]
    add("contact", "/contact", c["title"], f"{c['address']}\nEmail: {c['email']}\n{T['Tel']}: {c['tel']}\n{T['Also']}: {D['footer']['phone_display']}\nFacebook, Instagram, X: " + ", ".join(D['footer']['social']))
    for doc in D["partnership_docs"]:
        add("doc-" + doc["slug"], "/partnerships/guidelines", doc["title"], doc["body"])
    return C

def overviews(D, lang):
    """Summary chunks so broad questions get a complete answer."""
    sec = (lambda x: x) if lang == "en" else (lambda x: SECT_LG[x])
    ac = "acres" if lang == "en" else "yiika"
    rows = []
    for i, o in enumerate(D["opportunities"]):
        m = re.search(r"(\d[\d,]*)\s+(?:acres|yiika)|[Yy]iika\s+(\d[\d,]*)", o["summary"][0])
        size = (m.group(1) or m.group(2)) if m else None
        rows.append(f"- {o['title']} ({', '.join(sec(c) for c in S['opportunities'][i]['categories'])}{', ' + size + ' ' + ac if size else ''}): {o['summary'][0]}")
    T = {"en": ("All investment opportunities", "All subsidiaries", "Our divisions"), "lg": ("Emikisa gyonna egy'okusiga ensimbi", "Kampuni zonna ezikola wansi wa BICUL", "Ebitongole byaffe")}[lang]
    P = D["people"]; W = D["why"]
    lead_title = {"en": "Leadership: CEO and board", "lg": "Abakulembeze: Ssenkulu n'olukiiko olufuzi"}[lang]
    lead = [f"{W['ceo']['role']}: {W['ceo']['name']} ({W['ceo']['email']})"] + [f"- {x['name']}: {x['role']}" for x in P["board"]]
    return [
        {"id": "ov-lead", "path": "/leadership", "title": lead_title, "text": "\n".join(lead)},
        {"id": "ov-opps", "path": "/invest/opportunities", "title": T[0], "text": "\n".join(rows)},
        {"id": "ov-subs", "path": "/partnerships/subsidiaries", "title": T[1], "text": "\n".join(f"- {x['name']}" + (f" ({x['website']})" if x.get('website') else "") for x in D["subsidiaries"])},
        {"id": "ov-divs", "path": "/about", "title": T[2], "text": "\n".join(f"- {d['title']}: {d['summary']}" for d in D["divisions"])},
    ]

KB = {"en": overviews(E, "en") + chunks(json.loads(json.dumps(E)), "en"), "lg": overviews(L, "lg") + chunks(json.loads(json.dumps(L)), "lg")}
# bilingual keywords for common questions (boost matching for short, everyday phrasing)
KW = {
    "about": "what does bicul do, what is bicul, who are you, about bicul, about you, mission, vision, motto, holding company, investment arm, ekola ki, bakola ki, mukola ki, ffe baani, bitukwatako, ekigendererwa, ekirooto, omulamwa",
    "contact": "contact, phone, telephone, call, email, address, office, location, where are you, reach you, visit you, appointment, tuukirira, tukwatagane, essimu, kuba essimu, wandiikira, ofiisi, esangibwa wa, endagiriro, okusisinkana",
    "why": "why invest, why buganda, lwaki nsiga, lwaki osiga, lwaki buganda",
    "ov-lead": "ceo, chief executive, managing director, who heads, who leads, head of bicul, leadership, leaders, chairman, ssenkulu, akulira bicul, abakulembeze, ssentebe",
    "ov-opps": "land, farm, farming, farmland, acres, agriculture land, opportunities, available, plots, real estate, invest in, ttaka, okulima, okulimirako, yiika, emikisa, faamu, okusiga ensimbi",
    "ov-subs": "subsidiaries, subsidiary, companies, commercial arms, institutions owned, kampuni, ebitongole by'obusuubuzi",
    "ov-divs": "divisions, departments, units, what work, ebitongole, emirimu gyammwe",
    "board": "board, directors, chairman, chairperson, board members, olukiiko olufuzi, ssentebe",
    "team": "staff, team, employees, workers, abakozi, ttiimu",
    "partners": "partners, partner organisations, donors, who do you work with, bannamukago",
    "impact": "social impact, csr, community programmes, campaigns, kaweefube, okukyusa embeera",
}
for lang in ("en", "lg"):
    for c in KB[lang]: c["kw"] = KW.get(c["id"], "")
# chunk titles that are names stay as they are; translate the two fixed labels
for c in KB["lg"]:
    c["title"] = {"Partners": "Bannamukago", "Board": "Olukiiko Olufuzi", "Advisory committee": "Akakiiko Akawabuzi", "Team": "Abakozi"}.get(c["title"], c["title"])
merged = [{"id": a["id"], "path": a["path"], "kw": a["kw"], "en": {"title": a["title"], "text": a["text"]}, "lg": {"title": b["title"], "text": b["text"]}} for a, b in zip(KB["en"], KB["lg"])]
assert all(a["id"] == b["id"] for a, b in zip(KB["en"], KB["lg"]))
json.dump(merged, open(f"{SITE}/public/kb.json", "w"), ensure_ascii=False)
json.dump(merged, open(f"{SITE}/src/data/kb.json", "w"), ensure_ascii=False)
print("kb chunks", len(merged), "chars en", sum(len(c["en"]["text"]) for c in merged))
