// _entry.js -- P4 slice 7 screens for the WorkEntryAgreement path.
//
// Every value rendered here comes from the server (/api/work-entry/*); this file keeps no
// relationship of its own. Credentials are the existing doors only (provision api_key or KA§§A
// JWT; the thread magic link for email-only posters) -- no alternate registration door.
//
//   CIVITAE_ENTRY.openEnter({ref, title})         Find Work: INTENT > TERMS > PREFLIGHT > CONFIRM > OUTCOME
//   CIVITAE_ENTRY.mountPosterPanel(host, opts)    poster side: accept / reject / retire (+ withdraw, activate)
//   CIVITAE_ENTRY.mountMission(host)              Mission Control: Agreement node, Acceptance record, PROGRESS
//   CIVITAE_ENTRY.mountMine(host)                 Mission Control: my entries as nodes
//   CIVITAE_ENTRY.mountDeploy(host, {mode})       ARM DEPLOY preflight (mode "arm") / second confirmation (mode "command")
window.CIVITAE_ENTRY = (function () {
  'use strict';
  var E = {};

  // ── tiny DOM helper (text only; no innerHTML with server data) ────────────
  function h(tag, attrs, kids) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'text') n.textContent = v;
      else if (k === 'class') n.className = v;
      else if (k.slice(0, 2) === 'on') n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? '' : v);
    });
    (kids || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function $(x) { return typeof x === 'string' ? document.querySelector(x) : x; }
  function pill(cls, text) { return h('span', { 'class': 'cve-pill ' + cls, text: text }); }
  function fmt(ts) { return ts ? String(ts).replace('T', ' ').replace(/\.\d+/, '').replace('+00:00', 'Z') : '—'; }
  function uuid() {
    try { return crypto.randomUUID(); } catch (e) { return 'k-' + Date.now() + '-' + Math.random().toString(16).slice(2); }
  }
  function qp(name) { try { return new URLSearchParams(location.search).get(name) || ''; } catch (e) { return ''; } }
  function store(k) { try { return localStorage.getItem(k) || sessionStorage.getItem(k) || ''; } catch (e) { return ''; } }

  // ── credentials: existing doors only ──────────────────────────────────────
  function credHeaders() {
    var out = [], key = '', jwt = store('kassa_jwt') || store('kassa_token');
    try {
      var ca = JSON.parse(localStorage.getItem('civitas_auth') || 'null');
      if (ca && ca.agentId && ca.key) key = ca.key;
    } catch (e) {}
    if (!key) key = store('au_api_key');
    if (key) out.push({ 'Authorization': 'Bearer ' + key });
    if (jwt) out.push({ 'Authorization': 'Bearer ' + jwt });
    return out;
  }
  function req(method, path, body, o) {
    o = o || {};
    var cands = o.magic ? [{ 'X-Magic-Token': o.magic, 'X-Thread-Id': o.threadId || '' }] : credHeaders();
    if (!cands.length) cands = [{}];
    function go(i) {
      var hd = { 'Content-Type': 'application/json' };
      Object.keys(cands[i]).forEach(function (k) { hd[k] = cands[i][k]; });
      return fetch(path, { method: method, headers: hd, body: body ? JSON.stringify(body) : undefined })
        .then(function (r) {
          return r.json().catch(function () { return {}; }).then(function (j) {
            return { ok: r.ok, status: r.status, json: j };
          });
        })
        .then(function (res) { return (res.status === 401 && i + 1 < cands.length) ? go(i + 1) : res; });
    }
    return go(0);
  }
  function errText(res) {
    var j = res.json || {};
    var d = j.error || j.detail || ('HTTP ' + res.status);
    if (typeof d !== 'string') d = JSON.stringify(d);
    return d + (j.code ? ' [' + j.code + ']' : '');
  }

  // ── styles (scoped, injected once) ────────────────────────────────────────
  function css() {
    if (document.getElementById('cve-css')) return;
    var s = document.createElement('style');
    s.id = 'cve-css';
    s.textContent = [
      '.cve-bg{position:fixed;inset:0;background:rgba(6,8,10,.72);z-index:9000;display:flex;align-items:center;justify-content:center;padding:16px}',
      '.cve-modal{width:min(560px,100%);max-height:92vh;overflow:auto;background:#17140E;border:1px solid #3C3424;border-radius:12px;padding:16px;color:#D7D8DA;font:13px/1.5 "DM Sans",Inter,system-ui,sans-serif}',
      '.cve-modal h3{font-size:15px;font-weight:600;margin:0}',
      '.cve-sub{font:10px "DM Mono",monospace;letter-spacing:.12em;color:#A88B52;text-transform:uppercase}',
      '.cve-steps{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin:12px 0}',
      '.cve-steps span{border:1px solid #262B31;background:#14171B;border-radius:6px;padding:5px 0;text-align:center;font:9px "DM Mono",monospace;letter-spacing:.08em;color:#5E656C}',
      '.cve-steps .done{border-color:#2F4434;background:#0F1812;color:#7AA188}',
      '.cve-steps .cur{border-color:#C7A35A;background:rgba(199,163,90,.12);color:#E3D7BE}',
      '.cve-pane{border:1px solid #2A2F35;background:#13171C;border-radius:10px;padding:12px;margin-top:8px}',
      '.cve-pane p{margin:6px 0 0;font-size:12px;color:#9AA0A6}',
      '.cve-kv{display:grid;grid-template-columns:104px 1fr;gap:6px 10px;margin:8px 0 0;font-size:12px}',
      '.cve-kv dt{font:9px "DM Mono",monospace;letter-spacing:.12em;color:#8D7D62;padding-top:3px;text-transform:uppercase}',
      '.cve-kv dd{margin:0;color:#D7D8DA;overflow-wrap:anywhere}',
      '.cve-opt{display:flex;gap:8px;align-items:flex-start;width:100%;text-align:left;border:1px solid #C7A35A;background:#1A160E;border-radius:8px;padding:8px 10px;color:#E3D7BE;margin-top:8px;font:inherit}',
      '.cve-opt small{display:block;color:#8A7C62;font-size:11px}',
      '.cve-in,.cve-sel{width:100%;margin-top:6px;background:#0A0D10;border:1px solid #2D3238;border-radius:8px;color:#D7D8DA;padding:7px 9px;font:inherit}',
      'textarea.cve-in{min-height:56px;resize:vertical}',
      '.cve-pill{display:inline-block;border:1px solid #3A3F45;border-radius:10px;padding:0 8px;font:9px "DM Mono",monospace;letter-spacing:.08em;color:#9AA0A6;vertical-align:middle}',
      '.cve-pill.live{border-color:#2F5A40;color:#7AC79A;background:#0F1812}',
      '.cve-pill.pend{border-color:#6A5A3A;color:#D6C3A0;background:#20190D}',
      '.cve-pill.block{border-color:#6A3A3A;color:#E0A0A0;background:#1C0F0F}',
      '.cve-pill.sel{border-color:#C7A35A;color:#E3D7BE}',
      '.cve-nav{display:flex;gap:8px;justify-content:flex-end;margin-top:12px}',
      '.cve-btn{border:1px solid #3E3524;background:#1B160D;color:#D3B266;border-radius:8px;padding:7px 14px;font:11px "DM Mono",monospace;letter-spacing:.06em;cursor:pointer}',
      '.cve-btn.primary{background:#C7A35A;border-color:#C7A35A;color:#0A0B0D;font-weight:600}',
      '.cve-btn.danger{border-color:#6A3A3A;color:#E0A0A0}',
      '.cve-btn[disabled]{opacity:.4;cursor:not-allowed}',
      '.cve-note{margin-top:8px;border:1px solid #2C3A47;background:#0D161E;border-radius:8px;padding:8px 10px;font-size:11px;color:#8FA9BF}',
      '.cve-warn{margin-top:8px;border:1px solid #6A5A3A;background:#20190D;border-radius:8px;padding:8px 10px;font-size:12px;color:#EBCBA4}',
      '.cve-err{margin-top:8px;border:1px solid #6A3A3A;background:#1C0F0F;border-radius:8px;padding:8px 10px;font-size:12px;color:#E0A0A0}',
      '.cve-ok{margin-top:8px;border:1px solid #2F5A40;background:#0F1812;border-radius:8px;padding:8px 10px;font-size:12px;color:#CFE1D3}',
      '.cve-list{list-style:none;margin:8px 0 0;padding:0;counter-reset:p}',
      '.cve-list li{display:grid;grid-template-columns:20px 1fr auto;gap:8px;padding:6px 0;border-bottom:1px solid #22272C;font-size:12px}',
      '.cve-list li:before{counter-increment:p;content:counter(p);font:10px "DM Mono",monospace;color:#5E656C;border:1px solid #2B3036;border-radius:4px;text-align:center;line-height:16px}',
      '.cve-list small{display:block;color:#6E747A;font-size:11px}',
      '.cve-rcpt{margin-top:10px;border:1px solid #3A3427;background:#14110C;border-radius:10px;padding:10px}',
      '.cve-panel{border:1px solid #3C3424;background:#17140E;border-radius:12px;padding:14px;margin:16px auto;max-width:960px;color:#D7D8DA;font:13px/1.5 "DM Sans",Inter,system-ui,sans-serif}',
      '.cve-panel h4{margin:0;font-size:14px;font-weight:600}',
      '.cve-tabs{display:flex;gap:6px;margin:10px 0 4px}',
      '.cve-tabs button{border:1px solid #2B3036;background:#14171B;color:#8E949A;border-radius:6px;padding:4px 12px;font:10px "DM Mono",monospace;letter-spacing:.1em;cursor:pointer}',
      '.cve-tabs button.on{border-color:#C7A35A;color:#E3D7BE;background:rgba(199,163,90,.12)}',
      '.cve-node{display:inline-flex;flex-direction:column;gap:4px;border:1px dashed #6A5A3A;background:#16130D;border-radius:10px;padding:8px 12px;margin:4px 8px 4px 0;cursor:pointer;color:#D7D8DA;font:inherit;text-align:left}',
      '.cve-node.on{border-style:solid;border-color:#C7A35A}',
      '.cve-node b{font:10px "DM Mono",monospace;letter-spacing:.12em;color:#A88B52}',
      '.cve-chain{display:flex;gap:6px;align-items:center;flex-wrap:wrap;font:11px "DM Mono",monospace}',
      '.cve-chain span{border:1px solid #2B3036;border-radius:6px;padding:1px 8px;color:#5E656C}',
      '.cve-chain span.lit{border-color:#2F5A40;color:#7AC79A;background:#0F1812}',
      '.cve-row{border:1px solid #2A2F35;border-radius:10px;padding:10px;margin-top:8px;background:#13171C}',
      '.cve-row .acts{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:8px}',
      '.cve-row .acts input{flex:1;min-width:140px;margin:0}',
      '.cve-tl{list-style:none;margin:8px 0 0;padding:0;font-size:12px}',
      '.cve-tl li{border-left:2px solid #3A3427;padding:2px 0 8px 10px;margin-left:4px}',
      '.cve-tl small{display:block;color:#6E747A;font:10px "DM Mono",monospace;overflow-wrap:anywhere}',
      '.cve-float{position:fixed;right:16px;bottom:44px;width:min(420px,calc(100vw - 32px));max-height:72vh;overflow:auto;z-index:60;margin:0}'
    ].join('\n');
    document.head.appendChild(s);
  }

  function kv(rows) {
    var dl = h('dl', { 'class': 'cve-kv' });
    rows.forEach(function (r) {
      dl.appendChild(h('dt', { text: r[0] }));
      var dd = h('dd', {});
      if (r[1] instanceof Node) dd.appendChild(r[1]); else dd.textContent = r[1] === null || r[1] === undefined || r[1] === '' ? '—' : String(r[1]);
      if (r[2]) dd.setAttribute('data-k', r[2]);
      dl.appendChild(dd);
    });
    return dl;
  }
  // Entrant-facing wait facts from the API object (waiting_on, poster_response); display only.
  function waitLine(v) {
    if (!v || !v.waiting_on) return null;
    var pr = v.poster_response || {};
    return h('div', { 'class': 'cve-sub', 'data-testid': 'waiting-on-poster',
      text: 'Waiting on the poster' + (pr.label ? ' · ' + pr.label : '') });
  }
  var MODE_LABEL = { open: 'Open', standard: 'Standard', constitutional: 'Constitutional' };
  function statePill(st) {
    var cls = { accepted: 'live', active: 'live', completed: 'live', pending: 'pend', dormant: 'pend' }[st] || 'block';
    return pill(cls, st);
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 1. Find Work: Enter flow (INTENT > TERMS > PREFLIGHT > CONFIRM > OUTCOME)
  // ═════════════════════════════════════════════════════════════════════════
  var STEPS = ['INTENT', 'TERMS', 'PREFLIGHT', 'CONFIRM', 'OUTCOME'];

  E.openEnter = function (o) {
    css();
    var S = { step: 1, opp: null, pr: null, note: '', ev: 'solution', out: null, err: null,
              loading: true, busy: false, key: uuid(), ref: o.ref, title: o.title || '' };
    var bg = h('div', { 'class': 'cve-bg', id: 'enter-modal', role: 'dialog', 'aria-modal': 'true' });
    var box = h('div', { 'class': 'cve-modal' });
    bg.appendChild(box);
    document.body.appendChild(bg);
    function close() { if (bg.parentNode) bg.parentNode.removeChild(bg); }
    bg.addEventListener('click', function (e) { if (e.target === bg) close(); });

    function blocked() {
      if (!S.opp) return 'Opportunity unavailable';
      if (!S.pr) return 'Sign in with your registered agent to enter (one door, /entry)';
      if (S.opp.caller && S.opp.caller.own_opportunity) return 'You cannot enter your own opportunity';
      if (S.opp.mine) return 'You already have a live entry: ' + S.opp.mine.agreement_id + ' (' + S.opp.mine.state + ')';
      return '';
    }

    function intent() {
      var o2 = S.opp, pane = h('div', { 'class': 'cve-pane' });
      pane.appendChild(h('h3', { text: 'How do you want in?' }));
      pane.appendChild(h('button', { 'class': 'cve-opt', type: 'button', 'data-testid': 'intent-option' }, [
        h('span', {}, [(o2.kind === 'slot' ? 'Fill this slot' : o2.kind === 'mission' ? 'Join this mission' : 'Enter this opportunity'),
          h('small', { text: 'Two explicit clicks: your entry is accepted, then you activate it. Stake stays separate.' })])]));
      pane.appendChild(h('div', { 'class': 'cve-sub', style: 'margin-top:12px',
                                  text: 'Note to the resolver · optional, 280 max' }));
      var ta = h('textarea', { 'class': 'cve-in', id: 'cve-note', maxlength: '280',
                               placeholder: 'What you can deliver, and when you can start' });
      ta.value = S.note;
      ta.addEventListener('input', function () { S.note = ta.value; });
      pane.appendChild(ta);
      pane.appendChild(h('div', { 'class': 'cve-note',
        text: 'Opening a thread or messaging does not count as entry. Only a confirmed Agreement does. ' +
              'A stake is separate: optional, non-exclusive, and it never becomes an entry.' }));
      var why = blocked();
      if (why) pane.appendChild(h('div', { 'class': 'cve-warn', 'data-testid': 'enter-blocked' }, [why + ' ',
        (!S.pr ? h('a', { href: '/entry', style: 'color:#D3B266', text: 'Sign in →' }) : null)]));
      var wl = S.opp && waitLine(S.opp.mine);
      if (wl) pane.appendChild(wl);
      return pane;
    }
    function terms() {
      var op = S.opp, pane = h('div', { 'class': 'cve-pane' });
      pane.appendChild(h('h3', { text: 'Terms you are entering under' }));
      var sel = h('select', { 'class': 'cve-sel', id: 'cve-ev' });
      op.delivery_evidence_classes.forEach(function (c) {
        var oo = h('option', { value: c.id, text: c.label });
        if (c.id === S.ev) oo.selected = true;
        sel.appendChild(oo);
      });
      sel.addEventListener('change', function () { S.ev = sel.value; });
      var obj = op.objects || {};
      pane.appendChild(kv([
        ['Opportunity', op.title || op.ref, 'opp-title'],
        ['Reference', op.ref, 'opp-ref'],
        ['Governance', MODE_LABEL[op.entry_mode] || op.entry_mode, 'mode'],
        ['Object', [obj.post_id && ('post ' + obj.post_id), obj.mission_id && ('mission ' + obj.mission_id),
                    obj.slot_id && ('slot ' + obj.slot_id)].filter(Boolean).join(' · ') || '—'],
        ['Evidence class', sel],
        ['Acceptance', op.acceptance.text, 'acceptance'],
        ['Withdrawal', op.withdrawal],
        ['Payout', 'No CR moves on entry. Payout happens only through an Acceptance record.']
      ]));
      pane.appendChild(h('div', { 'class': 'cve-note',
        text: 'WHAT IS DISCLOSED: to the owner / resolver: your principal, registration status and your note. ' +
              'Not disclosed: wallet balance, other entries, thread contents.' }));
      return pane;
    }
    function preflight() {
      var op = S.opp, pane = h('div', { 'class': 'cve-pane' });
      pane.appendChild(h('h3', { text: 'Commitment preview' }));
      pane.appendChild(h('p', { text: 'Steps 1–3 run now; 4–7 run only after you confirm.' }));
      var rows = [
        ['Resolve principal', S.pr.agent_id + ' · ' + S.pr.credential_type, 'OK', 'live'],
        ['Check governance / authority', (MODE_LABEL[op.entry_mode] || op.entry_mode) + ' · ' + op.acceptance.kind +
          ' · resolver: ' + op.acceptance.resolver, 'OK', 'live'],
        ['Disclose economics / evidence', 'No CR moves on entry. Writes an audit entry and a Seed.', 'SHOWN', 'live'],
        ['Confirm', 'Your explicit confirmation', 'NEXT', 'sel'],
        ['Authoritative commit', 'WorkEntryAgreement written as ' + (op.entry_mode === 'open' ? 'accepted' : 'pending'), 'WAIT', ''],
        ['Durable receipt', '', 'WAIT', ''],
        ['Provenance Seed', 'A failed Seed is loud: rolled back or an evidence gap is recorded', 'WAIT', '']];
      var ol = h('ol', { 'class': 'cve-list', 'data-testid': 'preflight-list' });
      rows.forEach(function (r) {
        ol.appendChild(h('li', {}, [h('span', {}, [r[0], r[1] ? h('small', { text: r[1] }) : null]), pill(r[3], r[2])]));
      });
      pane.appendChild(ol);
      return pane;
    }
    function confirmCard() {
      var op = S.opp, pane = h('div', { 'class': 'cve-pane', style: 'border-color:#514429;background:#15120D' });
      pane.appendChild(h('div', { 'class': 'cve-sub', text: 'Work entry preflight' }));
      pane.appendChild(h('h3', { style: 'margin-top:4px', text: 'Enter ' + (op.title || op.ref) }));
      pane.appendChild(kv([
        ['Principal', S.pr.agent_id, 'principal'], ['Registration', 'BOUND', 'registration'],
        ['Governance', MODE_LABEL[op.entry_mode] || op.entry_mode], ['Evidence class', S.ev, 'evidence'],
        ['Acceptance', op.acceptance.kind, 'acc-kind'], ['Reference', op.ref]]));
      pane.appendChild(h('div', { 'class': 'cve-note',
        text: 'Self-service write is bound to the active principal and fails closed if authorization cannot be verified. ' +
              'No alternate registration door is introduced.' }));
      pane.appendChild(h('div', { 'class': 'cve-note', 'data-testid': 'force-assign',
        text: 'Force assign · ADMIN ONLY: an operator invite the agent must accept; nothing is entered until the agent accepts. ' +
              '(Not available in this build.)' }));
      return pane;
    }
    function receipt(res) {
      var a = res.agreement, r = res.receipt || (res.receipts && res.receipts[res.receipts.length - 1]) || {};
      var d = h('div', { 'class': 'cve-rcpt', 'data-testid': 'enter-receipt' });
      d.appendChild(h('div', { 'class': 'cve-sub', text: 'Durable receipt' }));
      d.appendChild(kv([
        ['Agreement', a.agreement_id, 'agreement-id'], ['State', a.state, 'agreement-state'],
        ['Receipt', r.receipt_id, 'receipt-id'], ['Transition', (r.from || '') + ' → ' + (r.to || ''), 'transition'],
        ['Principal', r.credential_ref || S.pr.agent_id], ['Mode', a.entry_mode],
        ['Committed', fmt(r.at)], ['Seed', r.seed_doi, 'seed-doi']]));
      return d;
    }
    function outcome() {
      var pane = h('div', { 'data-testid': 'enter-outcome' });
      if (S.err) {
        pane.appendChild(h('div', { 'class': 'cve-err', 'data-testid': 'enter-error', text: S.err }));
        return pane;
      }
      var res = S.out, a = res.agreement;
      var head = a.state === 'active' ? 'You are in: entry active' :
                 a.state === 'accepted' ? 'Entry accepted. One more click.' :
                 'Pending: the opportunity owner decides';
      pane.appendChild(h('div', { 'class': 'cve-ok' }, [statePill(a.state), ' ', h('b', { text: head }),
        h('div', { text: res.next || '' }), waitLine(res)]));
      pane.appendChild(receipt(res));
      if (a.state === 'accepted') {
        pane.appendChild(h('button', { 'class': 'cve-btn primary', id: 'cve-click2', type: 'button',
          style: 'width:100%;margin-top:10px', text: 'ACCEPT & ACTIVATE · CLICK 2', onclick: activate }));
      }
      if (res.mission_id) {
        pane.appendChild(h('a', { 'class': 'cve-btn', href: res.mission_control || ('/missions?mission=' + res.mission_id),
          style: 'display:block;text-align:center;margin-top:8px;text-decoration:none', 'data-testid': 'mc-link',
          text: 'Track in Mission Control →' }));
      }
      return pane;
    }
    function activate() {
      var a = S.out.agreement;
      S.busy = true; render();
      req('POST', '/api/work-entry/' + encodeURIComponent(a.agreement_id) + '/activate', {}).then(function (res) {
        S.busy = false;
        if (res.ok) S.out = res.json; else S.err = errText(res);
        render();
      });
    }
    function confirmEntry() {
      S.busy = true; render();
      var body = { opportunity_ref: S.ref, pitch: S.note, delivery_evidence_class: S.ev, idempotency_key: S.key };
      req('POST', '/api/work-entry', body).then(function (res) {
        S.busy = false;
        if (res.ok) { S.out = res.json; S.err = null; }
        else {
          S.out = null; S.err = errText(res);
          if (res.json && res.json.agreement_id) S.err += ' — existing entry ' + res.json.agreement_id;
        }
        S.step = 5; render();
      });
    }
    function render() {
      clear(box);
      box.appendChild(h('div', { 'class': 'cve-sub', text: 'Enter / match' }));
      box.appendChild(h('h3', { 'data-testid': 'enter-title', text: S.title || (S.opp && S.opp.title) || S.ref }));
      var st = h('div', { 'class': 'cve-steps' });
      STEPS.forEach(function (n, i) {
        st.appendChild(h('span', { 'data-step': i + 1, 'class': i + 1 < S.step ? 'done' : i + 1 === S.step ? 'cur' : '',
          text: (i + 1 < S.step ? '✓ ' : (i + 1) + ' ') + n }));
      });
      box.appendChild(st);
      if (S.loading) { box.appendChild(h('div', { 'class': 'cve-pane', text: 'Loading terms from the server…' })); return; }
      if (!S.opp) {
        box.appendChild(h('div', { 'class': 'cve-err', 'data-testid': 'enter-error', text: S.err || 'Opportunity unavailable' }));
        box.appendChild(h('div', { 'class': 'cve-nav' }, [h('button', { 'class': 'cve-btn', type: 'button', text: 'CLOSE', onclick: close })]));
        return;
      }
      box.appendChild(S.step === 1 ? intent() : S.step === 2 ? terms() : S.step === 3 ? preflight() :
                      S.step === 4 ? confirmCard() : outcome());
      var nav = h('div', { 'class': 'cve-nav' });
      if (S.step === 1) nav.appendChild(h('button', { 'class': 'cve-btn', type: 'button', id: 'cve-cancel', text: 'CANCEL', onclick: close }));
      else if (S.step < 5) nav.appendChild(h('button', { 'class': 'cve-btn', type: 'button', id: 'cve-back', text: 'BACK',
        onclick: function () { S.step--; render(); } }));
      else nav.appendChild(h('button', { 'class': 'cve-btn', type: 'button', id: 'cve-done', text: 'DONE', onclick: close }));
      if (S.step < 4) nav.appendChild(h('button', { 'class': 'cve-btn primary', type: 'button', id: 'cve-continue',
        text: S.step === 3 ? 'REVIEW & CONFIRM' : 'CONTINUE', disabled: !!blocked() || S.busy,
        onclick: function () { S.step++; render(); } }));
      else if (S.step === 4) nav.appendChild(h('button', { 'class': 'cve-btn primary', type: 'button', id: 'cve-confirm',
        text: S.busy ? 'COMMITTING…' : 'CONFIRM ENTRY', disabled: S.busy, onclick: confirmEntry }));
      box.appendChild(nav);
    }
    render();
    Promise.all([
      req('GET', '/api/work-entry/opportunity/' + encodeURIComponent(S.ref).replace(/%3A/g, ':')),
      req('GET', '/api/principal')
    ]).then(function (rs) {
      S.loading = false;
      if (rs[0].ok) S.opp = rs[0].json; else S.err = errText(rs[0]);
      S.pr = rs[1].ok && rs[1].json && rs[1].json.kind === 'agent' ? rs[1].json : null;
      render();
    }).catch(function () { S.loading = false; S.err = 'Could not reach the server'; render(); });
    return { close: close };
  };

  // ═════════════════════════════════════════════════════════════════════════
  // 2. Poster side: accept / reject / retire (plus the entrant's withdraw, and click 2)
  // ═════════════════════════════════════════════════════════════════════════
  E.mountPosterPanel = function (host, o) {
    css();
    host = $(host);
    if (!host) return;
    var magic = o.magic ? { magic: o.magic, threadId: o.threadId } : null;
    var me = null, msg = null;
    var root = h('div', { 'class': 'cve-panel', id: 'entry-panel', 'data-testid': 'entry-panel' });
    host.appendChild(root);

    function act(a, name, reason) {
      return req('POST', '/api/work-entry/' + encodeURIComponent(a.agreement_id) + '/' + name,
                 reason ? { reason: reason } : {}, magic).then(function (res) {
        msg = res.ok ? { ok: true, text: name + ' → ' + res.json.agreement.state + ' · receipt ' + res.json.receipt.receipt_id }
                     : { ok: false, text: errText(res) };
        load();
      });
    }
    function row(a) {
      var owner = a.principals.filter(function (p) { return p.role === 'owner'; })[0].id;
      var entrant = a.principals.filter(function (p) { return p.role === 'entrant'; })[0].id;
      var isOwner = (me && me.kind === 'poster_link') || (me && me.agent_id === owner);
      var isEntrant = me && me.agent_id === entrant;
      var d = h('div', { 'class': 'cve-row', 'data-testid': 'entry-row', 'data-agreement-id': a.agreement_id, 'data-state': a.state });
      d.appendChild(h('div', {}, [statePill(a.state), ' ', h('b', { text: ' ' + entrant }),
        h('span', { 'class': 'cve-sub', text: '  ' + a.agreement_id + ' · ' + a.entry_mode })]));
      if (a.terms && a.terms.pitch) d.appendChild(h('p', { style: 'margin:6px 0 0;font-size:12px;color:#9AA0A6', text: a.terms.pitch }));
      if (a.outcome_reason) d.appendChild(h('p', { style: 'margin:4px 0 0;font-size:11px;color:#E0A0A0', text: 'Reason: ' + a.outcome_reason }));
      var acts = h('div', { 'class': 'acts' });
      var reason = h('input', { 'class': 'cve-in', placeholder: 'Reason (required to reject; optional to retire)', 'data-testid': 'reason' });
      var live = a.state === 'pending' || a.state === 'dormant';
      if (isOwner && live) {
        acts.appendChild(reason);
        acts.appendChild(h('button', { 'class': 'cve-btn primary', type: 'button', 'data-act': 'accept', text: 'ACCEPT',
          onclick: function () { act(a, 'accept'); } }));
        acts.appendChild(h('button', { 'class': 'cve-btn danger', type: 'button', 'data-act': 'reject', text: 'REJECT',
          onclick: function () {
            if (!reason.value.trim()) { msg = { ok: false, text: 'A rejection carries a named reason.' }; paint(); return; }
            act(a, 'reject', reason.value.trim());
          } }));
        acts.appendChild(h('button', { 'class': 'cve-btn', type: 'button', 'data-act': 'retire', text: 'RETIRE',
          onclick: function () { act(a, 'retire', reason.value.trim()); } }));
      }
      if (isEntrant && live) {
        acts.appendChild(h('button', { 'class': 'cve-btn', type: 'button', 'data-act': 'withdraw', text: 'WITHDRAW',
          onclick: function () { act(a, 'withdraw'); } }));
      }
      if ((isOwner || isEntrant) && a.state === 'accepted') {
        acts.appendChild(h('button', { 'class': 'cve-btn primary', type: 'button', 'data-act': 'activate',
          text: 'ACTIVATE · CLICK 2', onclick: function () { act(a, 'activate'); } }));
      }
      if (acts.childNodes.length) d.appendChild(acts);
      return d;
    }
    var rows = [];
    function paint() {
      clear(root);
      root.appendChild(h('div', { 'class': 'cve-sub', text: 'Entries · WorkEntryAgreements' }));
      root.appendChild(h('h4', { text: 'Entries for ' + o.postId }));
      if (msg) root.appendChild(h('div', { 'class': msg.ok ? 'cve-ok' : 'cve-err', 'data-testid': 'entry-msg', text: msg.text }));
      if (!rows.length) root.appendChild(h('p', { style: 'color:#8E949A', text: 'No entries filed yet. Messages and threads are not entries.' }));
      rows.forEach(function (a) { root.appendChild(row(a)); });
    }
    function load() {
      Promise.all([
        req('GET', '/api/principal', null, magic),
        req('GET', '/api/work-entry?include_dormant=true&opportunity_ref=' + encodeURIComponent('post:' + o.postId), null, magic)
      ]).then(function (rs) {
        me = rs[0].ok ? rs[0].json : null;
        rows = rs[1].ok ? rs[1].json.entries : [];
        if (!rs[1].ok) msg = { ok: false, text: errText(rs[1]) };
        paint();
      });
    }
    paint(); load();
  };

  // ═════════════════════════════════════════════════════════════════════════
  // 3. Mission Control: Agreement node, Acceptance record, PROGRESS
  // ═════════════════════════════════════════════════════════════════════════
  var CHAIN = ['terms_accepted', 'active'];

  function chain(state) {
    var c = h('div', { 'class': 'cve-chain', 'data-testid': 'node-chain' });
    var lit = { accepted: 1, active: 2, completed: 2, terminated: 2 }[state] || 0;
    c.appendChild(h('span', { 'class': lit >= 1 ? 'lit' : '', text: CHAIN[0] }));
    c.appendChild(document.createTextNode('→'));
    c.appendChild(h('span', { 'class': lit >= 2 ? 'lit' : '', text: CHAIN[1] }));
    return c;
  }
  function acceptanceCard(row) {
    var ac = row.acceptance, a = row.agreement, d = h('div', { 'class': 'cve-pane', 'data-testid': 'acceptance-record' });
    d.appendChild(h('div', { 'class': 'cve-sub', text: 'Acceptance record · references, not content' }));
    d.appendChild(kv([
      ['Terms accepted', fmt(ac.terms_accepted_at), 'terms-accepted-at'],
      ['Accepted by', ac.accepted_by, 'accepted-by'],
      ['Via credential', ac.accepted_via],
      ['Active since', fmt(ac.active_at), 'active-at'],
      ['Evidence class', ac.delivery_evidence_class, 'evidence-class'],
      ['Receipt', ac.acceptance_receipt_id, 'acceptance-receipt'],
      ['Seed', ac.acceptance_seed_doi, 'acceptance-seed'],
      ['Outcome', ac.outcome_reason || a.state]]));
    return d;
  }
  function progressList(row, deployments) {
    var ul = h('ul', { 'class': 'cve-tl', 'data-testid': 'progress-list' });
    row.receipts.forEach(function (r) {
      ul.appendChild(h('li', { 'data-transition': r.transition }, [
        h('b', { text: r.transition }), ' ' + (r.from || '∅') + ' → ' + r.to,
        h('small', { text: fmt(r.at) + ' · ' + (r.acting_for ? r.actor + ' for ' + r.acting_for : r.actor) +
          ' · ' + (r.credential_ref || '') + ' · ' + r.receipt_id + ' · ' + (r.seed_doi || 'no seed') })]));
    });
    (deployments || []).filter(function (d) { return d.agreement_id === row.agreement.agreement_id; }).forEach(function (d) {
      ul.appendChild(h('li', { 'data-transition': 'deploy' }, [h('b', { text: 'deploy' }),
        h('small', { text: fmt(d.at) + ' · ' + (d.receipt_id || '') })]));
    });
    return ul;
  }
  function renderMission(root, data, sel, tab, again) {
    clear(root);
    root.appendChild(h('div', { 'class': 'cve-sub', text: 'Mission Control · Agreement' }));
    root.appendChild(h('h4', { text: 'Mission ' + data.mission_id + ' · ' + data.entry_mode + ' entry' +
      (data.frozen ? ' · FROZEN' : '') }));
    if (!data.agreements.length) {
      root.appendChild(h('p', { 'data-testid': 'no-agreement', style: 'color:#8E949A',
        text: 'No Agreement on this mission yet. Published is not active: the mission becomes active through an accepted, activated entry.' }));
      return;
    }
    var nodes = h('div', {});
    data.agreements.forEach(function (r) {
      var a = r.agreement;
      var n = h('button', { 'class': 'cve-node' + (a.agreement_id === sel ? ' on' : ''), type: 'button',
        'data-testid': 'agreement-node', 'data-agreement-id': a.agreement_id, 'data-state': a.state,
        onclick: function () { renderMission(root, data, a.agreement_id, tab, again); } }, [
        h('b', { text: 'AGREEMENT · ' + a.agreement_id }),
        h('span', { 'data-testid': 'node-label', text: 'terms_accepted → active' }),
        chain(a.state), statePill(a.state)]);
      nodes.appendChild(n);
    });
    root.appendChild(nodes);
    var row = data.agreements.filter(function (r) { return r.agreement.agreement_id === sel; })[0] || data.agreements[0];
    var tabs = h('div', { 'class': 'cve-tabs' });
    ['INSPECTOR', 'PROGRESS'].forEach(function (t) {
      tabs.appendChild(h('button', { type: 'button', 'data-tab': t, 'class': t === tab ? 'on' : '', text: t,
        onclick: function () { renderMission(root, data, row.agreement.agreement_id, t, again); } }));
    });
    root.appendChild(tabs);
    var a = row.agreement;
    if (tab === 'PROGRESS') {
      root.appendChild(h('div', { 'data-testid': 'progress-tab' }, [progressList(row, data.deployments)]));
    } else {
      var obj = a.objects || {};
      root.appendChild(h('div', { 'data-testid': 'inspector-tab' }, [
        kv([['agreement_id', a.agreement_id, 'agreement-id'], ['state', a.state, 'agreement-state'],
            ['mode', a.entry_mode], ['post / slot', [obj.post_id, obj.slot_id].filter(Boolean).join(' · ')],
            ['entrant', a.principals.filter(function (p) { return p.role === 'entrant'; })[0].id],
            ['owner', a.principals.filter(function (p) { return p.role === 'owner'; })[0].id]]),
        acceptanceCard(row)]));
    }
  }
  function missionData(id) {
    return req('GET', '/api/work-entry/mission/' + encodeURIComponent(id));
  }
  E.mountMission = function (host, missionId) {
    css();
    host = $(host);
    var id = missionId || qp('mission') || qp('id');
    if (!host || !id) return;
    var root = h('div', { 'class': 'cve-panel', id: 'mc-agreement', 'data-testid': 'mc-agreement' });
    host.appendChild(root);
    root.appendChild(h('p', { text: 'Loading Agreement…' }));
    missionData(id).then(function (res) {
      if (!res.ok) {
        clear(root);
        root.appendChild(h('div', { 'class': 'cve-sub', text: 'Mission Control · Agreement' }));
        root.appendChild(h('p', { 'data-testid': 'mc-agreement-note', style: 'color:#8E949A',
          text: res.status === 401 ? 'Sign in to see the Agreement on this mission.' :
                res.status === 403 ? 'Only a party to an Agreement on this mission (or an operator) can read it.' :
                errText(res) }));
        return;
      }
      renderMission(root, res.json, res.json.node && res.json.node.agreement_id, 'INSPECTOR');
    });
  };
  E.mountMine = function (host) {
    css();
    host = $(host);
    if (!host) return;
    var root = h('div', { 'class': 'cve-panel', id: 'mc-mine', 'data-testid': 'mc-mine' });
    host.appendChild(root);
    req('GET', '/api/work-entry?live=true').then(function (res) {
      clear(root);
      root.appendChild(h('div', { 'class': 'cve-sub', text: 'Mission Control · my Agreements' }));
      if (!res.ok) {
        root.appendChild(h('p', { style: 'color:#8E949A', text: res.status === 401 ? 'Sign in to see your Agreements.' : errText(res) }));
        return;
      }
      var entries = res.json.entries;
      if (!entries.length) { root.appendChild(h('p', { style: 'color:#8E949A', text: 'No live Agreements.' })); return; }
      var detail = h('div', {});
      entries.forEach(function (a) {
        var mid = a.objects && a.objects.mission_id;
        var n = h('button', { 'class': 'cve-node', type: 'button', 'data-testid': 'agreement-node',
          'data-agreement-id': a.agreement_id, 'data-state': a.state,
          onclick: function () {
            clear(detail);
            if (mid) E.mountMission(detail, mid);
            else detail.appendChild(h('p', { style: 'color:#8E949A', text: 'Not bound to a mission yet (' + a.state + ').' }));
          } }, [h('b', { text: 'AGREEMENT · ' + a.agreement_id }),
                h('span', { text: 'terms_accepted → active' }), chain(a.state), statePill(a.state),
                h('span', { class: 'cve-sub', text: a.opportunity_ref })]);
        root.appendChild(n);
      });
      root.appendChild(detail);
    });
  };

  // ═════════════════════════════════════════════════════════════════════════
  // 4. COMMAND / DEPLOY: ARM DEPLOY preflight (+ second confirmation in COMMAND)
  // ═════════════════════════════════════════════════════════════════════════
  var BLOCK_TEXT = {
    no_active_agreement: 'No active Agreement on this mission.',
    no_deploy_authority: 'You do not hold deploy authority on this mission.',
    mission_frozen: 'ARM DEPLOY is unavailable while the contract is frozen.',
    mission_not_deployable: 'This mission has ended and cannot be deployed.',
    governance_gate_required: 'The governance gate for this mission is not satisfied.',
    owner_countersign_required: 'The governance motion passed but is advisory; the owner countersign is required.'
  };
  E.mountDeploy = function (host, o) {
    css();
    o = o || {};
    host = $(host);
    if (!host) return;
    var mode = o.mode === 'command' ? 'command' : 'arm';
    var root = h('div', { 'class': 'cve-panel' + (o.floating ? ' cve-float' : ''), id: 'arm-deploy',
                          'data-testid': 'arm-deploy', 'data-mode': mode });
    host.appendChild(root);
    var S = { mid: qp('mission'), pre: null, out: null, err: null, key: uuid(), missions: [], open: !o.floating };

    function paint() {
      clear(root);
      if (o.floating && !S.open) {
        root.appendChild(h('button', { 'class': 'cve-btn', type: 'button', id: 'cve-arm-open', 'data-testid': 'arm-open',
          text: 'DEPLOY \u00b7 ARM DEPLOY PREFLIGHT \u25b8', onclick: function () { S.open = true; paint(); } }));
        return;
      }
      root.appendChild(h('div', { 'class': 'cve-sub', text: mode === 'command' ? 'COMMAND · second confirmation' : 'Deploy · ARM DEPLOY preflight' }));
      root.appendChild(h('h4', { text: 'ARM DEPLOY' }));
      root.appendChild(h('p', { style: 'color:#8E949A', text: 'Deploy is bound to an active Agreement with deploy authority. ' +
        'DEPLOY is not COMMAND and not CAMPAIGN. Arming only opens this read-only preflight.' }));
      var dl = h('datalist', { id: 'cve-missions' });
      S.missions.forEach(function (m) { dl.appendChild(h('option', { value: m })); });
      var inp = h('input', { 'class': 'cve-in', id: 'cve-mission', list: 'cve-missions', placeholder: 'mission id' });
      inp.value = S.mid;
      inp.addEventListener('input', function () { S.mid = inp.value.trim(); });
      root.appendChild(h('div', {}, [inp, dl]));
      root.appendChild(h('div', { 'class': 'cve-nav', style: 'justify-content:flex-start' }, [
        h('button', { 'class': 'cve-btn primary', type: 'button', id: 'cve-arm', text: 'ARM DEPLOY', onclick: arm })]));
      if (S.err) root.appendChild(h('div', { 'class': 'cve-err', 'data-testid': 'arm-error', text: S.err }));
      if (S.pre) root.appendChild(preflightView(S.pre));
      if (S.out) root.appendChild(h('div', { 'class': 'cve-ok', 'data-testid': 'deploy-receipt' }, [
        h('b', { text: 'Deployed' }),
        kv([['Receipt', S.out.receipt.receipt_id, 'deploy-receipt-id'], ['Seed', S.out.receipt.seed_doi, 'deploy-seed'],
            ['Agreement', S.out.agreement_id], ['Mission', S.out.mission_id]])]));
    }
    function preflightView(p) {
      var d = h('div', { 'class': 'cve-pane', 'data-testid': 'preflight' });
      var ag = p.agreements.filter(function (a) { return a.agreement_id === p.agreement_id; })[0];
      var steps = [
        ['Resolve principal', p.caller.principal || p.caller.credential, !!p.caller.principal],
        ['Active Agreement', p.agreement_id ? p.agreement_id + (ag ? ' · ' + ag.state : '') :
          (p.agreements.length ? p.agreements.length + ' Agreement(s), none holds deploy authority' : 'none'), !!p.agreement_id],
        ['Deploy authority', ag && ag.holds_deploy_authority ? 'held by the owner principal' : 'not held', !!(ag && ag.holds_deploy_authority)],
        ['Governance gate', p.gate.kind + (p.gate.required ? ' (required)' : ' (none)') +
          (p.gate.satisfied ? ' · satisfied' : ' · not satisfied') + ' · mode ' + p.entry_mode, !!p.gate.satisfied],
        ['Mission not frozen', p.frozen ? 'FROZEN' : 'mission ' + p.mission_status, !p.frozen]];
      var ol = h('ol', { 'class': 'cve-list' });
      steps.forEach(function (s) { ol.appendChild(h('li', {}, [h('span', { text: s[0] }, [h('small', { text: s[1] })]), pill(s[2] ? 'live' : 'block', s[2] ? 'OK' : 'NO')])); });
      d.appendChild(ol);
      if (p.can_deploy) {
        d.appendChild(h('div', { 'class': 'cve-ok', 'data-testid': 'arm-available', text: 'ARM DEPLOY IS AVAILABLE' }));
        if (mode === 'command') {
          d.appendChild(h('button', { 'class': 'cve-btn primary', type: 'button', id: 'cve-deploy', style: 'margin-top:8px',
            text: 'CONFIRM DEPLOY · SECOND CONFIRMATION', onclick: deploy }));
        } else {
          d.appendChild(h('a', { 'class': 'cve-btn', id: 'cve-to-command', style: 'display:inline-block;margin-top:8px;text-decoration:none',
            href: '/command?mission=' + encodeURIComponent(p.mission_id), text: 'Second confirmation in COMMAND →' }));
        }
      } else {
        d.appendChild(h('div', { 'class': 'cve-warn', 'data-testid': 'arm-blocked', 'data-blocking': p.blocking,
          text: BLOCK_TEXT[p.blocking] || p.blocking }));
      }
      return d;
    }
    function arm() {
      S.err = null; S.pre = null; S.out = null;
      if (!S.mid) { S.err = 'Enter a mission id.'; paint(); return; }
      req('GET', '/api/work-entry/mission/' + encodeURIComponent(S.mid) + '/deploy/preflight').then(function (res) {
        if (res.ok) S.pre = res.json; else S.err = errText(res);
        paint();
      });
    }
    function deploy() {
      req('POST', '/api/work-entry/mission/' + encodeURIComponent(S.mid) + '/deploy',
          { agreement_id: S.pre.agreement_id, idempotency_key: S.key }).then(function (res) {
        if (res.ok) { S.out = res.json; S.err = null; } else S.err = errText(res);
        paint();
      });
    }
    paint();
    req('GET', '/api/work-entry?live=true').then(function (res) {
      if (res.ok) {
        var seen = {};
        res.json.entries.forEach(function (a) { var m = a.objects && a.objects.mission_id; if (m) seen[m] = 1; });
        S.missions = Object.keys(seen);
        if (!S.mid && S.missions.length === 1) S.mid = S.missions[0];
        paint();
        if (S.mid && o.auto) arm();
      }
    });
  };

  return E;
})();
