# True Gain Media: SEO Lead Generation Website

Static website (no framework) for GitHub Pages. About 1,250 pages for the UK, USA and India: countries, industries, sub-categories, city pages and city + industry pages, plus `sitemap.xml` and `robots.txt`.

## 1. Change everything from ONE file: `assets/config.js`

| Key | What it controls |
|---|---|
| `siteUrl` | Your live URL (used for canonical tags and sitemap.xml) |
| `brandName`, `brandTagline` | Brand name and tagline on every page |
| `logoImage` | Path to a logo file, e.g. `assets/logo.png` (leave empty to show initials) |
| `phoneDisplay`, `phoneDigits` | Header, footer, bottom bar and contact page number (digits only with country code for the tel: link) |
| `whatsappDigits`, `whatsappMessage` | WhatsApp number and pre-filled message |
| `email` | Email shown everywhere |
| `web3formsKey` | Your Web3Forms access key (get it free at web3forms.com) |
| `testimonials` | Widget key (`provider: "elfsight"`), your own embed code (`provider: "embed"`), or manual `items` |

Phone, WhatsApp, email, logo, form key and testimonials update on all pages as soon as you save `config.js`. No rebuild is needed.
If you change `brandName` or `siteUrl`, rebuild once (titles, canonical URLs and sitemap contain them):

```
python3 tools/build.py
```

## 2. Publish on GitHub Pages

1. Create a GitHub repository and upload everything in this folder (keep `.nojekyll`).
2. Settings -> Pages -> Deploy from branch -> `main` / root.
3. Set `siteUrl` in `assets/config.js` to your final address (for example `https://username.github.io/repo-name`, or your custom domain), run `python3 tools/build.py`, and commit again.
4. Submit `https://YOUR-URL/sitemap.xml` in Google Search Console.

## 3. Edit content

* Industries, sub-categories, cities and services: `tools/data.py`
* Page templates and text: `tools/build.py`
* Design: `assets/style.css`

After any change, run `python3 tools/build.py` (Python 3, no packages needed).

## 4. Location-based "near me" feature

`assets/geo.js` finds the visitor's approximate city (IP lookup via ipwho.is). It shows a banner with a link to the matching city page and personalises `/seo-services-near-me/`. Google still indexes the full static city pages. The privacy policy already mentions this lookup.

## 5. Quality notes for SEO

* Replace the placeholder phone number and email in `config.js` before launch.
* City + industry pages share a template. Add genuine local detail (case studies, local examples, real testimonials) to your most important pages, because Google can treat near-identical pages as thin content. Consider launching the highest-value cities first.
* Testimonials stay hidden until you add real ones.
* Review the Privacy Policy and Terms with a lawyer.
