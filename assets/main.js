(function () {
  'use strict';
  var cfg = window.SITE_CONFIG || {};
  var base = document.documentElement.getAttribute('data-base') || './';

  function each(sel, fn) { Array.prototype.forEach.call(document.querySelectorAll(sel), fn); }

  /* ---- central config injection (brand, phone, WhatsApp, email, logo) ---- */
  function applyConfig() {
    each('[data-brand]', function (el) { el.textContent = cfg.brandName || ''; });
    each('[data-tagline]', function (el) { el.textContent = cfg.brandTagline || ''; });
    each('[data-phone]', function (el) { el.textContent = cfg.phoneDisplay || ''; });
    each('[data-tel]', function (el) { el.setAttribute('href', 'tel:+' + String(cfg.phoneDigits || '').replace(/\D/g, '')); });
    each('[data-wa]', function (el) {
      var n = String(cfg.whatsappDigits || '').replace(/\D/g, '');
      var m = encodeURIComponent(cfg.whatsappMessage || '');
      el.setAttribute('href', 'https://wa.me/' + n + (m ? '?text=' + m : ''));
      el.setAttribute('target', '_blank');
      el.setAttribute('rel', 'noopener');
    });
    each('[data-email]', function (el) { el.textContent = cfg.email || ''; });
    each('[data-mail]', function (el) { el.setAttribute('href', 'mailto:' + (cfg.email || '')); });
    each('[data-year]', function (el) { el.textContent = new Date().getFullYear(); });
    each('[data-logo-mark]', function (el) {
      if (cfg.logoImage) {
        var img = document.createElement('img');
        img.src = base + String(cfg.logoImage).replace(/^\//, '');
        img.alt = cfg.brandName || '';
        el.textContent = '';
        el.appendChild(img);
        el.classList.add('has-img');
      } else {
        var words = String(cfg.brandName || '').split(/\s+/).filter(Boolean).slice(0, 2);
        el.textContent = words.map(function (w) { return w.charAt(0); }).join('').toUpperCase();
      }
    });
  }

  /* ---- header: scroll shadow + mobile menu ---- */
  function initHeader() {
    var hdr = document.querySelector('.site-header');
    var nav = document.getElementById('nav');
    var burger = document.getElementById('burger');
    function onScroll() { if (hdr) hdr.classList.toggle('scrolled', window.scrollY > 4); }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    if (burger && nav) {
      burger.addEventListener('click', function () {
        var open = nav.classList.toggle('open');
        burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }
    each('.has-sub > a', function (a) {
      a.addEventListener('click', function (e) {
        if (window.innerWidth <= 1050) {
          var li = a.parentNode;
          if (!li.classList.contains('open')) { e.preventDefault(); li.classList.add('open'); }
        }
      });
    });
  }

  /* ---- lead forms (Web3Forms) ---- */
  function initForms() {
    each('form[data-w3]', function (form) {
      var status = form.querySelector('.form-status');
      function say(msg, cls) { if (status) { status.textContent = msg; status.className = 'form-status ' + (cls || ''); } }
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var key = cfg.web3formsKey || '';
        if (!key || key.indexOf('YOUR_') === 0) { say('The form is not configured yet. Please call or WhatsApp us.', 'err'); return; }
        var fd = new FormData(form);
        var geo = window.TGM_GEO;
        var payload = {
          access_key: key,
          subject: 'New SEO lead - ' + (form.getAttribute('data-context') || 'Website'),
          from_name: cfg.brandName || 'Website',
          page_url: location.href,
          page_context: form.getAttribute('data-context') || '',
          detected_location: geo ? [geo.city, geo.country].filter(Boolean).join(', ') : '',
          botcheck: fd.get('botcheck') ? true : false
        };
        fd.forEach(function (v, k) { if (k !== 'botcheck') payload[k] = v; });
        var btn = form.querySelector('button[type=submit]');
        if (btn) { btn.disabled = true; }
        say('Sending...', '');
        fetch('https://api.web3forms.com/submit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(payload)
        }).then(function (r) { return r.json(); }).then(function (j) {
          if (j && j.success) { say('Thank you! We have received your request and will contact you shortly.', 'ok'); form.reset(); }
          else { say('Sorry, something went wrong. Please call or WhatsApp us.', 'err'); }
        }).catch(function () { say('Network error. Please call or WhatsApp us.', 'err'); })
          .then(function () { if (btn) btn.disabled = false; });
      });
    });
  }

  /* ---- testimonials (widget key, embed code or manual items) ---- */
  function loadScript(src) { var s = document.createElement('script'); s.src = src; s.async = true; document.body.appendChild(s); }
  function initTestimonials() {
    var sec = document.getElementById('testimonials-section');
    var box = document.getElementById('testimonials');
    if (!sec || !box) return;
    var t = cfg.testimonials || {};
    var shown = false;
    if (t.provider === 'elfsight' && t.widgetKey) {
      box.innerHTML = '<div class="elfsight-app-' + String(t.widgetKey).replace(/[^a-zA-Z0-9-]/g, '') + '" data-elfsight-app-lazy></div>';
      loadScript('https://elfsightcdn.com/platform.js');
      shown = true;
    } else if (t.provider === 'embed' && t.embedHtml) {
      box.innerHTML = t.embedHtml;
      if (t.embedScriptSrc) loadScript(t.embedScriptSrc);
      shown = true;
    } else if (t.items && t.items.length) {
      var wrap = document.createElement('div');
      wrap.className = 'testi';
      t.items.forEach(function (it) {
        var c = document.createElement('div'); c.className = 'card';
        var q = document.createElement('blockquote'); q.textContent = '“' + (it.text || '') + '”';
        var w = document.createElement('div'); w.className = 'who';
        w.textContent = [it.name, it.role].filter(Boolean).join(', ');
        c.appendChild(q); c.appendChild(w); wrap.appendChild(c);
      });
      box.appendChild(wrap);
      shown = true;
    }
    if (shown) sec.hidden = false;
  }

  applyConfig();
  initHeader();
  initForms();
  initTestimonials();
})();
