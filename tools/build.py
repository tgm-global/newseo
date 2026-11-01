#!/usr/bin/env python3
"""Static site generator for True Gain Media.

Usage:  python3 tools/build.py
Reads assets/config.js (single source of truth) and tools/data.py, then writes every
HTML page, sitemap.xml and robots.txt into the repository root (ready for GitHub Pages).
"""
import datetime
import html
import json
import os
import re
import shutil
import sys
import zlib
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from data import COUNTRIES, INDUSTRIES, CITIES, SERVICES, OVERRIDES  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, ".."))
TODAY = datetime.date.today().isoformat()


def E(s):
    return html.escape(str(s), quote=True)


def load_cfg():
    txt = open(os.path.join(ROOT, "assets", "config.js"), encoding="utf-8").read()
    m = re.search(r"window\.SITE_CONFIG\s*=\s*(\{.*\})\s*;?\s*$", txt, re.S)
    return json.loads(m.group(1))


CFG = load_cfg()
BRAND = CFG["brandName"]
TAGLINE = CFG.get("brandTagline", "")
SITE = CFG["siteUrl"].rstrip("/")
PHONE = CFG["phoneDisplay"]
PHONE_D = re.sub(r"\D", "", CFG["phoneDigits"])
WA_D = re.sub(r"\D", "", CFG["whatsappDigits"])
WA_MSG = CFG.get("whatsappMessage", "")
EMAIL = CFG["email"]

SITEMAP = []  # (path, priority, changefreq)
ALL_PAGES = []  # (path, title)


# ----------------------------------------------------------------- helpers
def slugify(s):
    s = s.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def pick(seed, options):
    return options[zlib.crc32(seed.encode("utf-8")) % len(options)]


def depth(path):
    return len([p for p in path.split("/") if p])


def rel(d, target=""):
    pre = "../" * d
    if target == "":
        return pre or "./"
    return pre + target


def loc(text, c):
    """Localise spelling for US pages."""
    if c and c["us"]:
        for a, b in (("Paediatric", "Pediatric"), ("Organisers", "Organizers"), ("enquiries", "inquiries"), ("enquiry", "inquiry"), ("travellers", "travelers"), ("Optimised", "Optimized")):
            text = text.replace(a, b)
        return text
    return text


def sp(c):
    us = bool(c and c["us"])
    return dict(opt="optimization" if us else "optimisation", optv="optimize" if us else "optimise",
                prog="program" if us else "programme")


def ind_info(ckey, slug):
    base = INDUSTRIES[slug]
    name, phrase = OVERRIDES.get((ckey, slug), (base["n"], base["p"]))
    c = COUNTRIES[ckey]
    return dict(slug=slug, n=loc(name, c), p=loc(phrase, c), lead=loc(base["lead"], c), buyer=loc(base["buyer"], c),
                subs=[loc(s, c) for s in base["subs"]])


def p_country(ckey):
    return f"{ckey}/"


def p_ind(ckey, slug):
    return f"{ckey}/seo-services-for-{slug}/"


def p_sub(ckey, slug, sub):
    return f"{ckey}/seo-services-for-{slug}/seo-for-{slugify(sub)}/"


def p_city(ckey, city):
    return f"{ckey}/{slugify(city)}/"


def p_cityind(ckey, city, slug):
    return f"{ckey}/{slugify(city)}/seo-services-for-{slug}/"


def p_service(slug):
    return f"services/{slug}/"


# --------------------------------------------------------------- icons
SVG = {
    "phone": '<svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.6 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.6 3.6a1 1 0 0 1-.25 1z"/></svg>',
    "wa": '<svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5.2 13.9c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.3-.7-2.8-1.1-4.5-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.8s.7-2 .9-2.3c.2-.2.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.8 2c.1.2.1.4 0 .5l-.3.5-.4.4c-.1.2-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.2 1 2.1 1.3 2.4 1.5.3.1.5.1.6-.1l.9-1c.2-.3.4-.2.6-.1l1.9.9c.3.1.5.2.5.3.1.2.1.8-.1 1.5z"/></svg>',
    "mail": '<svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm0 2v.5l8 5 8-5V6H4zm16 12V9l-8 5-8-5v9h16z"/></svg>',
    "menu": '<svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z"/></svg>',
    "chart": '<svg class="svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V10h3v10zm6 0V4h3v16zm6 0v-7h3v7z"/></svg>',
}


# --------------------------------------------------------------- layout
def logo_html(d):
    words = BRAND.split()[:2]
    initials = "".join(w[0] for w in words).upper()
    if CFG.get("logoImage"):
        mark = f'<span class="logo-mark has-img" data-logo-mark><img src="{rel(d, CFG["logoImage"].lstrip("/"))}" alt="{E(BRAND)}"></span>'
    else:
        mark = f'<span class="logo-mark" data-logo-mark>{E(initials)}</span>'
    return f'<a class="logo" href="{rel(d)}" aria-label="{E(BRAND)} home">{mark}<span class="logo-text" data-brand>{E(BRAND)}</span></a>'


def header_html(d):
    h = lambda t="": rel(d, t)
    svc = f'<li><a href="{h("services/")}">All SEO Services</a></li>' + "".join(
        f'<li><a href="{h(p_service(s["slug"]))}">{E(s["name"])}</a></li>' for s in SERVICES)
    inds = f'<li><a href="{h("industries/")}">All Industries</a></li>' + "".join(
        f'<li><a href="{h(p_country(k))}#industries">Industries in {E(c["name"])}</a></li>' for k, c in COUNTRIES.items())
    locs = f'<li><a href="{h("locations/")}">All Locations</a></li>' + "".join(
        f'<li><a href="{h(p_country(k))}#locations">SEO Services in {E(c["name"])}</a></li>' for k, c in COUNTRIES.items())
    return f'''<header class="site-header" id="top"><div class="container hdr">
{logo_html(d)}
<nav class="nav" id="nav" aria-label="Main navigation"><ul>
<li><a href="{h()}">Home</a></li>
<li class="has-sub"><a href="{h("services/")}">Services</a><ul class="sub">{svc}</ul></li>
<li class="has-sub"><a href="{h("industries/")}">Industries</a><ul class="sub">{inds}</ul></li>
<li class="has-sub"><a href="{h("locations/")}">Locations</a><ul class="sub">{locs}</ul></li>
<li><a href="{h("seo-services-near-me/")}">SEO Near Me</a></li>
<li><a href="{h("about/")}">About</a></li>
<li><a href="{h("contact/")}">Contact</a></li>
</ul></nav>
<div class="hdr-actions">
<a class="hdr-btn" data-tel href="tel:+{PHONE_D}" aria-label="Call {E(BRAND)}">{SVG["phone"]}<span class="t" data-phone>{E(PHONE)}</span></a>
<a class="hdr-btn wa" data-wa href="https://wa.me/{WA_D}?text={quote(WA_MSG)}" aria-label="Chat on WhatsApp">{SVG["wa"]}<span class="t">WhatsApp</span></a>
<button class="burger" id="burger" aria-label="Open menu" aria-expanded="false" aria-controls="nav">{SVG["menu"]}</button>
</div></div></header>
<div id="geo-banner" class="geo-banner" hidden><div class="container"><span id="geo-text"></span> <a id="geo-link" href="#"></a><button class="geo-close" aria-label="Dismiss">&times;</button></div></div>'''


def footer_html(d):
    h = lambda t="": rel(d, t)
    svc = "".join(f'<li><a href="{h(p_service(s["slug"]))}">{E(s["name"])}</a></li>' for s in SERVICES)
    countries = "".join(f'<li><a href="{h(p_country(k))}">SEO Services in {E(c["name"])}</a></li>' for k, c in COUNTRIES.items())
    company = "".join(f'<li><a href="{h(p)}">{E(n)}</a></li>' for p, n in [
        ("about/", "About Us"), ("contact/", "Contact"), ("seo-services-near-me/", "SEO Services Near Me"),
        ("industries/", "All Industries"), ("locations/", "All Locations"), ("site-map/", "HTML Site Map"),
        ("privacy-policy/", "Privacy Policy"), ("terms/", "Terms of Service")])
    more = ""
    for k, c in COUNTRIES.items():
        cl = "".join(f'<li><a href="{h(p_city(k, city[0]))}">SEO in {E(city[0])}</a></li>' for city in CITIES[k][:8])
        il = "".join(f'<li><a href="{h(p_ind(k, s))}">{E(ind_info(k, s)["n"])}</a></li>' for s in c["ind"][:8])
        more += f'<h4>{E(c["name"])}: popular cities</h4><ul>{cl}</ul><h4>{E(c["name"])}: SEO by industry</h4><ul>{il}</ul>'
    return f'''<footer class="site-footer"><div class="container">
<div class="fgrid">
<div><h3 data-brand>{E(BRAND)}</h3><p>{E(TAGLINE)} helping businesses in the UK, USA and India get found on Google and turn searches into enquiries.</p>
<ul><li><a data-tel href="tel:+{PHONE_D}">{SVG["phone"]} <span data-phone>{E(PHONE)}</span></a></li>
<li><a data-wa href="https://wa.me/{WA_D}?text={quote(WA_MSG)}">{SVG["wa"]} WhatsApp us</a></li>
<li><a data-mail href="mailto:{E(EMAIL)}">{SVG["mail"]} <span data-email>{E(EMAIL)}</span></a></li></ul></div>
<div><h3>Services</h3><ul>{svc}</ul></div>
<div><h3>Countries</h3><ul>{countries}</ul></div>
<div><h3>Company</h3><ul>{company}</ul></div>
</div>
<div class="fmore">{more}</div>
<div class="fbottom">&copy; <span data-year>{datetime.date.today().year}</span> <span data-brand>{E(BRAND)}</span>. All rights reserved.</div>
</div></footer>
<div class="bottom-bar" role="complementary" aria-label="Quick contact"><div class="container bb">
<span class="bb-text"><strong data-brand>{E(BRAND)}</strong> &middot; <span data-tagline>{E(TAGLINE)}</span></span>
<div class="bb-actions">
<a data-tel href="tel:+{PHONE_D}">{SVG["phone"]} Call</a>
<a class="w" data-wa href="https://wa.me/{WA_D}?text={quote(WA_MSG)}">{SVG["wa"]} WhatsApp</a>
<a class="p" href="{h("contact/")}#quote">{SVG["chart"]} Free SEO Audit</a>
</div></div></div>'''


def crumbs_html(d, crumbs):
    if not crumbs or len(crumbs) < 2:
        return ""
    items = []
    for i, (name, path) in enumerate(crumbs):
        if i == len(crumbs) - 1:
            items.append(f'<li aria-current="page">{E(name)}</li>')
        else:
            items.append(f'<li><a href="{rel(d, path)}">{E(name)}</a></li>')
    return f'<nav class="crumbs" aria-label="Breadcrumb"><div class="container"><ol>{"".join(items)}</ol></div></nav>'


def crumb_schema(crumbs):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{SITE}/{p}" if p else f"{SITE}/"}
        for i, (n, p) in enumerate(crumbs)]}


def faq_html(items):
    return '<div class="faq-list">' + "".join(
        f'<details class="faq"><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in items) + "</div>"


def faq_schema(items):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}


def org_schema():
    data = {"@context": "https://schema.org", "@type": "ProfessionalService", "@id": f"{SITE}/#org", "name": BRAND,
            "description": f"{BRAND} is an SEO and lead generation agency serving businesses in the United Kingdom, United States and India.",
            "url": f"{SITE}/", "email": EMAIL,
            "areaServed": [{"@type": "Country", "name": "United Kingdom"}, {"@type": "Country", "name": "United States"},
                           {"@type": "Country", "name": "India"}]}
    if "X" not in PHONE.upper():
        data["telephone"] = PHONE
    if CFG.get("logoImage"):
        data["logo"] = f"{SITE}/{CFG['logoImage'].lstrip('/')}"
    same = [v for v in CFG.get("social", {}).values() if v]
    if same:
        data["sameAs"] = same
    return data


def service_schema(name, desc, area_name, area_type="Country"):
    return {"@context": "https://schema.org", "@type": "Service", "name": name, "description": desc,
            "provider": {"@id": f"{SITE}/#org"}, "areaServed": {"@type": area_type, "name": area_name},
            "serviceType": "Search engine optimization"}


def page(path, title, desc, body, kws=None, crumbs=None, schemas=None, c=None, prio=0.5, freq="monthly",
         body_attrs="", noindex=False, sitemap=True):
    d = depth(path)
    suffix = f" | {BRAND}"
    if len(title) > 62 and title.endswith(suffix):
        title = title[: -len(suffix)]
    lang = c["lang"] if c else "en"
    locale = c["locale"] if c else "en_US"
    canon = f"{SITE}/{path}" if path else f"{SITE}/"
    kw = ", ".join(kws or [])
    robots = "noindex,follow" if noindex else "index,follow,max-image-preview:large"
    schema_blocks = "".join(
        f'<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>' for s in (schemas or []))
    doc = f'''<!doctype html>
<html lang="{lang}" data-base="{rel(d)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
{f'<meta name="keywords" content="{E(kw)}">' if kw else ''}
<meta name="robots" content="{robots}">
<meta name="author" content="{E(BRAND)}">
<meta name="theme-color" content="#0b1b3a">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{E(BRAND)}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:locale" content="{locale}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%230b1b3a'/%3E%3Cpath d='M14 44l12-14 9 8 15-20' fill='none' stroke='%2300b37e' stroke-width='6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<link rel="stylesheet" href="{rel(d, 'assets/style.css')}">
{schema_blocks}
</head>
<body {body_attrs}>
{header_html(d)}
{crumbs_html(d, crumbs)}
<main id="main">
{body}
</main>
{footer_html(d)}
<script src="{rel(d, 'assets/config.js')}"></script>
<script src="{rel(d, 'assets/data.js')}"></script>
<script src="{rel(d, 'assets/main.js')}" defer></script>
<script src="{rel(d, 'assets/geo.js')}" defer></script>
</body>
</html>
'''
    out = os.path.join(ROOT, path, "index.html") if path else os.path.join(ROOT, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    if sitemap:
        SITEMAP.append((path, prio, freq))
    ALL_PAGES.append((path, title))


# --------------------------------------------------------------- blocks
def hero(eyebrow, h1, lede, d, ctas=True, extra=""):
    btns = ""
    if ctas:
        btns = (f'<div class="hero-cta"><a class="btn btn-primary" href="#quote">Get a Free SEO Audit</a>'
                f'<a class="btn btn-wa" data-wa href="https://wa.me/{WA_D}?text={quote(WA_MSG)}">{SVG["wa"]} WhatsApp Us</a>'
                f'<a class="btn btn-ghost" data-tel href="tel:+{PHONE_D}">{SVG["phone"]} <span data-phone>{E(PHONE)}</span></a></div>')
    return (f'<section class="hero"><div class="container"><span class="eyebrow">{E(eyebrow)}</span><h1>{h1}</h1>'
            f'<p class="lede">{lede}</p>{btns}{extra}</div></section>')


def section(title, inner, intro="", alt=False, sid=""):
    idattr = f' id="{sid}"' if sid else ""
    head = f'<div class="section-head"><h2>{title}</h2>{f"<p>{intro}</p>" if intro else ""}</div>'
    return f'<section class="section{" alt" if alt else ""}"{idattr}><div class="container">{head}{inner}</div></section>'


def cards(items, cols="g3"):
    out = []
    for t, txt, href in items:
        if href:
            out.append(f'<a class="card" href="{href}"><h3>{E(t)}</h3><p>{E(txt)}</p><span class="more">Learn more &rarr;</span></a>')
        else:
            out.append(f'<div class="card"><h3>{E(t)}</h3><p>{E(txt)}</p></div>')
    return f'<div class="grid {cols}">{"".join(out)}</div>'


def steps(items):
    return '<div class="grid g3">' + "".join(
        f'<div class="card"><span class="num">{i + 1}</span><h3>{E(t)}</h3><p>{E(x)}</p></div>' for i, (t, x) in enumerate(items)) + "</div>"


def chips(items):
    return '<ul class="chips">' + "".join(f'<li><a href="{h}">{E(t)}</a></li>' for t, h in items) + "</ul>"


def kwchips(words):
    return '<ul class="chips kw">' + "".join(f"<li><span>{E(w)}</span></li>" for w in words) + "</ul>"


def linklist(items):
    return '<ul class="linkcols">' + "".join(f'<li><a href="{h}">{E(t)}</a></li>' for t, h in items) + "</ul>"


def testimonials_block():
    return ('<section class="section alt" id="testimonials-section" hidden><div class="container">'
            '<div class="section-head"><h2>What Our Clients Say</h2></div><div id="testimonials"></div></div></section>')


def form_block(context, heading="Get Your Free SEO Audit", sub=None, extra_hidden=""):
    sub = sub or "Tell us about your business and we will review your website, competitors and search opportunities. No obligation."
    return f'''<section class="section cta" id="quote"><div class="container grid g2">
<div><h2>{E(heading)}</h2><p>{E(sub)}</p>
<ul class="checks"><li>Review of your current search visibility</li><li>Competitor and keyword opportunities</li><li>Clear, prioritised recommendations</li><li>Honest advice, no rankings guarantees</li></ul>
<p>Prefer to talk? Call <a data-tel data-phone href="tel:+{PHONE_D}" style="color:#ffb703;font-weight:700">{E(PHONE)}</a> or <a data-wa href="https://wa.me/{WA_D}?text={quote(WA_MSG)}" style="color:#ffb703;font-weight:700">message us on WhatsApp</a>.</p></div>
<form class="lead-form" data-w3 data-context="{E(context)}" novalidate>
<label>Your name<input type="text" name="name" required autocomplete="name"></label>
<label>Email address<input type="email" name="email" required autocomplete="email"></label>
<label>Phone / WhatsApp<input type="tel" name="phone" autocomplete="tel"></label>
<label>Website URL<input type="text" name="website" placeholder="https://"></label>
<label>How can we help?<textarea name="message" rows="3"></textarea></label>
<input type="checkbox" name="botcheck" class="hp" tabindex="-1" autocomplete="off">
<button class="btn btn-primary" type="submit">Request My Free Audit</button>
<div class="form-status" role="status" aria-live="polite"></div>
</form></div></section>'''


# ---------------------------------------------------------------- pages
def build_home():
    d = 0
    h = lambda t="": rel(d, t)
    country_cards = "".join(
        f'<a class="card" href="{h(p_country(k))}"><h3>SEO Services in {E(c["name"])}</h3><p>{E(c["market"])}</p>'
        f'<span class="more">Explore {E(c["short"])} &rarr;</span></a>' for k, c in COUNTRIES.items())
    ind_blocks = ""
    for k, c in COUNTRIES.items():
        ind_blocks += f'<h3>{E(c["name"])}</h3>' + chips(
            [(ind_info(k, s)["n"], h(p_ind(k, s))) for s in c["ind"]]) + "<br>"
    city_blocks = ""
    for k, c in COUNTRIES.items():
        city_blocks += f'<h3>{E(c["name"])}</h3>' + chips(
            [(f"SEO in {city[0]}", h(p_city(k, city[0]))) for city in CITIES[k][:10]]) + f'<p><a href="{h(p_country(k))}#locations">All {E(c["short"])} locations &rarr;</a></p>'
    svc_cards = cards([(s["name"], s["short"], h(p_service(s["slug"]))) for s in SERVICES], "g4")
    how = steps([("Free audit", "We review your website, search visibility and competitors to find the biggest opportunities."),
                 ("Strategy", "You get a clear plan built around your services, locations and lead goals."),
                 ("Execution", "We fix technical issues, improve content and earn quality links."),
                 ("Reporting", "Monthly reports show rankings, traffic and the enquiries SEO is producing.")])
    why = cards([
        ("Lead-focused SEO", "We measure calls, forms and WhatsApp enquiries, not just rankings and traffic.", None),
        ("Three markets, one team", "Local knowledge of search behaviour in the UK, USA and India.", None),
        ("Industry-specific strategy", "Dedicated approaches for dozens of industries and their sub-sectors.", None),
        ("Location-level pages", "City pages that help you rank where your customers actually search.", None),
        ("Transparent reporting", "Plain-language monthly reports so you always know what is happening.", None),
        ("White-hat methods", "Search-engine-friendly techniques that protect your website long term.", None)])
    faqs = [
        (f"What does {BRAND} do?", f"{BRAND} is an SEO and lead generation agency. We help businesses rank higher on Google and Google Maps and turn that visibility into calls, forms and WhatsApp enquiries."),
        ("Which countries do you serve?", "We serve businesses across the United Kingdom, the United States and India, with dedicated industry and city pages for each market."),
        ("Do you guarantee first-page rankings?", "No ethical agency can guarantee specific rankings because search engines control the results. We guarantee honest work, clear reporting and a strategy built on proven methods."),
        ("How long does SEO take to show results?", "Most businesses see early improvements within three to six months. Highly competitive markets can take longer."),
        ("Can you work with my industry?", "We have dedicated service pages for many industries, from travel and hospitality to healthcare, law, real estate, ecommerce and more. If yours is not listed, contact us."),
        ("How much does SEO cost?", "Pricing depends on your goals, competition and website. Request a free audit and we will recommend a plan and quote that fits.")]
    body = hero("SEO & Lead Generation Agency · UK · USA · India",
                "SEO Services &amp; Lead Generation for Businesses in the UK, USA &amp; India",
                f'{E(BRAND)} gets your business found on Google and turns searches into enquiries. '
                f'Looking for SEO services in <strong data-geo-city>your city</strong>? You are in the right place.', d,
                extra='<div class="trust"><span>Local and national SEO</span><span>Industry-specific strategies</span><span>City-level landing pages</span><span>Transparent monthly reporting</span></div>')
    body += section("Our SEO Services", svc_cards, "Everything you need to rank, attract and convert more customers from search.")
    body += section("SEO Services by Country", f'<div class="grid g3">{country_cards}</div>', alt=True)
    body += section("How Our SEO Process Works", how)
    body += section("SEO Services by Industry", ind_blocks, "Pick your country and industry to see specialist SEO services and sub-sectors.", alt=True)
    body += section("Top Locations We Serve", city_blocks, "City pages for the most populated towns and cities in each country.")
    body += section(f"Why Choose {E(BRAND)}", why, alt=True)
    body += testimonials_block()
    body += section("Frequently Asked Questions", faq_html(faqs))
    body += form_block("Home page")
    page("", f"SEO Services & Lead Generation | UK, USA, India | {BRAND}",
         f"{BRAND} provides SEO services and lead generation for businesses in the UK, USA and India. Local SEO, ecommerce SEO and industry-specific strategies. Get a free audit.",
         body, ["SEO services", "lead generation", "SEO agency", "local SEO", "SEO services UK", "SEO services USA", "SEO services India", BRAND],
         [("Home", "")], [org_schema(), faq_schema(faqs)], prio=1.0, freq="weekly",
         body_attrs='data-city="" data-country=""')


def build_country(ckey):
    c = COUNTRIES[ckey]
    d = 1
    h = lambda t="": rel(d, t)
    t = sp(c)
    inds = [ind_info(ckey, s) for s in c["ind"]]
    ind_cards = cards([(f"SEO for {i['n']}", f"Rank higher and win more {i['lead']} with {t['opt']} built for {i['p']}.", h(p_ind(ckey, i["slug"]))) for i in inds])
    city_chips = chips([(f"SEO Services in {x[0]}", h(p_city(ckey, x[0]))) for x in CITIES[ckey]])
    svc_cards = cards([(s["name"], s["short"], h(p_service(s["slug"]))) for s in SERVICES], "g4")
    faqs = [
        (f"Do you provide SEO services across {c['name']}?", f"Yes. We work with businesses in every major city in {c['name']}, and we have dedicated pages for {len(CITIES[ckey])} of the most populated towns and cities."),
        ("Which industries do you specialise in?", f"We have specialist pages for {len(inds)} industries in {c['name']}, including {inds[0]['p']}, {inds[1]['p']} and {inds[2]['p']}."),
        ("How quickly can I expect results?", "Early improvements often appear within three to six months, depending on your competition, website and budget."),
        ("Can I get a free SEO audit?", "Yes. Use the form on this page to request a free audit of your website.")]
    body = hero(f"{c['name']} SEO Agency", f"SEO Services in {E(c['name'])}",
                f"{E(c['market'])} {E(BRAND)} helps {E(c['short'])} businesses rank higher and generate consistent enquiries from search.", d)
    body += section(f"SEO Services We Offer in {E(c['name'])}", svc_cards, alt=True)
    body += section(f"SEO by Industry in {E(c['name'])}", ind_cards, f"Choose your industry to see specialist SEO services and sub-categories.", sid="industries")
    body += section(f"SEO Services by City in {E(c['name'])}", city_chips, "Local SEO pages for the most populated towns and cities.", alt=True, sid="locations")
    body += section("Frequently Asked Questions", faq_html(faqs))
    body += form_block(f"Country: {c['name']}")
    crumbs = [("Home", ""), (f"SEO Services in {c['name']}", p_country(ckey))]
    page(p_country(ckey), f"SEO Services in {c['name']} | {BRAND}",
         f"Professional SEO services in {c['name']} for {len(inds)} industries and {len(CITIES[ckey])} major cities. Local SEO, lead generation and transparent reporting.",
         body, [f"SEO services {c['name']}", f"SEO company {c['short']}", f"local SEO {c['short']}", f"lead generation {c['short']}"],
         crumbs, [service_schema(f"SEO Services in {c['name']}", f"SEO and lead generation services for businesses in {c['name']}.", c["name"]), crumb_schema(crumbs), faq_schema(faqs)],
         c=c, prio=0.9, freq="weekly", body_attrs=f'data-city="" data-country="{ckey}"')


def sub_faq_common(name, p, city_or_country, lead):
    return [
        (f"How long does SEO take for {p} in {city_or_country}?", "Many businesses see early movement in three to six months. The timeline depends on competition, your website's current condition and the work completed each month. No agency can honestly guarantee specific rankings."),
        (f"Do you offer local SEO for {p} in {city_or_country}?", f"Yes. Local SEO is a core part of our work for {p}. We optimize your Google Business Profile, local pages, citations and reviews so you appear where customers search."),
        ("Will I receive regular reports?", f"Yes. You receive a monthly report covering rankings, traffic and the {lead} generated by search, written in plain language."),
        ("How do I get started?", "Request a free SEO audit using the form on this page. We will review your website and recommend a clear plan.")]


def build_industry(ckey, slug):
    c = COUNTRIES[ckey]
    i = ind_info(ckey, slug)
    d = 2
    h = lambda t="": rel(d, t)
    t = sp(c)
    sub_cards = cards([(s, f"Specialist SEO for {s.lower()} in {c['name']}.", h(p_sub(ckey, slug, s))) for s in i["subs"]])
    city_chips = chips([(f"SEO services for {i['p']} in {x[0]}", h(p_cityind(ckey, x[0], slug))) for x in CITIES[ckey]])
    serv = cards([
        ("Local SEO", f"Win map-pack visibility and \"near me\" searches for your {i['p']} business.", h(p_service("local-seo"))),
        ("Keyword research", f"Target the searches {i['buyer']} use when they are ready to enquire.", h(p_service("seo-audit"))),
        ("On-page SEO", f"Pages and content built to rank and to convert into {i['lead']}.", h(p_service("on-page-seo"))),
        ("Technical SEO", "Fast, crawlable, mobile-friendly websites that search engines trust.", h(p_service("technical-seo"))),
        ("Content marketing", f"Guides and service pages that answer what {i['buyer']} ask.", h(p_service("content-marketing"))),
        ("Link building", "Quality links that build authority in your industry and region.", h(p_service("link-building")))])
    kws = [f"SEO services for {i['p']}", f"{i['p']} SEO company in {c['short']}", f"best SEO agency for {i['p']}",
           f"local SEO for {i['p']}", f"{i['p']} marketing {c['short']}", f"{i['p']} lead generation"] + [f"SEO for {s.lower()}" for s in i["subs"][:3]]
    faqs = sub_faq_common(i["n"], i["p"], c["name"], i["lead"])
    body = hero(f"{i['n']} SEO · {c['name']}", f"SEO Services for {E(i['n'])} in {E(c['short'])}",
                f"{E(BRAND)} helps {E(i['p'])} across {E(c['name'])} rank higher on Google and generate more {E(i['lead'])}. "
                f"Our {t['optv']}d strategies are built around how {E(i['buyer'])} really search.", d)
    body += section(f"How We Help {E(i['n'])}", serv, f"A complete SEO {t['prog']} for {E(i['p'])} in {E(c['name'])}.", alt=True)
    body += section(f"Specialisations: SEO for {E(i['n'])} Sub-Categories".replace("Specialisations", "Specialties" if c["us"] else "Specialisations"), sub_cards,
                    f"We tailor our approach to each type of {E(i['p'])} business.")
    body += section(f"SEO Services for {E(i['n'])} by City", city_chips, f"Local SEO pages for {E(i['p'])} in the major cities of {E(c['name'])}.", alt=True, sid="cities")
    body += section("Keywords We Target", kwchips(kws), "Examples of the search terms we research and target for your industry.")
    body += section("Frequently Asked Questions", faq_html(faqs), alt=True)
    body += form_block(f"{i['n']} - {c['name']}")
    crumbs = [("Home", ""), (c["name"], p_country(ckey)), (f"SEO for {i['n']}", p_ind(ckey, slug))]
    page(p_ind(ckey, slug), f"SEO Services for {i['n']} in {c['short']} | {BRAND}",
         f"Specialist SEO services for {i['p']} in {c['name']}. Rank higher, get more {i['lead']} and track real results. Free SEO audit available.",
         body, kws, crumbs,
         [service_schema(f"SEO Services for {i['n']}", f"SEO services for {i['p']} in {c['name']}.", c["name"]), crumb_schema(crumbs), faq_schema(faqs)],
         c=c, prio=0.7, body_attrs=f'data-city="" data-country="{ckey}"')


def build_sub(ckey, slug, sub):
    c = COUNTRIES[ckey]
    i = ind_info(ckey, slug)
    d = 3
    h = lambda t="": rel(d, t)
    t = sp(c)
    low = sub.lower()
    sibs = chips([(s, h(p_sub(ckey, slug, s))) for s in i["subs"] if s != sub])
    top_cities = chips([(f"SEO for {i['p']} in {x[0]}", h(p_cityind(ckey, x[0], slug))) for x in CITIES[ckey][:12]])
    intro1 = pick(sub + ckey, [
        f"Competition for {low} in {c['name']} is growing, and customers compare several providers online before they get in touch.",
        f"Most {i['buyer']} start their search on Google. If your {low} business is not visible there, you are missing {i['lead']} every day.",
        f"Whether you are a small local business or a growing brand, strong search visibility is one of the most reliable ways for {low} to attract new customers."])
    benefits = cards([
        ("Search visibility", f"Appear when people search for {low} in your area.", None),
        ("More qualified leads", f"Attract {i['buyer']} who are actively looking for what you offer.", None),
        ("Trust and authority", "Strong reviews, content and links show customers why they should choose you.", None),
        ("Measurable results", f"Track calls, forms and WhatsApp enquiries from search.", None)], "g4")
    work = steps([("Audit", f"Review your website, Google Business Profile and competitors in {c['name']}."),
                  ("Plan", f"Build a keyword and content plan for {low}."),
                  ("Optimise" if not c["us"] else "Optimize", "Improve pages, speed, local listings and calls to action."),
                  ("Grow", "Earn links and reviews, then report progress every month.")])
    faqs = [(f"What does SEO for {low} include?", f"It includes keyword research, on-page {t['opt']}, technical fixes, local SEO, content and link building tailored to {low} in {c['name']}."),
            (f"How long does SEO take for {low}?", "Most businesses see early movement in three to six months. Results depend on competition and the work completed. No agency can guarantee rankings."),
            (f"Can you help {low} in my city?", f"Yes. We have local SEO pages for the major cities of {c['name']}. Choose your city below or contact us."),
            ("How do I start?", "Request a free SEO audit using the form on this page.")]
    body = hero(f"{c['name']} · {i['n']}", f"SEO for {E(sub)} in {E(c['short'])}",
                f"{E(intro1)} {E(BRAND)} provides specialist SEO for {E(low)} to help you rank higher and win more {E(i['lead'])}.", d)
    body += section(f"Why {E(sub)} Need SEO", benefits, alt=True)
    body += section("Our SEO Process", work)
    body += section(f"SEO for {E(sub)} in Top Cities", top_cities, f'<a href="{h(p_ind(ckey, slug))}#cities">See all cities for SEO services for {E(i["p"])}</a>', alt=True)
    body += section("Related Specialties" if c["us"] else "Related Specialisations", sibs + f'<p><br><a href="{h(p_ind(ckey, slug))}">&larr; Back to SEO services for {E(i["n"])}</a></p>')
    body += section("Frequently Asked Questions", faq_html(faqs), alt=True)
    body += form_block(f"{sub} - {c['name']}")
    crumbs = [("Home", ""), (c["name"], p_country(ckey)), (f"SEO for {i['n']}", p_ind(ckey, slug)), (sub, p_sub(ckey, slug, sub))]
    page(p_sub(ckey, slug, sub), f"SEO for {sub} in {c['short']} | {BRAND}",
         f"SEO services for {low} in {c['name']}. Improve rankings, earn more {i['lead']} and track results with {BRAND}. Free audit.",
         body, [f"SEO for {low}", f"{low} SEO services {c['short']}", f"{low} marketing", f"{low} lead generation"],
         crumbs, [service_schema(f"SEO for {sub}", f"SEO services for {low} in {c['name']}.", c["name"]), crumb_schema(crumbs), faq_schema(faqs)],
         c=c, prio=0.6, body_attrs=f'data-city="" data-country="{ckey}"')


def build_city(ckey, city):
    name, region, note = city
    c = COUNTRIES[ckey]
    d = 2
    h = lambda t="": rel(d, t)
    t = sp(c)
    inds = [ind_info(ckey, s) for s in c["ind"]]
    ind_cards = cards([(f"SEO for {i['n']} in {name}", f"Get more {i['lead']} in {name} with local SEO.", h(p_cityind(ckey, name, i['slug']))) for i in inds])
    nearby = chips([(f"SEO Services in {x[0]}", h(p_city(ckey, x[0]))) for x in CITIES[ckey] if x[0] != name])
    svc = cards([(s["name"], s["short"], h(p_service(s['slug']))) for s in SERVICES[:6]])
    faqs = [(f"Do you offer SEO services in {name}?", f"Yes. {BRAND} provides local SEO and lead generation services for businesses in {name} and across {region}."),
            (f"Which industries do you work with in {name}?", f"We have dedicated pages for {len(inds)} industries in {name}, including {inds[0]['p']}, {inds[1]['p']} and {inds[2]['p']}."),
            (f"How long does SEO take in {name}?", "Many businesses see early progress in three to six months. Competitive industries and new websites can take longer."),
            ("How can I get a free audit?", "Fill in the form on this page, call us or message us on WhatsApp.")]
    body = hero(f"{name}, {region}", f"SEO Services in {E(name)}, {E(c['short'])}",
                f"{E(name)} is {E(note)}. {E(BRAND)} helps {E(name)} businesses rank higher on Google and Google Maps and turn searches into enquiries.", d)
    body += section(f"SEO Services for Industries in {E(name)}", ind_cards, f"Choose your industry for {E(name)}-specific SEO services.", sid="industries")
    body += section(f"Our SEO Services in {E(name)}", svc, alt=True)
    body += section(f"SEO Services in Other {E(c['short'])} Cities", nearby, alt=False)
    body += section("Frequently Asked Questions", faq_html(faqs), alt=True)
    body += form_block(f"City: {name}, {c['name']}")
    crumbs = [("Home", ""), (c["name"], p_country(ckey)), (name, p_city(ckey, name))]
    page(p_city(ckey, name), f"SEO Services in {name}, {c['short']} | {BRAND}",
         f"Professional SEO services in {name}, {region}. Local SEO, lead generation and industry-specific strategies for {name} businesses. Get a free SEO audit.",
         body, [f"SEO services {name}", f"SEO company {name}", f"local SEO {name}", f"SEO agency {name}", f"digital marketing {name}"],
         crumbs, [service_schema(f"SEO Services in {name}", f"SEO services for businesses in {name}, {region}.", name, "City"), crumb_schema(crumbs), faq_schema(faqs)],
         c=c, prio=0.7, body_attrs=f'data-city="{E(name)}" data-country="{ckey}"')


def build_cityind(ckey, city, slug):
    name, region, note = city
    c = COUNTRIES[ckey]
    i = ind_info(ckey, slug)
    d = 3
    h = lambda t="": rel(d, t)
    t = sp(c)
    seed = f"{ckey}{name}{slug}"
    lede = pick(seed + "a", [
        f"{BRAND} provides specialist SEO services for {i['p']} in {name}. We help you rank higher on Google and Google Maps so more {i['buyer']} in {name} find you and send {i['lead']}.",
        f"Want more {i['lead']} in {name}? Your website needs to appear when {i['buyer']} search. Our {name} SEO {t['prog']} for {i['p']} is built to do exactly that.",
        f"Competition for {i['p']} in {name} grows every year. {BRAND} builds search visibility that brings steady {i['lead']} from {name} and the wider {region} area."])
    why1 = pick(seed + "b", [
        f"{name} is {note}. For {i['p']}, that means strong demand but tough competition: {i['buyer']} compare several providers on Google, Maps and review sites before they make contact.",
        f"With {name} being {note}, local {i['buyer']} have plenty of choice. The businesses that appear first in search results and map listings are the ones that get noticed.",
        f"Located in {region}, {name} is {note}. {i['buyer'].capitalize()} here search online first, so visibility on Google is a major factor in who wins the enquiry."])
    why2 = (f"A well-planned SEO strategy places your {i['p']} business in front of {i['buyer']} at the exact moment they are searching. "
            f"Unlike paid ads, organic visibility keeps working month after month, so the cost of generating {i['lead']} can fall over time.")
    inc = cards([
        ("Local SEO & Google Business Profile", f"A fully {t['optv']}d Google Business Profile and strong local signals so your {i['p']} business shows up in {name} map results.", None),
        (f"Keyword research for {name}", f"Searches that {name} {i['buyer']} actually use, mapped to the right pages.", None),
        ("On-page optimisation".replace("isation", t["opt"].replace("optimization", "ization") if False else "isation") if not c["us"] else "On-page optimization", f"Titles, headings and content refined to match search intent and drive {i['lead']}.", None),
        ("Technical SEO", "Speed, mobile usability, indexing and structured data fixes.", None),
        ("Content & link building", f"Helpful content and quality links that build authority for {i['p']} in {name}.", None),
        ("Tracking & monthly reporting", f"Calls, forms and WhatsApp enquiries tracked so you see the {i['lead']} SEO delivers.", None)], "g3")
    proc = steps([
        ("Audit", f"We review your website, Google Business Profile and the top competitors in {name}."),
        ("Research", f"We identify the keywords and questions {i['buyer']} in {name} search for."),
        ("Fix & optimise" if not c["us"] else "Fix & optimize", "We improve technical health, page content and local listings."),
        ("Build authority", "We create content and earn links and reviews that strengthen trust."),
        ("Report & refine", "Monthly reporting shows progress, and we refine the plan from the data.")])
    subs = chips([(s, h(p_sub(ckey, slug, s))) for s in i["subs"]])
    kws = [f"SEO services for {i['p']} in {name}", f"best {i['p']} SEO company {name}", f"{i['p']} SEO {name}",
           f"{i['p']} near me in {name}", f"{i['p']} marketing {name}", f"local SEO for {i['p']} {name}"] + [f"{s.lower()} {name}" for s in i["subs"][:3]]
    others_ind = chips([(f"SEO for {x['n']} in {name}", h(p_cityind(ckey, name, x['slug']))) for x in (ind_info(ckey, s) for s in c["ind"]) if x["slug"] != slug])
    other_cities = chips([(f"SEO for {i['p']} in {x[0]}", h(p_cityind(ckey, x[0], slug))) for x in CITIES[ckey] if x[0] != name])
    faqs = [(f"How long does SEO take for {i['p']} in {name}?", "Many businesses see early movement in three to six months. Timing depends on competition, your website and the work completed. No agency can honestly guarantee specific rankings."),
            (f"Do you offer local SEO for {i['p']} in {name}?", f"Yes. We optimize your Google Business Profile, build {name}-focused pages, manage citations and help you earn reviews so you appear in local results."),
            ("Will I receive reports?", f"Yes. Every month you receive a plain-language report showing rankings, traffic and the {i['lead']} coming from search."),
            (f"Can you work with {i['p']} outside {name}?", f"Yes. We serve {i['p']} across {c['name']}. See the other cities listed below or contact us."),
            ("How do I get started?", "Request a free SEO audit with the form on this page, call us or message us on WhatsApp.")]
    body = hero(f"{name}, {region} · {i['n']}", f"SEO Services for {E(i['n'])} in {E(name)}", E(lede), d)
    body += section(f"Why {E(i['n'])} in {E(name)} Need SEO", f'<div class="prose"><p>{E(why1)}</p><p>{E(why2)}</p></div>', alt=True)
    body += section(f"What Our SEO Service for {E(i['n'])} in {E(name)} Includes", inc)
    body += section(f"Types of {E(i['n'])} We Support" if True else "", subs, f'Specialist pages for each sub-category.', alt=True)
    body += section("Our SEO Process", proc)
    body += section(f"Search Terms We Target in {E(name)}", kwchips(kws), alt=True)
    body += section("Frequently Asked Questions", faq_html(faqs))
    body += section(f"More SEO Services in {E(name)}", others_ind + f'<p><br><a href="{h(p_city(ckey, name))}">&larr; All SEO services in {E(name)}</a></p>', alt=True)
    body += section(f"SEO for {E(i['n'])} in Other Cities", other_cities)
    body += form_block(f"{i['n']} in {name}, {c['name']}", f"Get a Free SEO Audit for Your {name} Business")
    crumbs = [("Home", ""), (c["name"], p_country(ckey)), (name, p_city(ckey, name)), (f"SEO for {i['n']}", p_cityind(ckey, name, slug))]
    page(p_cityind(ckey, name, slug), f"SEO Services for {i['n']} in {name} | {BRAND}",
         f"SEO services for {i['p']} in {name}, {region}. Rank higher on Google, get more {i['lead']} and track results. Free audit from {BRAND}.",
         body, kws, crumbs,
         [service_schema(f"SEO Services for {i['n']} in {name}", f"Local SEO for {i['p']} in {name}, {region}.", name, "City"), crumb_schema(crumbs), faq_schema(faqs)],
         c=c, prio=0.6, body_attrs=f'data-city="{E(name)}" data-country="{ckey}"')


# ---- core pages
def build_services():
    d = 1
    h = lambda t="": rel(d, t)
    body = hero("SEO Services", "SEO Services to Grow Your Business",
                f"From local SEO to technical fixes and content, {E(BRAND)} offers every service you need to get found on Google and turn visitors into leads.", d)
    body += section("Our SEO Services", cards([(s["name"], s["short"], h(p_service(s["slug"]))) for s in SERVICES], "g4"))
    body += section("Choose Your Country", cards([(f"SEO Services in {c['name']}", c["market"], h(p_country(k))) for k, c in COUNTRIES.items()]), alt=True)
    body += form_block("Services overview")
    crumbs = [("Home", ""), ("Services", "services/")]
    page("services/", f"SEO Services: Local, Ecommerce, Technical | {BRAND}",
         f"Explore {BRAND} SEO services: local SEO, ecommerce SEO, technical SEO, content, link building, audits and lead generation for the UK, USA and India.",
         body, ["SEO services", "SEO company", "local SEO", "ecommerce SEO", "technical SEO", "link building"], crumbs,
         [crumb_schema(crumbs)], prio=0.8, body_attrs='data-city="" data-country=""')
    for s in SERVICES:
        d = 2
        h = lambda t="", d=d: rel(d, t)
        intro = "".join(f"<p>{E(x)}</p>" for x in s["intro"])
        pts = cards([(a, b, None) for a, b in s["points"]])
        body = hero(s["name"], E(s["name"]), E(s["short"]), d)
        body += section(f"About {E(s['name'])}", f'<div class="prose">{intro}</div>', alt=True)
        body += section("What Is Included", pts)
        body += section("Available in the UK, USA and India", chips([(f"{s['name']} in {c['name']}", h(p_country(k))) for k, c in COUNTRIES.items()]) +
                        f'<p><br>Browse <a href="{h("industries/")}">SEO services by industry</a> or <a href="{h("locations/")}">find your city</a>.</p>', alt=True)
        body += section("Frequently Asked Questions", faq_html(s["faqs"]))
        other = chips([(x["name"], h(p_service(x["slug"]))) for x in SERVICES if x["slug"] != s["slug"]])
        body += section("Related Services", other, alt=True)
        body += form_block(s["name"])
        crumbs = [("Home", ""), ("Services", "services/"), (s["name"], p_service(s["slug"]))]
        page(p_service(s["slug"]), f"{s['name']} | {BRAND}",
             f"{s['short']} {BRAND} offers {s['name'].lower()} for businesses in the UK, USA and India. Request a free audit.",
             body, [s["name"].lower(), f"{s['name'].lower()} UK", f"{s['name'].lower()} USA", f"{s['name'].lower()} India"], crumbs,
             [service_schema(s["name"], s["short"], "United Kingdom, United States, India"), crumb_schema(crumbs), faq_schema(s["faqs"])],
             prio=0.8, body_attrs='data-city="" data-country=""')


def build_industries_hub():
    d = 1
    h = lambda t="": rel(d, t)
    body = hero("Industries", "SEO Services by Industry and Sub-Category",
                f"{E(BRAND)} has specialist SEO strategies for businesses across the UK, USA and India. Choose your country, industry and sub-category.", d, ctas=False)
    for k, c in COUNTRIES.items():
        blocks = ""
        for s in c["ind"]:
            i = ind_info(k, s)
            blocks += (f'<h3><a href="{h(p_ind(k, s))}">SEO for {E(i["n"])}</a></h3>' +
                       chips([(sub, h(p_sub(k, s, sub))) for sub in i["subs"]]) + "<br>")
        body += section(f"Industries in {E(c['name'])}", blocks, alt=(k == "uk"))
    body += form_block("Industries hub")
    crumbs = [("Home", ""), ("Industries", "industries/")]
    page("industries/", f"SEO Services by Industry: UK, USA, India | {BRAND}",
         f"Industry-specific SEO services for tour operators, law firms, dentists, real estate, ecommerce and more across the UK, USA and India.",
         body, ["SEO for industries", "industry SEO services", "SEO by industry"], crumbs, [crumb_schema(crumbs)], prio=0.8,
         body_attrs='data-city="" data-country=""')


def build_locations_hub():
    d = 1
    h = lambda t="": rel(d, t)
    body = hero("Locations", "SEO Services by City: UK, USA & India",
                f"Find local SEO services in the most populated towns and cities of the UK, USA and India.", d, ctas=False)
    for k, c in COUNTRIES.items():
        blocks = "".join(f'<h3><a href="{h(p_city(k, x[0]))}">SEO Services in {E(x[0])}</a></h3>' +
                         chips([(f"{ind_info(k, s)['n']}", h(p_cityind(k, x[0], s))) for s in c["ind"]]) + "<br>" for x in CITIES[k][:6])
        body += section(f"{E(c['name'])}: Top Cities", chips([(f"SEO Services in {x[0]}", h(p_city(k, x[0]))) for x in CITIES[k]]) +
                        f'<br><p><a href="{h(p_country(k))}">Go to the {E(c["name"])} hub &rarr;</a></p>', alt=(k == "uk"))
    body += form_block("Locations hub")
    crumbs = [("Home", ""), ("Locations", "locations/")]
    page("locations/", f"SEO Services by City in UK, USA & India | {BRAND}",
         "Local SEO services in the top cities of the UK, USA and India, including London, New York, Dallas, Houston, Mumbai, Delhi and more.",
         body, ["SEO services by city", "local SEO agency", "SEO company near me"], crumbs, [crumb_schema(crumbs)], prio=0.8,
         body_attrs='data-city="" data-country=""')


def build_near_me():
    d = 1
    h = lambda t="": rel(d, t)
    country_blocks = ""
    for k, c in COUNTRIES.items():
        country_blocks += f'<h3>{E(c["name"])}</h3>' + chips([(f"SEO in {x[0]}", h(p_city(k, x[0]))) for x in CITIES[k]]) + "<br>"
    body = f'''<section class="hero"><div class="container"><span class="eyebrow">Local SEO · UK · USA · India</span>
<h1 id="nm-h1">SEO Services Near Me</h1>
<p class="lede" id="nm-lede">Looking for an SEO company near you? {E(BRAND)} provides local SEO and lead generation services in major cities across the UK, USA and India. Choose your location below.</p>
<div class="hero-cta"><a class="btn btn-primary" href="#quote">Get a Free SEO Audit</a><a class="btn btn-wa" data-wa href="https://wa.me/{WA_D}?text={quote(WA_MSG)}">{SVG["wa"]} WhatsApp Us</a></div></div></section>'''
    body += '<section class="section alt" id="nm-result" hidden><div class="container"><div class="section-head"><h2>SEO Services Picked for Your Location</h2><p>Based on your approximate location.</p></div><ul class="linkcols" id="nm-links"></ul></div></section>'
    body += section("Choose Your City", country_blocks, "Select your city to see local SEO services and industry pages.")
    body += section("Our SEO Services", cards([(s["name"], s["short"], h(p_service(s["slug"]))) for s in SERVICES], "g4"), alt=True)
    body += form_block("SEO services near me")
    crumbs = [("Home", ""), ("SEO Services Near Me", "seo-services-near-me/")]
    page("seo-services-near-me/", f"SEO Services Near Me | Local SEO Company | {BRAND}",
         f"Find SEO services near you. {BRAND} provides local SEO in London, New York, Dallas, Mumbai, Delhi and many more UK, USA and India cities.",
         body, ["SEO services near me", "SEO company near me", "local SEO near me", "SEO agency near me"], crumbs, [crumb_schema(crumbs)],
         prio=0.8, freq="weekly", body_attrs='data-city="" data-country=""')


def build_about():
    d = 1
    h = lambda t="": rel(d, t)
    body = hero("About Us", f"About {E(BRAND)}", f"{E(BRAND)} is an SEO and lead generation agency that helps businesses in the UK, USA and India grow through search.", d, ctas=False)
    body += section("Who We Are", f'<div class="prose"><p>{E(BRAND)} helps businesses get found by customers who are already searching for their services. We combine technical SEO, local SEO, content and link building with a clear focus on the enquiries that search generates.</p><p>We work with businesses of all sizes, from local service providers to ecommerce stores and national brands, across the United Kingdom, United States and India.</p></div>', alt=True)
    body += section("How We Work", cards([
        ("Honest strategy", "We explain what is realistic, and we never promise guaranteed rankings.", None),
        ("White-hat methods", "We follow search engine guidelines to protect your website's long-term performance.", None),
        ("Focus on leads", "We track calls, forms and WhatsApp enquiries so SEO is tied to business results.", None),
        ("Clear communication", "Plain-language reports and regular check-ins.", None),
        ("Local relevance", "City and industry pages built for how customers search in each market.", None),
        ("Continuous improvement", "We test, learn and refine the plan from real data.", None)]))
    body += section("Where We Work", cards([(c["name"], c["market"], h(p_country(k))) for k, c in COUNTRIES.items()]), alt=True)
    body += form_block("About page")
    crumbs = [("Home", ""), ("About", "about/")]
    page("about/", f"About {BRAND} | SEO & Lead Generation Agency",
         f"Learn about {BRAND}, an SEO and lead generation agency serving businesses in the UK, USA and India.",
         body, [f"about {BRAND}", "SEO agency", "lead generation agency"], crumbs, [org_schema(), crumb_schema(crumbs)], prio=0.6,
         body_attrs='data-city="" data-country=""')


def build_contact():
    d = 1
    body = hero("Contact", f"Contact {E(BRAND)}", "Request a free SEO audit, ask a question or talk to our team.", d, ctas=False)
    body += f'''<section class="section"><div class="container grid g3">
<div class="card"><h3>Call us</h3><p><a data-tel data-phone href="tel:+{PHONE_D}">{E(PHONE)}</a></p></div>
<div class="card"><h3>WhatsApp</h3><p><a data-wa href="https://wa.me/{WA_D}?text={quote(WA_MSG)}">Chat with us on WhatsApp</a></p></div>
<div class="card"><h3>Email</h3><p><a data-mail data-email href="mailto:{E(EMAIL)}">{E(EMAIL)}</a></p></div></div></section>'''
    body += testimonials_block()
    body += form_block("Contact page", "Request Your Free SEO Audit")
    crumbs = [("Home", ""), ("Contact", "contact/")]
    page("contact/", f"Contact {BRAND} | Free SEO Audit",
         f"Contact {BRAND} for SEO services in the UK, USA and India. Call, WhatsApp, email or request a free audit.",
         body, [f"contact {BRAND}", "SEO quote", "free SEO audit"], crumbs, [org_schema(), crumb_schema(crumbs)], prio=0.7,
         body_attrs='data-city="" data-country=""')


def build_legal():
    crumbs = [("Home", ""), ("Privacy Policy", "privacy-policy/")]
    body = hero("Legal", "Privacy Policy", f"Last updated: {TODAY}", 1, ctas=False)
    body += section("Privacy Policy", f'''<div class="prose">
<h2>Information we collect</h2><p>When you submit a form on this website, we collect the details you provide, such as your name, email address, phone number, website and message. Form submissions are processed by Web3Forms and delivered to our email.</p>
<h2>Approximate location</h2><p>To show you the most relevant city page, this website makes an approximate, IP-based location lookup using a third-party service (ipwho.is) in your browser. We do not store this lookup, but we may include the detected city in your form submission to help us respond.</p>
<h2>How we use information</h2><p>We use your details to respond to your enquiry, provide SEO services and improve our website. We do not sell your personal information.</p>
<h2>Cookies and storage</h2><p>This website uses session storage in your browser to remember your detected city for the visit. Third-party widgets, such as a testimonials widget, may set their own cookies.</p>
<h2>Retention and your rights</h2><p>We keep enquiry data only as long as needed for business purposes. You may request access, correction or deletion of your data by emailing <a data-mail data-email href="mailto:{E(EMAIL)}">{E(EMAIL)}</a>.</p>
</div>''')
    page("privacy-policy/", f"Privacy Policy | {BRAND}", f"Privacy policy for {BRAND}: how we handle form data and approximate location.", body, None, crumbs, [crumb_schema(crumbs)], prio=0.3, freq="yearly", body_attrs='data-city="" data-country=""')
    crumbs = [("Home", ""), ("Terms of Service", "terms/")]
    body = hero("Legal", "Terms of Service", f"Last updated: {TODAY}", 1, ctas=False)
    body += section("Terms of Service", f'''<div class="prose">
<h2>Use of this website</h2><p>The content on this website is provided for general information. By using it, you agree to use it lawfully and not to misuse or disrupt it.</p>
<h2>No guarantee of results</h2><p>Search engine results are controlled by third parties. {E(BRAND)} does not guarantee specific rankings, traffic or lead volumes. Any services are governed by a separate written agreement.</p>
<h2>Intellectual property</h2><p>All content on this website belongs to {E(BRAND)} unless stated otherwise and may not be copied without permission.</p>
<h2>Limitation of liability</h2><p>To the extent permitted by law, {E(BRAND)} is not liable for losses arising from the use of this website.</p>
<h2>Contact</h2><p>Questions about these terms can be sent to <a data-mail data-email href="mailto:{E(EMAIL)}">{E(EMAIL)}</a>.</p>
</div>''')
    page("terms/", f"Terms of Service | {BRAND}", f"Terms of service for {BRAND}.", body, None, crumbs, [crumb_schema(crumbs)], prio=0.3, freq="yearly", body_attrs='data-city="" data-country=""')


def build_html_sitemap():
    d = 1
    h = lambda t="": rel(d, t)
    pages = [(p, t) for p, t in ALL_PAGES if p and p != "site-map/"]
    body = hero("Site Map", "HTML Site Map", "Every page on this website, grouped by section.", d, ctas=False)
    groups = [("Core pages", [(p, t) for p, t in pages if p.count("/") == 1 and p.split("/")[0] in ("about", "contact", "services", "industries", "locations", "seo-services-near-me", "privacy-policy", "terms")]),
              ("Services", [(p, t) for p, t in pages if p.startswith("services/") and p.count("/") == 2])]
    for k, c in COUNTRIES.items():
        groups.append((c["name"], [(p, t) for p, t in pages if p.startswith(k + "/")]))
    for name, items in groups:
        body += section(E(name), linklist([(t.split(" | ")[0], h(p)) for p, t in items]), alt=False)
    crumbs = [("Home", ""), ("Site Map", "site-map/")]
    page("site-map/", f"HTML Site Map | {BRAND}", f"Complete list of pages on the {BRAND} website.", body, None, crumbs, [crumb_schema(crumbs)], prio=0.4, body_attrs='data-city="" data-country=""')


def build_404():
    d = 0
    abs_pre = SITE + "/"
    body = hero("Page not found", "404: This page could not be found", "The page you are looking for may have moved. Try one of the links below.", 0, ctas=False)
    body += section("Helpful links", chips([("Home", abs_pre), ("SEO Services", abs_pre + "services/"), ("Industries", abs_pre + "industries/"),
                                           ("Locations", abs_pre + "locations/"), ("Contact", abs_pre + "contact/")]))
    out = os.path.join(ROOT, "404.html")
    # build via page() into temp location then rewrite relative URLs to absolute
    page("__404__/", f"Page Not Found | {BRAND}", "Page not found.", body, None, None, None, noindex=True, sitemap=False)
    src = os.path.join(ROOT, "__404__", "index.html")
    txt = open(src, encoding="utf-8").read()
    # 404 can be served from any depth, so convert relative asset/page links to absolute
    txt = txt.replace('data-base="../"', f'data-base="{abs_pre}"')
    txt = re.sub(r'(href|src)="\.\./', lambda m: f'{m.group(1)}="{abs_pre}', txt)
    txt = txt.replace(f'<link rel="canonical" href="{SITE}/__404__/">', "")
    txt = txt.replace(f'<meta property="og:url" content="{SITE}/__404__/">', "")
    open(out, "w", encoding="utf-8").write(txt)
    shutil.rmtree(os.path.join(ROOT, "__404__"))
    ALL_PAGES[:] = [x for x in ALL_PAGES if x[0] != "__404__/"]


# --------------------------------------------------------------- outputs
def write_data_js():
    data = {"brand": BRAND, "countries": {}, "cities": [], "industries": {}}
    for k, c in COUNTRIES.items():
        data["countries"][c["cc"]] = {"slug": k, "name": c["name"], "p": p_country(k)}
        data["industries"][c["cc"]] = [{"s": s, "n": ind_info(k, s)["n"], "p": p_ind(k, s)} for s in c["ind"]]
        for city in CITIES[k]:
            data["cities"].append({"n": city[0], "cc": c["cc"], "p": p_city(k, city[0])})
    with open(os.path.join(ROOT, "assets", "data.js"), "w", encoding="utf-8") as f:
        f.write("window.SITE_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")


def write_sitemap():
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.w3.org/2005/Sitemap/0.9">']
    for path, prio, freq in SITEMAP:
        url = f"{SITE}/{path}" if path else f"{SITE}/"
        lines.append(f"  <url><loc>{E(url)}</loc><lastmod>{TODAY}</lastmod><changefreq>{freq}</changefreq><priority>{prio:.1f}</priority></url>")
    lines.append("</urlset>")
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    open(os.path.join(ROOT, ".nojekyll"), "w").write("")


def clean():
    for name in ["usa", "uk", "india", "services", "industries", "locations", "about", "contact", "seo-services-near-me",
                 "privacy-policy", "terms", "site-map", "__404__"]:
        shutil.rmtree(os.path.join(ROOT, name), ignore_errors=True)
    for f in ["index.html", "404.html", "sitemap.xml", "robots.txt"]:
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            os.remove(p)


def main():
    clean()
    write_data_js()
    build_home()
    for k in COUNTRIES:
        build_country(k)
        for s in COUNTRIES[k]["ind"]:
            build_industry(k, s)
            for sub in ind_info(k, s)["subs"]:
                build_sub(k, s, sub)
        for city in CITIES[k]:
            build_city(k, city)
            for s in COUNTRIES[k]["ind"]:
                build_cityind(k, city, s)
    build_services()
    build_industries_hub()
    build_locations_hub()
    build_near_me()
    build_about()
    build_contact()
    build_legal()
    build_html_sitemap()
    build_404()
    write_sitemap()
    print(f"Built {len(ALL_PAGES)} pages; sitemap has {len(SITEMAP)} URLs. Site URL: {SITE}")


if __name__ == "__main__":
    main()
