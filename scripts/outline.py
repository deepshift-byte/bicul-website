import sys, re
from bs4 import BeautifulSoup, NavigableString, Tag
WS=re.compile(r"\s+")
def clean(s):
    for t in s(['script','style','noscript','svg']): t.decompose()
    for el in s.select('.screen-reader-text'): el.decompose()
    for a in s.find_all('a',href=re.compile(r'sharer|intent/tweet|share-offsite|whatsapp.com/send')): a.decompose()
def out(el, d=0):
    for c in el.children:
        if isinstance(c, NavigableString):
            t=WS.sub(' ',str(c)).strip()
            if t: print('  '*d+'"'+t+'"')
        elif isinstance(c, Tag):
            cls='.'.join(c.get('class') or [])[:50]
            extra=''
            if c.name=='img': extra=' src='+(c.get('src') or '')[-60:]+' alt='+repr(c.get('alt'))
            if c.name=='a': extra=' href='+(c.get('href') or '')[-70:]
            txt=WS.sub(' ',c.get_text(' ',strip=True))
            kids=[k for k in c.children if isinstance(k,Tag)]
            if c.name in ('p','h1','h2','h3','h4','h5','h6','li','a','span','strong','em','button','label') and len(txt)<400 and not c.find(['img','ul','div','p']):
                print('  '*d+f'<{c.name} {cls}{extra}> {txt}')
            else:
                print('  '*d+f'<{c.name} {cls}{extra}>')
                out(c,d+1)
for f in sys.argv[1:]:
    s=BeautifulSoup(open(f,'rb').read(),'lxml',from_encoding='utf-8'); clean(s)
    m=s.find('main'); ft=m.find('footer',class_='site-footer')
    print('#####',f, s.title.get_text())
    out(m if '--footer' not in f else ft)
