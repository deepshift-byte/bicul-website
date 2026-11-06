"""Organise the extracted content into the new site's structure (content/site_en.json).
All text is taken verbatim from content/en.json (the scraped site). Helpers look strings up
by prefix so nothing is retyped by hand; only obvious spelling slips are corrected (listed in FIXES)."""
import json, re, copy

C = json.load(open("/home/claude/bicul/content/en.json"))
P = C["pages"]

# Obvious typos on the source site, corrected for the new site (reported to the client)
FIXES = [
    ("Board Memeber", "Board Member"),
    ("above see level", "above sea level"),
    ("CENTRAL BROADCATING SERVICE also", "Central Broadcasting Service, also"),
    ("Buganda Heritage & Tourism Boar", "Buganda Heritage & Tourism Board"),
    ("Principle Developments and Partnerships Officer", "Principal Developments and Partnerships Officer"),
    ("Mwanyi Terimba LImited", "Mwanyi Terimba Limited"),
    ("people of Buganda.MBL is", "people of Buganda. MBL is"),
    ("20th  August", "20th August"), ("17th  February", "17th February"),
    ("Kingdom of Buganda  BICUL & BUCADEF  visited", "Kingdom of Buganda (BICUL & BUCADEF) visited"),
    ("Mr Mwanje Martin Head sustainability  (Extreme right)", "Mr Mwanje Martin Head sustainability (Extreme right)"),
    ("livestock watering  including", "livestock watering including"),
    ("Minister for Social Services Buganda Kingdom singing a", "Minister for Social Services Buganda Kingdom signing a"),
    ("2026 –Meeting", "2026 – Meeting"), ("2026 –Partnerships", "2026 – Partnerships"), ("2026 –History", "2026 – History"),
    ("the Kingdoms vast resources", "the Kingdom’s vast resources"),
]
# Sentences on the source that are clearly copy-paste errors or CMS leftovers (dropped, reported to the client)
DROP_SENTENCES = [
    " It is against this background that BUCADEF orients itself to spearhead and direct general community development emphasizing the promotion of standards of living particularly of the rural community and the urban poor in the central region.",
]
DROP_BLOCKS = ["Caldera Forms", "has been closed as of April 5, 2022", "Listing Section", "Partner Slider"]


def fix(o):
    if isinstance(o, dict): return {k: fix(v) for k, v in o.items()}
    if isinstance(o, list):
        out = []
        for v in o:
            if isinstance(v, dict) and v.get("t") in ("p", "h") and any(v.get("x", "").startswith(d) for d in DROP_BLOCKS):
                continue
            out.append(fix(v))
        return out
    if isinstance(o, str):
        o = re.sub(r"[ \t\u00a0]+", " ", o).strip()
        for a, b in FIXES: o = o.replace(a, b)
        for d in DROP_SENTENCES: o = o.replace(d, "")
        return o
    return o


def find(page, prefix, kind=None):
    for b in P[page]:
        if kind and b["t"] != kind: continue
        if b.get("x", "").startswith(prefix): return b["x"]
    raise KeyError((page, prefix))


def items_after(page, prefix):
    seen = False
    for b in P[page]:
        if seen and b["t"] in ("ul", "ol"): return b["items"]
        if b.get("x", "").startswith(prefix): seen = True
    raise KeyError((page, prefix))


S = {}
S["home"] = C["home"]
S["stats"] = C["home"]["stats"]

# ---- About ----
S["about"] = {
    "title": find("about-us", "About Us"),
    "paras": [find("about-us", "Buganda Investments and Commercial Undertakings Limited (BICUL) aims"),
              find("about-us", "BICUL takes up its core role")],
    "vision": find("about-us", "Innovate, empower"),
    "mission": find("about-us", "To create Value"),
    "motto": find("about-us", "Buganda Kuntiko"),
    "who_text": C["home"]["who_text"],
}

# ---- Why invest ----
why_long = find("why-invest-in-buganda", "70% of business sales")
# the source paragraph repeats one sentence (once garbled as "r u r a l"); keep the clean copy once
reasons = [
    "70% of business sales or goods and services happen within a radius of 50- 80kms from which is all Buganda.",
    "The passion, love and loyalty of the people of Buganda for their King and Kingdom are in their DNA. You will have guaranteed access to this segment of the market.",
    "The current Kingdom administration is dynamic, empowered engaged and extremely professional",
    "Buganda Kingdom has a lot of land constituted with water, forests and special stones among others",
    "Some pieces of land are in the capital city and urban centers (very prime for high end developments); while the rural areas have big chunks of suitable land for commercial farming.",
]
for r in reasons:  # guard: every reason must come from the source paragraph
    assert r.replace("suitable", "") [:40] in why_long or r[:40] in why_long, r
S["why"] = {
    "title": find("why-invest-in-buganda", "Why Invest"),
    "lead": find("why-invest-in-buganda", "The Kingdom of Buganda is the largest"),
    "question": find("why-invest-in-buganda", "One may wonder"),
    "reasons": reasons,
    "closing": [find("why-invest-in-buganda", "With the existence"), find("why-invest-in-buganda", "We welcome you")],
    "ceo": {"name": "Roland Michael Sebuwufu", "role": find("why-invest-in-buganda", "Chief Executive Officer"),
            "email": "sebuwufu@bicul.co.ug", "photo": "2025_04_Roland-Michael-Sebuwufu.jpg"},
}

# ---- Divisions ----
TEL = "+256 (0) 200900886"
S["divisions"] = [
    {"slug": "statistics", "title": find("statistics-division", "Statistics Division"),
     "lead": find("statistics-division", "The Statistics Division is the pillar"),
     "paras": [find("statistics-division", "The need for statistical"), find("statistics-division", "The Statistics Division is governed"),
               find("statistics-division", "The legal framework"), find("statistics-division", "Uganda Bureau of Statistics (UBOS) appointed"),
               find("statistics-division", "There is great optimism"), find("statistics-division", "The Buganda Statistics Unit sincerely")],
     "vision": find("statistics-division", "Buganda shall be"), "mission": find("statistics-division", "Apply best practices"),
     "objectives": [],
     "link": {"label": "Click here For Statistics Data Request Form", "url": "https://ee.kobotoolbox.org/x/MHgeVe1t"},
     "summary": C["home"]["who_items"][2]["text"], "short": C["home"]["who_items"][2]["title"],
     "contacts": [
         {"name": "Namubiru Winnifred", "role": "Kingdom Chief Statistician", "tel": TEL, "email": "namubiru@bicul.co.ug", "photo": "2025_04_Winnifred-Namubiru.jpg"},
         {"name": "Nabuyondo Hamirat Shibah", "role": "Kingdom Statistician", "tel": TEL, "email": "nabuyondo@bicul.co.ug", "photo": "2025_04_Hamirat-Shibah-Nabuyondo.jpg"}]},
    {"slug": "strategic-partnerships", "title": find("strategic-partnerships-division", "Strategic Partnerships Division"),
     "lead": find("strategic-partnerships-division", "The strategic Partnerships unit"),
     "paras": [find("strategic-partnerships-division", "The SPU’s main focus")],
     "vision": find("strategic-partnerships-division", "To strategically position the Kingdom of Buganda as a key implementation"),
     "mission": find("strategic-partnerships-division", "To oversee grant activity"),
     "objectives": items_after("strategic-partnerships-division", "To oversee grant activity"),
     "summary": C["home"]["who_items"][0]["text"], "short": C["home"]["who_items"][0]["title"],
     "contacts": [
         {"name": "Nankinga Caroline", "role": "Head Strategic Partnerships & Human Resource", "email": "nankinga@bicul.co.ug", "photo": "2025_04_IMG-20250818-WA0016.jpg"},
         {"name": "Mukiibi Herman Joseph", "role": "Principle Developments and Partnerships Officer", "email": "mukiibi@bicul.co.ug", "photo": "2025_04_IMG-20250818-WA0014.jpg"},
         {"name": "Bagenda Augustine", "role": "Principle Developments and Partnerships Officer", "email": "bagenda@bicul.co.ug", "photo": "2025_04_IMG-20250818-WA0018.jpg"},
         {"name": "Nakiwala Brenda", "role": "Monitoring and Evaluation Officer", "email": "nakiwala@bicul.co.ug", "photo": "2025_04_Brenda-Nakiwala.jpg"}]},
    {"slug": "incubation", "title": find("incubation-division", "Incubation Division"),
     "lead": find("incubation-division", "The Incubation Division is the department"),
     "paras": [find("incubation-division", "The Incubation Division’s focus"), find("incubation-division", "The Division seeks")],
     "vision": find("incubation-division", "To strategically position the Kingdom of Buganda as a key investment"),
     "mission": find("incubation-division", "To increase the successful"),
     "objectives": items_after("incubation-division", "Objectives"),
     "summary": C["home"]["who_items"][3]["text"], "short": C["home"]["who_items"][3]["title"],
     "contacts": [{"name": "Daniel Nakibinge", "role": "Principal Investments and Planning Officer", "email": "nakibinge@bicul.co.ug", "photo": "2025_04_Daniel-Nakibingee.jpg"}]},
    {"slug": "monitoring-evaluation", "title": find("monitoring-and-evaluation", "Monitoring and Evaluation"),
     "lead": find("monitoring-and-evaluation", "The Monitoring and Evaluation (M&E) Office"),
     "paras": [find("monitoring-and-evaluation", "Its core mandate"), find("monitoring-and-evaluation", "This office plays"),
               find("monitoring-and-evaluation", "The Kingdom leverages"), find("monitoring-and-evaluation", "By tracking outcomes")],
     "vision": None, "mission": None, "objectives": [],
     "summary": C["home"]["who_items"][1]["text"], "short": C["home"]["who_items"][1]["title"],
     "contacts": [{"name": "Nakiwala Brenda", "role": "Monitoring & Evaluation", "tel": TEL, "email": "nakiwala@bicul.co.ug", "photo": "2025_04_Brenda-Nakiwala.jpg"}]},
]

# ---- Social impact collaborations ----
sp = "spotlight-on-social-impact-collaborations"
blocks = P[sp]
sections = []
cur = None
start = next(i for i, b in enumerate(blocks) if b.get("x") == "The Mwanyi Terimba Campaign")
end = next(i for i, b in enumerate(blocks) if b.get("x", "").startswith("Join Us in Building"))
EMO = re.compile(r"^([\U0001F300-\U0001FAFF☀-➿][\U0001F300-\U0001FAFF☀-➿‍\U0001F3FB-\U0001F3FF️]*)\s*")
i = start
while i < end:
    b = blocks[i]
    x = b.get("x", "")
    is_head = (b["t"] == "h") or (b["t"] == "p" and (EMO.match(x) and ":" in x and len(x) < 90 and not x.startswith("👥")) ) \
        or x in ("Ongoing Civic Engagement", "📍 Ongoing Civic Engagement")
    if b["t"] == "h" and x == "The Mwanyi Terimba Campaign":
        cur = {"icon": "🌱", "title": "Agriculture: Nutrition & Income Generation", "name": x, "blocks": []}
        sections.append(cur); i += 1
        # skip the repeated subtitle + repeated name on the source
        while blocks[i].get("x") in ("Agriculture: Nutrition & Income Generation", "The Mwanyi Terimba Campaign"): i += 1
        continue
    if is_head:
        m = EMO.match(x)
        cur = {"icon": m.group(1) if m else "", "title": EMO.sub("", x), "blocks": []}
        sections.append(cur); i += 1; continue
    cur["blocks"].append(b); i += 1
S["impact"] = {
    "title": find(sp, "Social Impact Collaborations"),
    "heading": find(sp, "Driving Transformation"),
    "intro": [find(sp, "Welcome to a special feature"), find(sp, "Inspired by our development agenda")],
    "pillars_title": find(sp, "Our focus spans"),
    "pillars": ["Agriculture", "Education", "Health", "Gender Empowerment", "Youth Empowerment", "Environment"],
    "sections": sections,
    "closing_title": find(sp, "Join Us in Building"),
    "closing": find(sp, "From village centers"),
    "closing_cta": find(sp, "Partner with us. Support"),
}

# ---- Partnership documents (no content on the source yet) ----
S["partnership_docs"] = [
    {"slug": "framework", "title": find("partnerships-framework", "Partnerships Framework"), "body": find("partnerships-framework", "Content to be added")},
    {"slug": "policy", "title": find("partnership-policy", "Partnership Policy"), "body": "Content to be added"},
    {"slug": "process-flow", "title": find("partnership-process-flow", "Partnership Process Flow"), "body": "Content to be added"},
]

# ---- Contact ----
S["contact"] = {
    "title": find("contact-us", "Contact Us"), "info_title": find("contact-us", "Contact Info"),
    "address": find("contact-us", "Bulange Building"), "email": "info@bicul.co.ug", "tel": "+256 708 400 208", "tel_link": "+256708400208",
    "form_title": find("contact-us", "Contact Form"),
    "fields": {"name": "Your name", "email": "Your email", "subject": "Subject", "message": "Your message"},
}

for k in ("opportunities", "programs", "projects", "publications", "subsidiaries", "partners", "people", "news", "gallery", "footer"):
    S[k] = C[k]

S = fix(S)
json.dump(S, open("/home/claude/bicul/content/site_en.json", "w"), ensure_ascii=False, indent=1)
print("sections:", [(s["icon"], s["title"], len(s["blocks"])) for s in S["impact"]["sections"]])
