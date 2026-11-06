"""Collect every translatable string from site_en.json (names, emails, URLs, file names excluded)."""
import json, re, sys
SKIPKEYS = {'slug','image','src','logo','photo','url','file','website','published','who_bg','hero_kabaka','social','webmail',
            'phone_link','phone_display','date','categories','alt','address','copyright','frontiers_tabs','t','name','email',
            'tel','tel_link','icon','gallery','downloads','value'}
NAME_TITLE_PARENTS = {'subsidiaries', 'partners'}
def collect(S):
    out = []
    def walk(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in SKIPKEYS: continue
                if k == 'title' and path and path[0] in NAME_TITLE_PARENTS: continue
                walk(v, path + [k])
        elif isinstance(x, list):
            for v in x: walk(v, path)
        elif isinstance(x, str) and x.strip():
            out.append(x)
    walk(S, [])
    return list(dict.fromkeys(out))
if __name__ == '__main__':
    S = json.load(open('content/site_en.json'))
    S.pop('home', None) if False else None
    strs = collect(S)
    print(len(strs), sum(len(s.split()) for s in strs))
