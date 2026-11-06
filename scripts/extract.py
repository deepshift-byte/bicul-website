"""Turn the scraped BICUL pages into structured English content (content/en.json).
Text is copied verbatim from the pages; nothing is invented."""
import re, json, os, glob, urllib.parse
from bs4 import BeautifulSoup, NavigableString, Tag, Comment

DATA = "/home/claude/bicul/data"
RAW = f"{DATA}/html_raw"
IMGDIR = f"{DATA}/images"
SITE = "https://bicul.co.ug"
WS = re.compile(r"\s+")
HAVE = set(os.listdir(IMGDIR))
MISSING = set()


def soup(slug):
    s = BeautifulSoup(open(f"{RAW}/{slug}.html", "rb").read(), "lxml", from_encoding="utf-8")
    for t in s(["script", "style", "noscript", "svg", "iframe"]): t.decompose()
    for el in s.select(".screen-reader-text"): el.decompose()
    for img in s.select("img.emoji, img.wp-smiley"):
        img.replace_with(img.get("alt") or "")
    return s


def txt(el):
    if el is None: return ""
    return WS.sub(" ", el.get_text(" ", strip=True)).replace(" ,", ",").replace(" .", ".").strip()


def best_src(img):
    for attr in ("srcset", "data-srcset"):
        if img.get(attr):
            best, bw = None, -1
            for part in img[attr].split(","):
                b = part.strip().split()
                if not b: continue
                w = int(b[1][:-1]) if len(b) > 1 and b[1].endswith("w") and b[1][:-1].isdigit() else 0
                if w > bw: best, bw = b[0], w
            if best: return best
    return img.get("data-src") or img.get("src")


def local(url):
    """Map an image URL to the downloaded file name; None for placeholders."""
    if not url: return None
    url = urllib.parse.urljoin(SITE + "/", url)
    p = urllib.parse.urlparse(url).path
    if p.endswith("/img/00.png") or "placeholder.png" in p: return None
    name = re.sub(r"^/wp-content/uploads/", "", p)
    name = re.sub(r"^/wp-content/", "wpc_", name).strip("/").replace("/", "_")
    if name in HAVE: return name
    # thumbnail fallback -> original
    orig = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", name)
    if orig in HAVE: return orig
    MISSING.add(url)
    return None


def img_of(img):
    return local(best_src(img))


def inline(el):
    """Inline text with external links kept as [text](url)."""
    out = []
    for c in el.children:
        if isinstance(c, Comment): continue
        if isinstance(c, NavigableString): out.append(str(c)); continue
        if c.name == "br": out.append("\n"); continue
        if c.name == "img": continue
        if c.name == "a":
            href = (c.get("href") or "").strip()
            t = inline(c)
            if href.startswith(("mailto:", "tel:")) or (href.startswith("http") and not href.startswith(SITE)):
                out.append(f"[{WS.sub(' ', t).strip() or href}]({href})")
            else:
                out.append(t)
            continue
        out.append(inline(c))
    return "".join(out)


def clean_inline(s):
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r" *\n *", "\n", s).strip()
    return s


def body_blocks(root):
    """Rich body: paragraphs, headings, lists, images (in order)."""
    blocks = []
    def walk(el):
        for c in el.children:
            if isinstance(c, NavigableString):
                t = WS.sub(" ", str(c)).strip()
                if t: blocks.append({"t": "p", "x": t})
                continue
            if not isinstance(c, Tag): continue
            n = c.name
            if n == "img":
                f = img_of(c)
                if f: blocks.append({"t": "img", "src": f, "alt": c.get("alt") or ""})
                continue
            if n in ("h1", "h2", "h3", "h4", "h5", "h6"):
                t = clean_inline(inline(c))
                if t: blocks.append({"t": "h", "x": t})
                continue
            if n in ("ul", "ol"):
                items = [clean_inline(inline(li)) for li in c.find_all("li", recursive=False)]
                items = [i for i in items if i]
                if items: blocks.append({"t": "ol" if n == "ol" else "ul", "items": items})
                continue
            if n in ("p", "blockquote", "figcaption"):
                for im in c.find_all("img"):
                    f = img_of(im)
                    if f: blocks.append({"t": "img", "src": f, "alt": im.get("alt") or ""})
                t = clean_inline(inline(c))
                if t: blocks.append({"t": "quote" if n == "blockquote" else "p", "x": t})
                continue
            walk(c)
    walk(root)
    # merge duplicate consecutive images
    out = []
    for b in blocks:
        if out and b == out[-1]: continue
        out.append(b)
    return out


def single(slug):
    """Common fields for a single post/opportunity/etc page."""
    s = soup(slug)
    art = s.find("article") or s.find("main")
    title = txt(art.select_one("h1.entry-title") or art.find("h1"))
    cats = [txt(a) for a in art.select(".sec-categories a, .sec-categories span")] if art.select_one(".sec-categories") else []
    if not cats and art.select_one(".sec-categories"):
        cats = [txt(art.select_one(".sec-categories"))]
    SECT = ["Trade & Commerce", "Real Estate", "Health", "Media", "Tourism", "Agriculture", "Education"]
    flat = " ".join(cats)
    found = [x for x in SECT if x in flat]
    cats = sorted(found, key=lambda x: flat.index(x)) if found else [c for c in dict.fromkeys(cats) if c]
    date = txt(art.select_one(".when"))
    hdr = art.select_one("header.entry-header")
    feat = None
    for more in art.select(".sec-more, .sec-aside-posts"): more.extract()
    fi = art.select_one("img.wp-post-image") or (hdr.select_one(".img-cover img") if hdr else None)
    if fi: feat = img_of(fi)
    summary = []
    if hdr:
        for p in hdr.select(".border-top p"):
            t = clean_inline(inline(p))
            if t: summary.append(t)
    content = art.select_one(".entry-content")
    body = body_blocks(content) if content else []
    downloads = []
    for a in art.find_all("a", href=re.compile(r"\.pdf$", re.I)):
        downloads.append({"url": a["href"], "file": a["href"].rsplit("/", 1)[1]})
    meta_pub = s.find("meta", attrs={"property": "article:published_time"})
    return dict(slug=slug.split("__")[-1], title=title, categories=cats, date=date, image=feat,
                summary=summary, body=body, downloads=list({d["url"]: d for d in downloads}.values()),
                published=meta_pub["content"][:10] if meta_pub else None)


def page_main(slug):
    s = soup(slug)
    m = s.find("main")
    f = m.find("footer", class_="site-footer")
    if f: f.extract()
    return s, m


C = {}

# ---------- Opportunities ----------
opps = []
for f in sorted(glob.glob(f"{RAW}/opportunity__*.html")):
    slug = os.path.basename(f)[:-5]
    d = single(slug)
    opps.append(d)
C["opportunities"] = opps

# ---------- Programs & projects ----------
C["programs"] = [single(os.path.basename(f)[:-5]) for f in sorted(glob.glob(f"{RAW}/program__*.html"))]
C["projects"] = [single(os.path.basename(f)[:-5]) for f in sorted(glob.glob(f"{RAW}/project__*.html"))]

# ---------- Publications (order from listing) ----------
s, m = page_main("publications")
pub_order = [a["href"].rstrip("/").rsplit("/", 1)[1] for a in m.select("a[href*='/publication/']")]
pub_order = list(dict.fromkeys(pub_order))
pubs = {os.path.basename(f)[:-5].split("__")[1]: single(os.path.basename(f)[:-5]) for f in glob.glob(f"{RAW}/publication__*.html")}
C["publications"] = [pubs[k] for k in pub_order if k in pubs] + [v for k, v in pubs.items() if k not in pub_order]
listing_text = {}
for h in m.find_all("h5"):
    p = h.find_next("p")
    listing_text[txt(h)] = clean_inline(inline(p)) if p else ""
for p in C["publications"]:
    p["body"] = [{"t": "p", "x": listing_text.get(p["title"], "")}] if listing_text.get(p["title"]) else []

# ---------- Subsidiaries (listing gives order, website links; detail gives full text) ----------
s, m = page_main("subsidiaries")
subs = []
for h in m.find_all("h4"):
    card = h
    for _ in range(6):
        card = card.parent
        if card.find("a", href=re.compile(r"/subsidiary/")) or card.find("img"): break
    name = txt(h)
    site = None
    for a in card.find_all("a", href=True):
        if a["href"].startswith("http") and not a["href"].startswith(SITE):
            site = a["href"]; break
    det = card.find("a", href=re.compile(r"/subsidiary/"))
    slug = det["href"].rstrip("/").rsplit("/", 1)[1] if det else None
    im = card.find("img")
    subs.append({"name": name, "website": site, "slug": slug, "logo": img_of(im) if im else None})
norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower().replace("’", "").replace("'", ""))
details = {}
for f in glob.glob(f"{RAW}/subsidiary__*.html"):
    d = single(os.path.basename(f)[:-5])
    details[norm(d["title"])] = d
for sub in subs:
    d = details.pop(norm(sub["name"]), None)
    if d: sub["slug"] = d["slug"]
    sub["body"] = [b for b in (d["body"] if d else []) if b["t"] != "img"]
    sub["image"] = (d or {}).get("image") or sub["logo"]
    sub["date"] = (d or {}).get("date")
    sub["title"] = (d or {}).get("title") or sub["name"]
# listing text where detail body is missing
for sub, h in zip(subs, m.find_all("h4")):
    if not sub["body"]:
        card = h.parent
        ps = [clean_inline(inline(p)) for p in card.find_all("p")]
        ps = [p for p in ps if p and p not in ("Read More",) and not p.startswith("Visit") and not p.startswith("View")]
        sub["body"] = [{"t": "p", "x": p} for p in ps]
assert not details, details.keys()
C["subsidiaries"] = subs

# ---------- Partners (order from the two listing pages) ----------
partners = []
for slug in ("partnerships", "partnerships__page__2"):
    s, m = page_main(slug)
    for h in m.find_all("h6"):
        card = h.parent
        while card and not card.find("img"): card = card.parent
        im = card.find("img")
        a = h.find_parent("a") or card.find("a", href=re.compile(r"/partner/"))
        partners.append({"name": txt(h), "logo": img_of(im) if im else None,
                         "slug": a["href"].rstrip("/").rsplit("/", 1)[1] if a else None})
C["partners"] = partners

# ---------- People ----------
def listing_people(slug):
    s, m = page_main(slug)
    out = []
    for h in m.find_all("h5"):
        card = h.parent
        while card and not card.find("img"): card = card.parent
        im = card.find("img")
        role = txt(card.select_one(".what")) or None
        a = card.find("a", href=re.compile(r"/people/"))
        out.append({"name": txt(h), "role": role, "photo": img_of(im) if im else None,
                    "slug": a["href"].rstrip("/").rsplit("/", 1)[1] if a else None})
    intro = m.find("h4") or m.find("p")
    return out, txt(intro)
board, board_intro = listing_people("board-members")
team, team_intro = listing_people("team")
s, m = page_main("designation__advisory-committee")
advisory = []
for h in m.select("article h2, h2.entry-title"):
    a = h.find("a")
    slug = a["href"].rstrip("/").rsplit("/", 1)[1] if a else None
    ph = None
    if slug and os.path.exists(f"{RAW}/people__{slug}.html"):
        d = single("people__" + slug)
        ph = d["image"] or next((b["src"] for b in d["body"] if b["t"] == "img"), None)
    advisory.append({"name": txt(h), "slug": slug, "photo": ph})
C["people"] = {"board": board, "board_intro": board_intro, "team": team, "team_intro": team_intro,
               "advisory": advisory}

# ---------- News posts ----------
import xml.etree.ElementTree as ET
post_urls = re.findall(r"<loc>([^<]+)</loc>", open(f"{DATA}/sm_post.xml").read())
posts = []
for u in post_urls:
    slug = u.rstrip("/").rsplit("/", 1)[1]
    d = single(slug)
    posts.append(d)
import datetime
for p in posts:
    p["published"] = datetime.datetime.strptime(p["date"], "%B %d, %Y").strftime("%Y-%m-%d")
posts.sort(key=lambda p: p["published"], reverse=True)
C["news"] = posts

# ---------- Gallery ----------
s, m = page_main("gallery")
C["gallery"] = [g for g in (img_of(i) for i in m.find_all("img")) if g]


def section_blocks(slug):
    s, m = page_main(slug)
    return body_blocks(m)

# ---------- Standalone pages (verbatim blocks) ----------
C["pages"] = {}
for slug in ["about-us", "why-invest-in-buganda", "statistics-division", "monitoring-and-evaluation",
             "incubation-division", "strategic-partnerships-division", "spotlight-on-social-impact-collaborations",
             "partnerships-framework", "partnership-policy", "partnership-process-flow", "contact-us"]:
    C["pages"][slug] = section_blocks(slug)

# ---------- Home page pieces ----------
s, m = page_main("home")
hero = m.select_one("section.site-hero")
stats = [{"value": txt(li.select_one(".wrap-number")), "label": txt(li.select_one(".wrap-label"))} for li in m.select(".card-stat")]
tbl_sec = m.select_one("section.bg-primary")
tbl = {"title": txt(tbl_sec.find("h2")), "intro": txt(tbl_sec.find("h2").find_next("span")),
       "items": [{"title": txt(c.find("h4")), "text": txt(c.find("h4").find_next("span"))} for c in tbl_sec.select(".card-icon")]}
frontier = m.find("h2", string=re.compile("Investment Frontiers")).parent
who = m.select_one("section.site-poster")
news_sec = m.find("h2", string=re.compile("New at BICUL")).parent
build = m.find("h2", string=re.compile("Build Together")).parent
arms = m.select("section.site-poster")[1]
cta = m.select_one("section.sec-cta")
C["home"] = {
    "hero_title": txt(hero.find("h1")), "hero_text": txt(hero.find("h1").find_next("span")),
    "hero_buttons": [txt(a) for a in hero.select(".sec-txt-btns a")],
    "hero_kabaka_alt": hero.select_one(".sec-kabaka img").get("alt"),
    "hero_kabaka": img_of(hero.select_one(".sec-kabaka img")),
    "stats": stats, "triple": tbl,
    "frontiers_title": txt(frontier.find("h2")), "frontiers_text": txt(frontier.find("span")),
    "frontiers_tabs": [txt(li) for li in m.select("ul.nav-tabs li")],
    "who_title": txt(who.find("h2")), "who_text": txt(who.find("p")), "who_bg": img_of(who.select_one(".sec-bg img")),
    "who_items": [{"title": txt(c.find("h4")), "text": txt(c.find("span"))} for c in who.select(".card-txt")],
    "news_title": txt(news_sec.find("h2")), "news_text": txt(news_sec.find("p")),
    "build_title": txt(build.find("h2")), "build_text": txt(build.find("span")),
    "arms_title": txt(arms.find("h2")), "arms_text": txt(arms.find("h2").find_next(["p", "span"])),
    "cta_title": txt(cta.find("h2") or cta.find("h3")), "cta_text": txt((cta.find("h2") or cta.find("h3")).find_next(["p", "span"])),
    "cta_buttons": [txt(a) for a in cta.find_all("a")],
}
home_raw = [t for t in body_blocks(m)]
C["home_all_text"] = home_raw

# ---------- Footer / contact facts ----------
s = soup("home")
ft = s.select_one("footer.site-footer")
C["footer"] = {
    "address": "Bulange Building Mengo, Ground Floor",
    "phone_display": "+256 200900886", "phone_link": "+256708400208",
    "social": [a["href"] for a in ft.find_all("a", href=re.compile(r"facebook|instagram|x\.com"))],
    "copyright": txt(ft.find(string=re.compile("©")).parent),
    "webmail": "https://webmail.supremecluster.com/",
}

os.makedirs("/home/claude/bicul/content", exist_ok=True)
json.dump(C, open("/home/claude/bicul/content/en.json", "w"), ensure_ascii=False, indent=1)
print("opps", len(opps), "programs", len(C["programs"]), "projects", len(C["projects"]), "pubs", len(C["publications"]),
      "subs", len(subs), "partners", len(partners), "board", len(board), "team", len(team), "advisory", len(advisory),
      "news", len(posts), "gallery", len(C["gallery"]))
print("missing images:", sorted(MISSING))
