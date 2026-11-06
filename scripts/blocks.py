import sys, re
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
WS=re.compile(r"\s+")
BLOCK={"div","section","article","header","footer","main","aside","nav","p","h1","h2","h3","h4","h5","h6","ul","ol","li","table","tr","td","th","blockquote","figure","figcaption","form","dl","dt","dd","label","button","select","option"}
def clean(s):
    for t in s(['script','style','noscript','svg','iframe']): t.decompose()
    for el in s.select('.screen-reader-text'): el.decompose()
    for a in s.find_all('a',href=re.compile(r'sharer|intent/tweet|share-offsite|whatsapp.com/send')): a.decompose()
    for h in s.find_all(string=re.compile(r'^\s*Share This\s*$')):
        h.parent.decompose()
class X:
    def __init__(s): s.out=[]; s.buf=[]
    def flush(s,tag='p'):
        t=WS.sub(' ',''.join(s.buf)).strip(); s.buf=[]
        if t: s.out.append(f'{tag}: {t}')
    def walk(s,el):
        for c in el.children:
            if isinstance(c,Comment): continue
            if isinstance(c,NavigableString): s.buf.append(str(c)); continue
            n=c.name
            if n=='img':
                s.flush(); s.out.append(f"IMG {(c.get('src') or '').split('/uploads/')[-1]} | {c.get('alt')}"); continue
            if n=='a' and c.get('href') and not c.get('href').startswith('https://bicul.co.ug'):
                s.walk(c); s.buf.append(f" <{c.get('href')}>"); continue
            if n in ('h1','h2','h3','h4','h5','h6'):
                s.flush(); s.walk(c); s.flush(n); continue
            if n=='li':
                s.flush(); s.walk(c); s.flush('li'); continue
            if n in BLOCK: s.flush(); s.walk(c); s.flush(); continue
            s.walk(c)
            if n=='span' and c.get('class'): s.buf.append(' ')
for f in sys.argv[1:]:
    s=BeautifulSoup(open(f,'rb').read(),'lxml',from_encoding='utf-8'); clean(s)
    m=s.find('main'); ft=m.find('footer',class_='site-footer')
    if ft: ft.extract()
    x=X(); x.walk(m); x.flush()
    print('#####',f.split('/')[-1])
    print('\n'.join(x.out))
