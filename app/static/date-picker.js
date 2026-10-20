/* Modal calendar date picker (Material-style) for the apply page.
   Usage: DatePicker.attach(inputEl, { min: 'YYYY-MM-DD', max: 'YYYY-MM-DD' })
   The input keeps its value as YYYY-MM-DD and gets 'input' and 'change' events when OK is pressed. */
(function () {
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  var WEEK = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  function svg(d, s) { return '<svg viewBox="0 0 24 24" width="' + s + '" height="' + s + '" aria-hidden="true"><path fill="currentColor" d="' + d + '"/></svg>'; }
  var ICON_PEN = svg('M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z', 24);
  var ICON_CAL = svg('M19 4h-1V2h-2v2H8V2H6v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 16H5V10h14v10zm0-12H5V6h14v2z', 24);
  var ICON_LEFT = svg('M15.41 7.41 14 6l-6 6 6 6 1.41-1.41L10.83 12z', 24);
  var ICON_RIGHT = svg('M10 6 8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z', 24);
  var ICON_DOWN = svg('M7 10l5 5 5-5z', 20);
  var ICON_UP = svg('M7 14l5-5 5 5z', 20);

  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function toIso(y, m, d) { return y + '-' + pad(m + 1) + '-' + pad(d); }
  function parseIso(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || '');
    if (!m) return null;
    var y = +m[1], mo = +m[2] - 1, d = +m[3];
    var dt = new Date(y, mo, d);
    if (dt.getFullYear() !== y || dt.getMonth() !== mo || dt.getDate() !== d) return null;
    return { y: y, m: mo, d: d };
  }
  function fmtLong(p) { return DAYS[new Date(p.y, p.m, p.d).getDay()] + ', ' + MONTHS[p.m].slice(0, 3) + ' ' + p.d; }

  function attach(input, opts) {
    opts = opts || {};
    var now = new Date();
    var todayIso = toIso(now.getFullYear(), now.getMonth(), now.getDate());
    var min = opts.min || '1900-01-01';
    var max = opts.max || todayIso;
    var minP = parseIso(min), maxP = parseIso(max);
    var overlay = null, st = null, lastFocus = null;

    input.readOnly = true;
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('aria-haspopup', 'dialog');
    input.addEventListener('click', open);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); }
    });

    function inRange(iso) { return iso >= min && iso <= max; }

    function open() {
      if (overlay) return;
      var cur = parseIso(input.value);
      var base = cur || maxP;
      st = { sel: cur ? input.value : '', y: base.y, m: base.m, mode: cur ? 'day' : 'year', text: false };
      lastFocus = document.activeElement;
      overlay = document.createElement('div');
      overlay.className = 'dp-overlay';
      overlay.addEventListener('mousedown', function (e) { if (e.target === overlay) close(); });
      overlay.addEventListener('click', onClick);
      document.body.appendChild(overlay);
      document.addEventListener('keydown', onKey);
      render();
    }
    function close() {
      if (!overlay) return;
      document.removeEventListener('keydown', onKey);
      overlay.remove();
      overlay = null;
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    function onKey(e) {
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      else if (e.key === 'Enter' && st.text && e.target.classList && e.target.classList.contains('dp-textinput')) { e.preventDefault(); commit(); }
    }
    function commit() {
      var val = st.sel;
      if (st.text) {
        val = overlay.querySelector('.dp-textinput').value.trim();
        if (!parseIso(val) || !inRange(val)) {
          var err = overlay.querySelector('.dp-err');
          err.textContent = 'Enter a valid date as YYYY-MM-DD, between ' + min + ' and ' + max + '.';
          err.hidden = false;
          return;
        }
      }
      if (!val) return;
      input.value = val;
      ['input', 'change'].forEach(function (n) { input.dispatchEvent(new Event(n, { bubbles: true })); });
      close();
    }
    function onClick(e) {
      var el = e.target.closest('[data-act]');
      if (!el || el.disabled) return;
      var act = el.getAttribute('data-act'), v = el.getAttribute('data-v');
      if (act === 'cancel') return close();
      if (act === 'ok') return commit();
      if (act === 'toggle-text') {
        if (st.text) {
          var t = overlay.querySelector('.dp-textinput').value.trim();
          var p = parseIso(t);
          if (p && inRange(t)) { st.sel = t; st.y = p.y; st.m = p.m; st.mode = 'day'; }
        }
        st.text = !st.text;
        return render();
      }
      if (act === 'years') { st.mode = 'year'; return render(); }
      if (act === 'days') { st.mode = 'day'; return render(); }
      if (act === 'year') {
        st.y = +v;
        if (st.y === maxP.y && st.m > maxP.m) st.m = maxP.m;
        if (st.y === minP.y && st.m < minP.m) st.m = minP.m;
        st.mode = 'month';
        return render();
      }
      if (act === 'month') { st.m = +v; st.mode = 'day'; return render(); }
      if (act === 'day') { st.sel = v; return render(); }
      if (act === 'prev' || act === 'next') {
        var idx = st.y * 12 + st.m + (act === 'next' ? 1 : -1);
        st.y = Math.floor(idx / 12);
        st.m = idx % 12;
        return render();
      }
    }

    function nav() {
      if (st.mode === 'day') {
        var idx = st.y * 12 + st.m;
        return '<div class="dp-nav"><button type="button" class="dp-monthbtn" data-act="years" aria-label="Choose year and month">' + MONTHS[st.m] + ' ' + st.y + ICON_DOWN + '</button><span class="dp-arrows">'
          + '<button type="button" class="dp-icon" data-act="prev" aria-label="Previous month"' + (idx <= minP.y * 12 + minP.m ? ' disabled' : '') + '>' + ICON_LEFT + '</button>'
          + '<button type="button" class="dp-icon" data-act="next" aria-label="Next month"' + (idx >= maxP.y * 12 + maxP.m ? ' disabled' : '') + '>' + ICON_RIGHT + '</button></span></div>';
      }
      return '<div class="dp-nav"><button type="button" class="dp-monthbtn" data-act="days" aria-label="Back to calendar">' + (st.mode === 'year' ? 'Select year' : 'Select month, ' + st.y) + ICON_UP + '</button></div>';
    }
    function days() {
      var first = new Date(st.y, st.m, 1).getDay();
      var dim = new Date(st.y, st.m + 1, 0).getDate();
      var h = '<div class="dp-week">';
      WEEK.forEach(function (w) { h += '<span>' + w + '</span>'; });
      h += '</div><div class="dp-grid">';
      for (var i = 0; i < first; i++) h += '<span></span>';
      for (var d = 1; d <= dim; d++) {
        var iso = toIso(st.y, st.m, d);
        h += '<button type="button" class="dp-day' + (iso === st.sel ? ' dp-sel' : '') + (iso === todayIso ? ' dp-today' : '') + '" data-act="day" data-v="' + iso + '"'
          + (inRange(iso) ? '' : ' disabled') + ' aria-label="' + MONTHS[st.m] + ' ' + d + ', ' + st.y + '">' + d + '</button>';
      }
      return h + '</div>';
    }
    function months() {
      var h = '<div class="dp-cells">';
      MONTHS.forEach(function (name, i) {
        var off = (st.y === maxP.y && i > maxP.m) || (st.y === minP.y && i < minP.m);
        h += '<button type="button" class="dp-cell' + (i === st.m ? ' dp-sel' : '') + '" data-act="month" data-v="' + i + '"' + (off ? ' disabled' : '') + '>' + name.slice(0, 3) + '</button>';
      });
      return h + '</div>';
    }
    function years() {
      var h = '<div class="dp-years"><div class="dp-cells">';
      for (var y = maxP.y; y >= minP.y; y--) {
        h += '<button type="button" class="dp-cell' + (y === st.y ? ' dp-sel' : '') + '" data-act="year" data-v="' + y + '">' + y + '</button>';
      }
      return h + '</div></div>';
    }
    function render() {
      var selP = parseIso(st.sel);
      var h = '<div class="dp-dialog" role="dialog" aria-modal="true" aria-label="Select date" tabindex="-1">';
      h += '<div class="dp-top"><div class="dp-eyebrow">Select date</div><div class="dp-titlerow">';
      h += '<div class="dp-title' + (selP ? '' : ' dp-muted') + '">' + (selP ? fmtLong(selP) : 'Pick a date') + '</div>';
      h += '<button type="button" class="dp-icon" data-act="toggle-text" aria-label="' + (st.text ? 'Switch to calendar' : 'Switch to typing') + '">' + (st.text ? ICON_CAL : ICON_PEN) + '</button>';
      h += '</div></div><div class="dp-divider"></div><div class="dp-body">';
      if (st.text) {
        h += '<label class="dp-field"><span>Date (YYYY-MM-DD)</span><input type="text" class="dp-textinput" inputmode="numeric" maxlength="10" placeholder="YYYY-MM-DD" value="' + st.sel + '"></label><p class="dp-err" hidden></p>';
      } else {
        h += nav() + (st.mode === 'day' ? days() : (st.mode === 'month' ? months() : years()));
      }
      h += '</div><div class="dp-actions"><button type="button" class="dp-btn" data-act="cancel">Cancel</button>';
      h += '<button type="button" class="dp-btn" data-act="ok"' + (!st.text && !st.sel ? ' disabled' : '') + '>OK</button></div></div>';
      overlay.innerHTML = h;
      var list = overlay.querySelector('.dp-years');
      var cur = overlay.querySelector('.dp-years .dp-sel');
      if (list && cur) list.scrollTop = cur.offsetTop - (list.clientHeight - cur.offsetHeight) / 2;
      var f = overlay.querySelector('.dp-textinput') || overlay.querySelector('.dp-sel') || overlay.querySelector('.dp-dialog');
      f.focus({ preventScroll: true });
    }
  }
  window.DatePicker = { attach: attach };
})();
