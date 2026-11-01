/* Location-aware personalisation.
   Uses an approximate, IP-based lookup (ipwho.is) to show visitors the SEO page for their own city.
   Search engines still see the static, fully written city pages. */
(function () {
  'use strict';
  var D = window.SITE_DATA;
  if (!D) return;
  var base = document.documentElement.getAttribute('data-base') || './';
  var KEY = 'tgm_geo_v1';
  var ALIAS = {
    'bangalore': 'bengaluru', 'bombay': 'mumbai', 'new delhi': 'delhi', 'calcutta': 'kolkata',
    'vizag': 'visakhapatnam', 'madras': 'chennai', 'poona': 'pune', 'baroda': 'vadodara',
    'newcastle upon tyne': 'newcastle', 'kingston upon hull': 'hull', 'new york city': 'new york',
    'noida': 'noida', 'greater noida': 'noida', 'navi mumbai': 'mumbai'
  };
  function norm(s) { return String(s || '').toLowerCase().trim(); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function findCity(city, cc) {
    var n = norm(city); n = ALIAS[n] || n;
    for (var i = 0; i < D.cities.length; i++) {
      if (D.cities[i].cc === cc && norm(D.cities[i].n) === n) return D.cities[i];
    }
    return null;
  }
  function detect(cb) {
    try { var c = JSON.parse(sessionStorage.getItem(KEY)); if (c) { cb(c); return; } } catch (e) {}
    var done = false;
    var timer = setTimeout(function () { if (!done) { done = true; cb(null); } }, 4000);
    fetch('https://ipwho.is/').then(function (r) { return r.json(); }).then(function (j) {
      if (done) return; done = true; clearTimeout(timer);
      if (!j || j.success === false) { cb(null); return; }
      var g = { city: j.city, country: j.country, cc: j.country_code };
      try { sessionStorage.setItem(KEY, JSON.stringify(g)); } catch (e) {}
      cb(g);
    }).catch(function () { if (!done) { done = true; clearTimeout(timer); cb(null); } });
  }

  detect(function (g) {
    if (!g || !g.city) return;
    var match = findCity(g.city, g.cc);
    var country = D.countries[g.cc] || null;
    window.TGM_GEO = { city: g.city, country: g.country, cc: g.cc, match: match };

    Array.prototype.forEach.call(document.querySelectorAll('[data-geo-city]'), function (el) { el.textContent = g.city; });

    /* banner */
    var banner = document.getElementById('geo-banner');
    var pageCity = document.body.getAttribute('data-city') || '';
    var pageCountry = document.body.getAttribute('data-country') || '';
    var dismissed = false;
    try { dismissed = sessionStorage.getItem('tgm_geo_banner') === '1'; } catch (e) {}
    if (banner && !dismissed && (match || country)) {
      var show = false, text = '', link = '', label = '';
      if (match && match.n !== pageCity) {
        show = true; text = 'Looking for SEO services in ' + esc(match.n) + '?';
        link = base + match.p; label = 'See SEO services in ' + esc(match.n) + ' →';
      } else if (!match && country && country.slug !== pageCountry) {
        show = true; text = 'Helping businesses across ' + esc(country.name) + '.';
        link = base + country.p; label = 'View SEO services in ' + esc(country.name) + ' →';
      }
      if (show) {
        document.getElementById('geo-text').innerHTML = text;
        var a = document.getElementById('geo-link'); a.setAttribute('href', link); a.innerHTML = label;
        banner.hidden = false;
        var x = banner.querySelector('.geo-close');
        if (x) x.addEventListener('click', function () { banner.hidden = true; try { sessionStorage.setItem('tgm_geo_banner', '1'); } catch (e) {} });
      }
    }

    /* "SEO services near me" page */
    var h1 = document.getElementById('nm-h1');
    var box = document.getElementById('nm-links');
    if (h1 && box) {
      var brand = (window.SITE_CONFIG && window.SITE_CONFIG.brandName) || '';
      var lede = document.getElementById('nm-lede');
      var html = '';
      if (match) {
        h1.textContent = 'SEO Services in ' + match.n + ', ' + (country ? country.name : g.country);
        document.title = 'SEO Services in ' + match.n + ' | ' + brand;
        if (lede) lede.textContent = 'We detected that you are near ' + match.n + '. Here are our SEO services for businesses in your area.';
        html += '<li><a href="' + base + match.p + '"><strong>All SEO services in ' + esc(match.n) + '</strong></a></li>';
        (D.industries[g.cc] || []).forEach(function (s) {
          html += '<li><a href="' + base + match.p + 'seo-services-for-' + s.s + '/">SEO services for ' + esc(s.n) + ' in ' + esc(match.n) + '</a></li>';
        });
      } else if (country) {
        h1.textContent = 'SEO Services Near You in ' + country.name;
        document.title = 'SEO Services Near You in ' + country.name + ' | ' + brand;
        if (lede) lede.textContent = 'We could not match your exact city, so here are our top locations across ' + country.name + '.';
        html += '<li><a href="' + base + country.p + '"><strong>SEO services in ' + esc(country.name) + '</strong></a></li>';
        D.cities.filter(function (c) { return c.cc === g.cc; }).forEach(function (c) {
          html += '<li><a href="' + base + c.p + '">SEO services in ' + esc(c.n) + '</a></li>';
        });
      }
      if (html) { box.innerHTML = html; var wrap = document.getElementById('nm-result'); if (wrap) wrap.hidden = false; }
    }
  });
})();
