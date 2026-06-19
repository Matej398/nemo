#!/usr/bin/env python3
# =============================================================================
#  NeMo blog generator  —  DEV TOOL ONLY
# -----------------------------------------------------------------------------
#  Generates the Članki index (clanki.html) and every article page in /clanki/
#  from the source posts on the live WordPress site, plus images in img/blog/.
#
#  Re-run it after changing shared markup (nav/footer/cookie) or the article
#  template/CSS so all 28 pages stay consistent:
#
#      python3 tools/build_blog.py
#
#  It re-downloads the source posts from the OLD live site, so it only works
#  WHILE https://www.nemo.si still serves the old WordPress blog.
#
#  ⚠️  DELETE THIS tools/ FOLDER BEFORE PUBLISHING THE NEW SITE.
#      It is a build-time helper, not part of the website, and must not be
#      deployed/served publicly. After launch the old blog is gone and this
#      script can no longer fetch sources anyway.
# =============================================================================
import re, os, html, base64, urllib.request, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART  = os.path.join(tempfile.gettempdir(), 'nemo_art')
BASE = 'https://www.nemo.si'
os.makedirs(os.path.join(REPO, 'img/blog'), exist_ok=True)
os.makedirs(os.path.join(REPO, 'clanki'), exist_ok=True)
os.makedirs(ART, exist_ok=True)

# live post slugs, in display order (newest first comes from <time> sort below)
SLUGS = [
    'krutost-nove-ere', 'testni-primer', 'rebalans-gurujev', 'pasjansa',
    'pospravljanje-za-novo-leto', 'gonja-za-cudezi', 'skrila-je-svoje-otroke-pred-svetom',
    'pravila-misterijev', 'jasnovidnost-in-njeni-odtenki', 'jasnovidnost-ucenci-in-zaveza',
    'jasnovidnost-v-casu-prihodnost', 'zate-zenska', 'jasnovidnost-kot-igranje-harfe',
    'komentar', 'postavljanje-linije-hare-osi-namena-nalog-in-resnice-posameznika',
    'vedezevanje', 'ljubezen-v-prerezu', 'spomnim-se-le-da-uzivam-ze-dolgo',
    'cas-ponocne-svetlobe', 'nagon-in-brezpogojnost-narave', 'pasion', 'meditacija',
    'energijske-slike', 'obilje', 'darilo', 'solza-in-smeh', 'skladovnica-casa',
    'nemo-predstavitev-kraj-delovanja',
]

def fetch_sources():
    """Download each post's raw HTML into ART if not already present."""
    for slug in SLUGS:
        dst = os.path.join(ART, slug + '.html')
        if os.path.exists(dst):
            continue
        try:
            req = urllib.request.Request(f'{BASE}/{slug}/', headers={'User-Agent': 'Mozilla/5.0'})
            open(dst, 'wb').write(urllib.request.urlopen(req, timeout=30).read())
            print('  fetched', slug)
        except Exception as e:
            print('  FETCH FAIL', slug, e)

# slug -> output filename stem (handle collisions / bad slugs)
RENAME = {
    'testni-primer': 'front-wo-man',
    'vedezevanje':   'vedezevanje-clanek',
}

MONTHS = {1:'januar',2:'februar',3:'marec',4:'april',5:'maj',6:'junij',
          7:'julij',8:'avgust',9:'september',10:'oktober',11:'november',12:'december'}

# ---- pull shared boilerplate fragments from existing clanki.html ----
src = open(os.path.join(REPO,'clanki.html'),encoding='utf-8').read()
SPRITE = src[src.index('<svg width="0"'): src.index('</svg>')+6]
NAV    = src[src.index('<nav>'): src.index('</nav>')+6]
FOOTER = src[src.index('<footer'): src.index('</footer>')+9]
COOKIE = src[src.index('<div class="cookie"'): src.rindex('<script>')]

HEAD_CONSENT = """<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){ dataLayer.push(arguments); }
  gtag('consent','default',{'ad_storage':'denied','analytics_storage':'denied','ad_user_data':'denied','ad_personalization':'denied','wait_for_update':500});
</script>"""

def script_block(page):
    return """<script>
  const GTM_ID = 'GTM-XXXXXXX';
  function loadGTM(){ if(window.__gtm)return; window.__gtm=true;
    (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});
    var f=d.getElementsByTagName(s)[0],j=d.createElement(s);j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i;f.parentNode.insertBefore(j,f);})(window,document,'script','dataLayer',GTM_ID);}
  function grantConsent(){ gtag('consent','update',{'ad_storage':'granted','analytics_storage':'granted','ad_user_data':'granted','ad_personalization':'granted'}); loadGTM(); }
  const banner=document.getElementById('cookieBanner');
  const choice=localStorage.getItem('nemo_consent');
  if(choice==='granted') grantConsent();
  else if(choice!=='denied') banner.classList.add('show');
  document.getElementById('cookieAccept').addEventListener('click',()=>{ localStorage.setItem('nemo_consent','granted'); banner.classList.remove('show'); grantConsent(); });
  document.getElementById('cookieDecline').addEventListener('click',()=>{ localStorage.setItem('nemo_consent','denied'); banner.classList.remove('show'); });
  document.querySelectorAll('a[href^="tel:"]').forEach(a=>a.addEventListener('click',()=>{
    dataLayer.push({event:'call_click', call_number:a.getAttribute('data-call'), page:'%s'});
  }));
  const nav=document.querySelector('nav');
  const onScroll=()=>nav.classList.toggle('scrolled', window.scrollY>24);
  onScroll(); window.addEventListener('scroll', onScroll, {passive:true});
</script>""" % page

def extract_block(h, classname):
    m = re.search(r'<div[^>]*class="[^"]*'+re.escape(classname)+r'[^"]*"[^>]*>', h)
    if not m: return None
    start = m.end(); depth = 1
    for mm in re.finditer(r'<(/?)div\b[^>]*>', h[start:]):
        depth += 1 if mm.group(1)=='' else -1
        if depth == 0:
            return h[start:start+mm.start()]
    return h[start:]

def to_sub(frag):
    # rewrite relative href/src for files living inside the /clanki/ subfolder
    return re.sub(r'(href|src)="(?!https?:|tel:|mailto:|#|\.\./)([^"]+)"', r'\1="../\2"', frag)

def save_image(s, stem, n):
    try:
        if s.startswith('data:image'):
            m = re.match(r'data:image/([a-zA-Z0-9.+-]+);base64,(.*)$', s, re.S)
            if not m: return None
            ext = m.group(1).lower(); ext = 'jpg' if ext in ('jpeg','jpg') else ext
            data = base64.b64decode(m.group(2).strip())
        else:
            url = s if s.startswith('http') else (BASE+s if s.startswith('/') else None)
            if not url: return None
            ext = url.split('?')[0].split('.')[-1].lower()
            ext = 'jpg' if ext in ('jpeg','jpg') else (ext if ext in ('png','gif','webp') else 'jpg')
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=25).read()
        if len(data) < 1200: return None     # skip spacers/placeholders
        fn = f'img/blog/{stem}-{n}.{ext}'
        open(os.path.join(REPO, fn),'wb').write(data)
        return fn, len(data)
    except Exception as e:
        print('   IMG FAIL', str(s)[:50], e); return None

def clean_content(raw, stem):
    c = raw
    c = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', '', c)
    # drop lightbox anchors that wrap images
    c = re.sub(r'(?is)<a\b[^>]*\.(?:jpe?g|png|gif)[^>]*>(.*?)</a>', r'\1', c)
    # images -> local
    imgs = []
    def img_repl(m):
        tag = m.group(0)
        src_m = re.search(r'\bsrc="([^"]+)"', tag)
        if not src_m: return ''
        res = save_image(src_m.group(1), stem, len(imgs)+1)
        if not res: return ''
        fn, sz = res; imgs.append((fn, sz))
        alt_m = re.search(r'\balt="([^"]*)"', tag)
        alt = html.escape(alt_m.group(1)) if alt_m else ''
        return f'\n<img src="{fn}" alt="{alt}" loading="lazy">\n'
    c = re.sub(r'(?is)<img\b[^>]*>', img_repl, c)
    c = re.sub(r'(?is)</?span\b[^>]*>', '', c)        # unwrap spans
    c = re.sub(r'(?is)<br\s*/?>', ' ', c)             # line breaks -> space
    c = re.sub(r'(?is)<a\b[^>]*?\bhref="([^"]+)"[^>]*>', lambda m:f'<a href="{m.group(1)}">', c)
    c = re.sub(r'(?is)<(p|h2|h3|h4|h5|blockquote|ul|ol|li|em|strong|i|b)\b[^>]*>', r'<\1>', c)
    c = c.replace('<h5>','<h3>').replace('</h5>','</h3>')
    c = c.replace('<h4>','<h3>').replace('</h4>','</h3>')
    c = c.replace('<b>','<strong>').replace('</b>','</strong>')
    c = c.replace('<i>','<em>').replace('</i>','</em>')
    allowed = {'p','h2','h3','blockquote','ul','ol','li','em','strong','a','img'}
    def tagf(m):
        name = m.group(1).lstrip('/').lower()
        return m.group(0) if name in allowed else ''
    c = re.sub(r'(?is)<(/?[a-z0-9]+)\b[^>]*>', tagf, c)
    c = c.replace('&nbsp;',' ')
    c = re.sub(r'(?is)<p>\s*(?:&#8230;|…)?\s*</p>', '', c)   # empty paras
    c = re.sub(r'[ \t]{2,}', ' ', c)
    c = re.sub(r'\n{3,}', '\n\n', c)
    return c.strip(), imgs

def make_excerpt(clean_html):
    t = re.sub(r'(?is)<[^>]+>', ' ', clean_html)
    t = html.unescape(t)
    t = t.lstrip('….  ').strip()
    t = re.sub(r'\s+', ' ', t)
    if len(t) <= 170: return t
    cut = t[:170].rsplit(' ', 1)[0]
    return cut + '…'

ARTICLE_TMPL = """<!DOCTYPE html>
<html lang="sl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — NeMo Neskončne Možnosti</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="https://www.nemo.si/clanki/{stem}.html">
<link rel="icon" type="image/png" href="../img/logo.png">
<link rel="stylesheet" href="../css/style.css">
{head_consent}
</head>
<body>

{sprite}

{nav}

<header class="page-head sky" style="padding:120px 0 44px;">
  <div class="narrow" style="text-align:center;">
    <h1 style="margin-bottom:30px;">{title}</h1>
    <a href="../clanki.html" class="back-link">← <span>Nazaj na članke</span></a>
  </div>
</header>

<section style="background:#fff; padding:64px 0 80px;">
  <div class="container">
    <div class="article-body">
{body}
      <a href="../clanki.html" class="back-link" style="margin-top:44px;">← <span>Nazaj na članke</span></a>
    </div>
  </div>
</section>

{footer}

{cookie}{script}
</body>
</html>
"""

fetch_sources()

articles = []   # (sortkey, stem, title, date_sl, excerpt, thumb, nimg)
for slug in SLUGS:
    path = os.path.join(ART, slug+'.html')
    if not os.path.exists(path):
        print('SKIP (no source)', slug); continue
    h = open(path, encoding='utf-8').read()
    tm = re.search(r'<h1[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h1>', h, re.S)
    title = html.unescape(re.sub(r'<[^>]+>','',tm.group(1))).strip() if tm else slug
    dm = re.search(r'<time[^>]*class="[^"]*entry-date published[^"]*"[^>]*datetime="([^"]+)"', h)
    iso = dm.group(1)[:10] if dm else '2016-01-01'
    y,mo,d = (int(x) for x in iso.split('-'))
    date_sl = f"{d}. {MONTHS[mo]} {y}"
    raw = extract_block(h, 'entry-content') or ''
    stem = RENAME.get(slug, slug)
    body, imgs = clean_content(raw, stem)
    excerpt = make_excerpt(body)
    thumb = imgs[0][0] if imgs else ''
    body_sub = body.replace('src="img/blog/', 'src="../img/blog/')
    out = ARTICLE_TMPL.format(
        title=html.escape(title), desc=html.escape(excerpt), stem=stem,
        date=html.escape(date_sl), body=body_sub,
        head_consent=HEAD_CONSENT, sprite=SPRITE, nav=to_sub(NAV), footer=to_sub(FOOTER),
        cookie=to_sub(COOKIE), script=script_block('clanek-'+stem))
    open(os.path.join(REPO, 'clanki', stem+'.html'),'w',encoding='utf-8').write(out)
    articles.append((iso, stem, title, date_sl, excerpt, thumb, len(imgs)))
    print(f"{stem:42s} {iso}  imgs={len(imgs)}  body={len(body):6d}  thumb={'Y' if thumb else '-'}")

# ---- index page ----
articles.sort(key=lambda a: a[0], reverse=True)
rows = []
for iso, stem, title, date_sl, excerpt, thumb, nimg in articles:
    if thumb:
        thumb_html = f'<img src="{thumb}" class="article-thumb" alt="{html.escape(title)}" loading="lazy">'
    else:
        thumb_html = '<span class="article-thumb article-thumb-ph" aria-hidden="true"></span>'
    rows.append(f"""      <a href="clanki/{stem}.html" class="article-row">
        {thumb_html}
        <div>
          <h3>{html.escape(title)}</h3>
          <p class="excerpt">{html.escape(excerpt)}</p>
          <span class="more">Preberi več →</span>
        </div>
      </a>""")

INDEX_BODY = f"""<section style="background:#fff; padding:64px 0 90px;">
  <div class="container">
    <div class="article-list">
{chr(10).join(rows)}
    </div>
  </div>
</section>"""

idx = f"""<!DOCTYPE html>
<html lang="sl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Članki — NeMo Neskončne Možnosti</title>
<meta name="description" content="Članki o jasnovidnosti, energijskem branju, duhovnosti in osebnem razvoju. NeMo Neskončne Možnosti.">
<link rel="canonical" href="https://www.nemo.si/clanki.html">
<link rel="icon" type="image/png" href="img/logo.png">
<link rel="stylesheet" href="css/style.css">
{HEAD_CONSENT}
</head>
<body>

{SPRITE}

{NAV}

<header class="page-head sky">
  <div class="narrow" style="text-align: center;">
    <h1>Članki</h1>
    <p>Misli, vpogledi in zapisi o jasnovidnosti, energiji, duhovnem svetu in vsakdanjem življenju.</p>
  </div>
</header>

{INDEX_BODY}

{FOOTER}

{COOKIE}{script_block('clanki')}
</body>
</html>
"""
open(os.path.join(REPO,'clanki.html'),'w',encoding='utf-8').write(idx)
print(f"\nTOTAL {len(articles)} articles | with image: {sum(1 for a in articles if a[5])}")
