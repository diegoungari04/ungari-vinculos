/* Ungari Vínculos: SPA */
const S = { me: null, meta: null, companyId: null, charts: [] };
const BCOL = { CO: "#16875A", CN: "#5160C8", EN: "#D07A1E" };
const BONDS = ["CO", "CN", "EN"];
const LEVELS = ["ART", "VAL", "PRE"];
const $ = (s, el = document) => el.querySelector(s);
const app = () => $("#app");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n, d = 1) => (n == null ? "–" : Number(n).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const fdate = (s) => (s ? new Date(s + (s.endsWith("Z") ? "" : "Z")).toLocaleDateString("pt-BR") : "–");
const rank = (r) => ({ colaborador: 0, gestor: 1, admin: 2, master: 3 }[r]);

async function api(path, opts = {}) {
  const o = { headers: { "Content-Type": "application/json" }, credentials: "same-origin", ...opts };
  if (o.body && typeof o.body !== "string") o.body = JSON.stringify(o.body);
  const r = await fetch(path, o);
  if (r.status === 401 && !path.startsWith("/api/login") && !path.startsWith("/api/invite")) {
    S.me = null; location.hash = "#/login"; throw new Error("auth");
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Algo deu errado.");
  return data;
}
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 3200); }
function killCharts() { S.charts.forEach((c) => c.destroy()); S.charts = []; }
function cq(params = {}) {
  const p = new URLSearchParams();
  if (S.me?.role === "master" && S.companyId) p.set("company_id", S.companyId);
  Object.entries(params).forEach(([k, v]) => v != null && v !== "" && p.set(k, v));
  const s = p.toString(); return s ? "?" + s : "";
}
function profileChip(code) {
  const p = S.meta.profiles[code]; if (!p) return "";
  return `<span class="chip"><span class="dot" style="background:${p.color}"></span>${esc(p.name)}</span>`;
}
async function copy(text) { try { await navigator.clipboard.writeText(text); toast("Link copiado."); } catch { prompt("Copie o link:", text); } }

/* ─── Navegação ─────────────────────────────────────────────── */
function buildNav() {
  const me = S.me, r = rank(me.role);
  const items = [["#/inicio", "Início"], ["#/resultado/" + me.id, "Meu resultado"]];
  if (me.has_team || r >= 3) items.push(["#/time", r >= 3 ? "Pessoas e times" : "Meu time"]);
  if (r >= 2) items.push(["#/organizacao", "Áreas e empresa"], ["#/pessoas", "Cadastro"], ["#/coletas", "Coletas"]);
  if (r >= 3) items.push(["#/instrumento", "Questionário"], ["#/empresas", "Empresas"]);
  $("#nav").innerHTML = items.map(([h, l]) => `<a href="${h}" data-h="${h}">${l}</a>`).join("");
  $("#topbar").classList.remove("hidden");
  $("#menuBtn").onclick = (e) => {
    e.stopPropagation();
    let d = $(".dropdown"); if (d) return d.remove();
    d = document.createElement("div"); d.className = "dropdown";
    d.innerHTML = `<div class="head"><b>${esc(me.name)}</b><div class="tiny muted">${esc(me.role_label)}${me.company_name ? " · " + esc(me.company_name) : ""}</div></div>
      <a href="#/conta">Minha conta</a><button id="logoutBtn">Sair</button>`;
    document.body.appendChild(d);
    $("#logoutBtn").onclick = async () => { await api("/api/logout", { method: "POST" }); S.me = null; d.remove(); location.hash = "#/login"; };
    setTimeout(() => document.addEventListener("click", () => d.remove(), { once: true }));
  };
}
async function buildCompanySel() {
  const sel = $("#companySel");
  if (S.me.role !== "master") return sel.classList.add("hidden");
  const cs = await api("/api/companies");
  if (!S.companyId && cs.length) S.companyId = localStorage.getItem("uv_company") || cs[0].id;
  if (!cs.find((c) => String(c.id) === String(S.companyId))) S.companyId = cs[0]?.id || null;
  sel.innerHTML = cs.map((c) => `<option value="${c.id}" ${String(c.id) === String(S.companyId) ? "selected" : ""}>${esc(c.name)}</option>`).join("");
  sel.classList.toggle("hidden", !cs.length);
  sel.onchange = () => { S.companyId = sel.value; try { localStorage.setItem("uv_company", sel.value); } catch {} route(); };
}
function markNav() {
  const h = location.hash;
  document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("on", h.startsWith(a.dataset.h) && (a.dataset.h !== "#/inicio" || h === "#/inicio")));
}

const routes = [
  [/^#\/login$/, viewLogin, true], [/^#\/convite\/(.+)$/, viewInvite, true],
  [/^#\/inicio$/, viewHome], [/^#\/questionario\/(\d+)$/, viewQuestionnaire],
  [/^#\/resultado\/(\d+)$/, viewReport], [/^#\/time$/, viewTeam], [/^#\/organizacao$/, viewOrg],
  [/^#\/pessoas$/, viewPeople], [/^#\/coletas$/, viewCampaigns], [/^#\/coletas\/(\d+)$/, viewCampaign],
  [/^#\/instrumento$/, viewInstrument], [/^#\/empresas$/, viewCompanies], [/^#\/conta$/, viewAccount],
];
async function route() {
  killCharts();
  const h = location.hash || "#/inicio";
  for (const [re, fn, pub] of routes) {
    const m = h.match(re); if (!m) continue;
    if (!pub && !S.me) {
      try { S.me = await api("/api/me"); S.meta = await api("/api/meta"); buildNav(); await buildCompanySel(); }
      catch { return; }
    }
    if (pub) $("#topbar").classList.add("hidden");
    else { app().style.padding = ""; app().style.maxWidth = ""; }
    markNav(); window.scrollTo(0, 0);
    try { await fn(...m.slice(1)); } catch (e) { if (e.message !== "auth") app().innerHTML = `<div class="card"><h2>Ops</h2><p>${esc(e.message)}</p></div>`; }
    return;
  }
  location.hash = "#/inicio";
}
window.addEventListener("hashchange", route);
window.addEventListener("load", route);

/* ─── Login e convite ───────────────────────────────────────── */
function authShell(inner) {
  return `<div class="auth"><div class="side"><div><img src="/static/img/ungari-rev.png" alt="Ungari Mentoria & Consultoria">
    <h1>Diagnóstico de Vínculos e Cultura</h1>
    <p>Entenda o que liga as pessoas à organização e como a cultura chega até cada uma delas.</p>
    <div class="tri"><span>Querer ficar</span><span>Dever obedecer</span><span>Precisar ficar</span></div></div>
    <p class="tiny" style="opacity:.75">Baseado em Ungari (2019), Silva (2013), Rodrigues e Bastos (2012) e Schein (2009).</p></div>
    <div class="form">${inner}</div></div>`;
}
async function viewLogin() {
  document.body.style.background = "";
  app().style.padding = "0"; app().style.maxWidth = "none";
  app().innerHTML = authShell(`<form class="card" id="f"><h2>Entrar</h2>
    <div class="field"><label for="em">E-mail</label><input id="em" type="email" autocomplete="username" required></div>
    <div class="field"><label for="pw">Senha</label><input id="pw" type="password" autocomplete="current-password" required></div>
    <p id="err" class="small" style="color:#a33"></p><button style="width:100%;justify-content:center">Entrar</button>
    <p class="tiny muted" style="margin-top:14px">Primeiro acesso? Use o link de convite que você recebeu. Esqueceu a senha? Peça um novo convite ao RH.</p></form>`);
  $("#f").onsubmit = async (e) => {
    e.preventDefault();
    try { await api("/api/login", { method: "POST", body: { email: $("#em").value, password: $("#pw").value } }); resetMain(); location.hash = "#/inicio"; }
    catch (er) { $("#err").textContent = er.message; }
  };
}
function resetMain() { app().style.padding = ""; app().style.maxWidth = ""; S.me = null; }
async function viewInvite(token) {
  app().style.padding = "0"; app().style.maxWidth = "none";
  let info;
  try { info = await api("/api/invite/" + token); }
  catch (e) { app().innerHTML = authShell(`<div class="card"><h2>Convite indisponível</h2><p>${esc(e.message)}</p><a class="btn" href="#/login">Ir para o login</a></div>`); return; }
  app().innerHTML = authShell(`<form class="card" id="f"><h2>Olá, ${esc(info.name.split(" ")[0])}!</h2>
    <p class="muted small">Você foi convidado(a)${info.company ? " por " + esc(info.company) : ""}. Crie sua senha para acessar.</p>
    <div class="field"><label>E-mail</label><input value="${esc(info.email)}" disabled></div>
    <div class="field"><label for="p1">Crie uma senha (mínimo 8 caracteres)</label><input id="p1" type="password" minlength="8" autocomplete="new-password" required></div>
    <div class="field"><label for="p2">Repita a senha</label><input id="p2" type="password" autocomplete="new-password" required></div>
    <p id="err" class="small" style="color:#a33"></p><button style="width:100%;justify-content:center">Criar acesso</button></form>`);
  $("#f").onsubmit = async (e) => {
    e.preventDefault();
    if ($("#p1").value !== $("#p2").value) return ($("#err").textContent = "As senhas não conferem.");
    try { await api("/api/invite/" + token, { method: "POST", body: { password: $("#p1").value } }); resetMain(); location.hash = "#/inicio"; }
    catch (er) { $("#err").textContent = er.message; }
  };
}

/* ─── Início ────────────────────────────────────────────────── */
async function viewHome() {
  const [asg, res] = await Promise.all([api("/api/my/assignments"), api("/api/results/" + S.me.id)]);
  const pend = asg.filter((a) => a.status === "pendente" && a.campaign_status === "aberta");
  const first = S.me.name.split(" ")[0];
  let html = `<h1>Olá, ${esc(first)}.</h1><p class="muted">${esc(S.me.role_label)}${S.me.company_name ? " · " + esc(S.me.company_name) : ""}</p>`;
  if (pend.length) {
    html += pend.map((a) => `<div class="card row between" style="border-left:5px solid var(--sol)"><div><h3 style="margin:0">Você tem um questionário para responder</h3>
      <p class="muted small" style="margin:4px 0 0">${esc(a.campaign)}${a.deadline ? " · prazo " + esc(a.deadline.split("-").reverse().join("/")) : ""} · cerca de 7 minutos</p></div>
      <a class="btn" href="#/questionario/${a.id}">Responder agora</a></div>`).join("");
  }
  if (res.result) {
    const p = res.profile;
    html += `<div class="hero"><div class="eyebrow">Seu perfil de vínculo · ${esc(res.campaign)}</div><h1>${esc(p.name)}</h1>
      <div class="tag">${esc(p.tagline)}</div><div class="row" style="margin-top:18px">
      <a class="btn" style="background:var(--broto);color:var(--floresta)" href="#/resultado/${S.me.id}">Ver relatório completo</a></div></div>
      <div class="card"><h3>Seus vínculos</h3>${bondBars(res.result.bonds, res.result.subs, res.result.cutoff || S.meta.cutoff)}</div>`;
  } else if (!pend.length) {
    html += `<div class="card"><h3>Ainda não há resultado</h3><p class="muted">Quando o RH abrir uma coleta para você, o questionário aparece aqui.</p></div>`;
  }
  if (S.me.has_team) html += `<div class="card row between"><div><h3 style="margin:0">Seu time</h3><p class="muted small" style="margin:4px 0 0">Veja os resultados das pessoas ligadas a você e compare.</p></div><a class="btn" href="#/time">Abrir painel do time</a></div>`;
  app().innerHTML = html;
}

/* ─── Questionário ──────────────────────────────────────────── */
async function viewQuestionnaire(aid) {
  const a = await api("/api/assignments/" + aid);
  if (a.status === "concluida") { app().innerHTML = `<div class="card"><h2>Questionário já respondido</h2><a class="btn" href="#/resultado/${S.me.id}">Ver meu resultado</a></div>`; return; }
  const inst = a.instrument, L = S.meta.likert_labels, PL = S.meta.presence_labels;
  const key = "uv_draft_" + aid;
  let st; try { st = JSON.parse(localStorage.getItem(key)) || null; } catch { st = null; }
  st = st || { step: 0, likert: {}, rank: {}, presence: {} };
  const save = () => { try { localStorage.setItem(key, JSON.stringify(st)); } catch {} };
  const pages = [{ t: "intro" }];
  for (let i = 0; i < inst.likert.length; i += 4) pages.push({ t: "likert", items: inst.likert.slice(i, i + 4) });
  pages.push({ t: "culture-intro" });
  inst.culture.forEach((el) => pages.push({ t: "culture", el }));
  pages.push({ t: "end" });
  const shuffle = (id) => { // ordem estável e embaralhada por bloco, para não induzir padrão de resposta
    const opts = ["CO", "CN", "EN"]; let h = 0; for (const c of id + aid) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return opts.map((o, i) => [o, (h >> (i * 4)) & 15]).sort((x, y) => x[1] - y[1]).map((x) => x[0]);
  };
  function pageValid(pg) {
    if (pg.t === "likert") return pg.items.every((it) => st.likert[it.id]);
    if (pg.t === "culture") return (st.rank[pg.el.id] || []).length === 3 && st.presence[pg.el.id];
    return true;
  }
  function render() {
    const pg = pages[st.step], pct = Math.round((st.step / (pages.length - 1)) * 100);
    let body = "";
    if (pg.t === "intro") body = `<h1>${esc(inst.title)}</h1><p>${esc(inst.intro)}</p>
      <div class="callout small"><b>Como funciona:</b> na primeira parte você indica o quanto concorda com algumas afirmativas.
      Na segunda, para cada aspecto da cultura, você ordena três frases da que mais tem a ver com você até a que menos tem.
      Suas respostas individuais são vistas apenas por você, por sua liderança e pela consultoria.</div>`;
    if (pg.t === "likert") body = `<div class="elname">Parte 1 de 2 · Sua relação com a organização</div>` + pg.items.map((it) => `
      <div class="qitem"><div class="stmt">${esc(it.text)}</div><div class="scale" role="radiogroup" aria-label="${esc(it.text)}">
      ${L.map((l, i) => `<button type="button" role="radio" aria-checked="${st.likert[it.id] === i + 1}" class="${st.likert[it.id] === i + 1 ? "sel" : ""}" data-it="${it.id}" data-v="${i + 1}">${l}</button>`).join("")}</div></div>`).join("");
    if (pg.t === "culture-intro") body = `<div class="elname">Parte 2 de 2 · A cultura a partir de você</div><h2>Agora, a cultura</h2>
      <p>Você verá 8 aspectos da cultura da organização. Para cada um, toque nas três frases <b>na ordem</b>: primeiro a que mais tem a ver com o que você vive aqui, depois a segunda, e a última fica por último.
      Nenhuma frase é melhor que a outra. Depois, diga o quanto aquele aspecto é forte no seu dia a dia.</p>
      <p class="muted small">Errou a ordem? Toque de novo numa frase para desmarcar.</p>`;
    if (pg.t === "culture") {
      const el = pg.el, r = st.rank[el.id] || [];
      body = `<div class="elname">Parte 2 de 2 · ${esc(el.name)}</div><h2 style="margin-bottom:16px">${esc(el.prompt)}</h2>
        ${shuffle(el.id).map((b) => { const pos = r.indexOf(b) + 1; return `<button type="button" class="rankopt ${pos ? "r" + pos : ""}" data-b="${b}"><span class="badge">${pos || ""}</span><span>${esc(el.options[b])}</span></button>`; }).join("")}
        <p class="small muted" style="margin:16px 0 8px">Quanto este aspecto está presente no seu dia a dia aqui?</p>
        <div class="presence">${PL.map((l, i) => `<button type="button" class="${st.presence[el.id] === i + 1 ? "sel" : ""}" data-p="${i + 1}">${l}</button>`).join("")}</div>`;
    }
    if (pg.t === "end") body = `<h2>Tudo pronto!</h2><p>Revise se quiser, voltando às telas anteriores. Ao enviar, seu relatório é gerado na hora.</p><p id="err" style="color:#a33"></p>`;
    app().innerHTML = `<div class="qwrap"><div class="row between small muted"><span>${esc(a.campaign)}</span><span>${pct}%</span></div>
      <div class="progress"><div style="width:${pct}%"></div></div><div class="card">${body}</div>
      <div class="row between"><button class="ghost" id="back" ${st.step === 0 ? "disabled" : ""}>Voltar</button>
      ${pg.t === "end" ? `<button id="send">Enviar respostas</button>` : `<button id="next" ${pageValid(pg) ? "" : "disabled"}>Continuar</button>`}</div></div>`;
    app().querySelectorAll("[data-it]").forEach((b) => (b.onclick = () => { st.likert[b.dataset.it] = +b.dataset.v; save(); render(); }));
    app().querySelectorAll("[data-b]").forEach((b) => (b.onclick = () => {
      const id = pg.el.id, cur = st.rank[id] || [], i = cur.indexOf(b.dataset.b);
      st.rank[id] = i >= 0 ? cur.slice(0, i) : [...cur, b.dataset.b];
      if (st.rank[id].length === 2) st.rank[id].push(["CO", "CN", "EN"].find((x) => !st.rank[id].includes(x)));
      save(); render();
    }));
    app().querySelectorAll("[data-p]").forEach((b) => (b.onclick = () => { st.presence[pg.el.id] = +b.dataset.p; save(); render(); }));
    $("#back").onclick = () => { st.step--; save(); render(); window.scrollTo(0, 0); };
    if ($("#next")) $("#next").onclick = () => { st.step++; save(); render(); window.scrollTo(0, 0); };
    if ($("#send")) $("#send").onclick = async () => {
      $("#send").disabled = true;
      try {
        await api(`/api/assignments/${aid}/submit`, { method: "POST", body: { likert: st.likert, rank: st.rank, presence: st.presence } });
        try { localStorage.removeItem(key); } catch {}
        location.hash = "#/resultado/" + S.me.id;
      } catch (e) { $("#err").textContent = e.message; $("#send").disabled = false; }
    };
  }
  render();
}

/* ─── Blocos visuais ────────────────────────────────────────── */
function bondBars(bonds, subs, cut = S.meta.cutoff || 4) {
  const pos = (v) => ((v - 1) / 5) * 100;
  return BONDS.map((b) => {
    const m = S.meta.bonds[b], v = bonds[b];
    const ss = subs ? Object.entries(subs).filter(([k]) => k.startsWith(b + "|")).map(([k, x]) => `${k.split("|")[1]} ${fmt(x)}`).join(" · ") : "";
    return `<div class="bondbar"><div class="lbl"><span>${m.name} <span class="muted small" style="font-weight:500">${m.short}</span></span>
      <span class="mono">${fmt(v)} <span class="muted small">/ 6 · ${v >= cut ? "alto" : "baixo"}</span></span></div>
      <div class="track" role="img" aria-label="${m.name}: ${fmt(v)} de 6"><div class="fill" style="width:${pos(v)}%;background:${BCOL[b]}"></div><div class="cut" style="left:${pos(cut)}%" title="Ponto de corte"></div></div>
      ${ss ? `<div class="sub">${esc(ss)}</div>` : ""}</div>`;
  }).join("") + `<div class="legend tiny"><span><i style="background:var(--carvao);opacity:.55;width:2px"></i>ponto de corte entre baixo e alto (${fmt(cut)})</span></div>`;
}
function stack(share) {
  return `<div class="stackbar">${BONDS.map((b) => share[b] > 0 ? `<div style="width:${share[b]}%;background:${BCOL[b]}" title="${S.meta.bonds[b].name}: ${fmt(share[b], 0)}%">${share[b] >= 12 ? fmt(share[b], 0) + "%" : ""}</div>` : "").join("")}</div>`;
}
function bondLegend() { return `<div class="legend">${BONDS.map((b) => `<span><i style="background:${BCOL[b]}"></i>${S.meta.bonds[b].name}</span>`).join("")}</div>`; }
function levelsBlock(levels) {
  return bondLegend() + LEVELS.filter((l) => levels[l]).map((l) => `<div class="levelrow"><div><b>${S.meta.levels[l].name}</b><div class="tiny muted">${esc(S.meta.levels[l].desc)}</div></div>
    ${stack(levels[l].share)}<div class="small mono" title="Intensidade: quanto esse nível da cultura está presente">força ${fmt(levels[l].intensity, 0)}%</div></div>`).join("");
}
function profileMap(code) {
  const order = ["PROTAGONISTA", "GUARDIAO", "ENRAIZADO", "ANCORA", "EM_TRANSITO", "CUMPRIDOR", "NA_TRINCHEIRA", "RESIGNADO"];
  return `<div class="pmap">${order.map((k) => { const p = S.meta.profiles[k]; const t = p.key.map((x, i) => `${["CO", "CN", "EN"][i]} ${x ? "↑" : "↓"}`).join(" ");
    return `<div class="${k === code ? "on" : ""}"><b>${esc(p.name)}</b><span class="tiny">${t}</span></div>`; }).join("")}</div>
    <p class="tiny muted" style="margin-top:8px">CO = Comprometimento · CN = Consentimento · EN = Entrincheiramento · ↑ alto · ↓ baixo</p>`;
}

/* ─── Relatório individual ──────────────────────────────────── */
async function viewReport(uid) {
  const d = await api("/api/results/" + uid);
  const per = d.person;
  if (!d.result) {
    app().innerHTML = `<h1>${per.is_self ? "Meu resultado" : esc(per.name)}</h1><div class="card"><p>Ainda não há respostas concluídas${per.is_self ? "" : " desta pessoa"}.</p><a class="btn" href="#/inicio">Voltar</a></div>`;
    return;
  }
  const r = d.result, p = d.profile, first = per.name.split(" ")[0];
  const glyph = BONDS.map((b, i) => `<span class="${p.key[i] ? "on" : ""}" title="${S.meta.bonds[b].name} ${p.key[i] ? "alto" : "baixo"}">${b}</span>`).join("");
  const border = r.borderline.length ? `<div class="callout small" style="margin-top:12px"><b>Zona de fronteira:</b> ${r.borderline.map((b) => S.meta.bonds[b].name).join(", ")} ficou próximo do ponto de corte. Leia também o perfil vizinho e converse sobre isso, porque pequenas mudanças de contexto podem alterar a classificação.</div>` : "";
  const els = Object.values(r.elements);
  const hist = d.history.length > 1 ? `<div class="card"><h3>Evolução</h3><div class="tablewrap"><table><tr><th>Coleta</th><th>Data</th><th>Perfil</th>${BONDS.map((b) => `<th>${S.meta.bonds[b].name}</th>`).join("")}</tr>
    ${d.history.map((h) => `<tr><td>${esc(h.campaign)}</td><td>${fdate(h.completed_at)}</td><td>${profileChip(h.profile)}</td>${BONDS.map((b) => `<td class="mono">${fmt(h.bonds[b])}</td>`).join("")}</tr>`).join("")}</table></div></div>` : "";
  app().innerHTML = `
    <div class="row between noprint" style="margin-bottom:14px"><a href="${per.is_self ? "#/inicio" : "#/time"}" class="small">← Voltar</a><button class="ghost sm" onclick="print()">Imprimir ou salvar em PDF</button></div>
    <div class="hero"><div class="glyph">${glyph}</div><div class="eyebrow">${per.is_self ? "Seu perfil de vínculo" : "Perfil de vínculo de " + esc(per.name)} · ${esc(d.campaign)} · ${fdate(d.completed_at)}</div>
      <h1>${esc(p.name)}</h1><div class="tag">${esc(p.tagline)}</div><p class="sum">${esc(p.summary)}</p></div>
    <div class="grid g2">
      <div class="card"><h3>Força de cada vínculo</h3><p class="small muted">Médias de 1 a 6. Os três vínculos coexistem: a combinação entre eles define o perfil.</p>${bondBars(r.bonds, r.subs, r.cutoff || S.meta.cutoff)}${border}</div>
      <div class="card"><h3>Onde o perfil se encaixa</h3><p class="small muted">Os oito padrões possíveis da combinação alto/baixo dos três vínculos.</p>${profileMap(r.profile)}</div>
    </div>
    <div class="card"><h3>Níveis da cultura a partir do vínculo</h3>
      <p class="small muted">Por qual vínculo cada nível da cultura chega até ${per.is_self ? "você" : esc(first)}. A barra mostra o peso de cada vínculo nas escolhas, considerando a força do elemento. Níveis de Schein (2009): do mais visível (artefatos) ao mais profundo (pressupostos).</p>
      ${levelsBlock(r.levels)}
      <h4 style="margin-top:22px">O que isso revela</h4><ul class="list">${d.reading.map((t) => `<li>${esc(t)}</li>`).join("")}</ul></div>
    <div class="card"><h3>Elemento por elemento</h3><div class="tablewrap"><table><tr><th>Nível</th><th>Elemento</th><th>Chega principalmente por</th><th>Depois</th><th>Força</th></tr>
      ${els.sort((a, b) => LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level)).map((e) => `<tr><td class="small muted">${S.meta.levels[e.level].name}</td><td><b>${esc(e.name)}</b></td>
      <td><span class="chip"><span class="dot" style="background:${BCOL[e.via]}"></span>${S.meta.bonds[e.via].name}</span></td>
      <td class="small">${S.meta.bonds[e.order[1]].name}</td><td class="small">${S.meta.presence_labels[e.presence - 1]}</td></tr>`).join("")}</table></div></div>
    <div class="grid g2">
      <div class="card"><h3>Forças deste padrão</h3><ul class="list">${p.strengths.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="card"><h3>Pontos de atenção</h3><ul class="list">${p.risks.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
    </div>
    <div class="grid g2">
      <div class="card" style="border-top:5px solid var(--mata)"><h3>${per.is_self ? "Seus próximos passos" : "Próximos passos para " + esc(first)}</h3><ul class="list">${p.next_steps.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="card" style="border-top:5px solid var(--sol)"><h3>Para a liderança: como liderar ${per.is_self ? "este perfil" : esc(first)}</h3><ul class="list">${p.manager.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
    </div>
    ${hist}
    <p class="tiny muted">Este diagnóstico descreve um momento da relação entre pessoa e organização. Não é um rótulo permanente nem uma avaliação de desempenho. Instrumento Ungari de Vínculos e Cultura, baseado em Ungari (2019), Silva (2013), Rodrigues e Bastos (2012), Bastos e Aguiar (2015), Freitas (2007) e Schein (2009).</p>`;
}

/* ─── Agregados reutilizáveis ───────────────────────────────── */
function profileDist(agg, total) {
  const order = ["PROTAGONISTA", "GUARDIAO", "ENRAIZADO", "ANCORA", "CUMPRIDOR", "RESIGNADO", "NA_TRINCHEIRA", "EM_TRANSITO"];
  const max = Math.max(...Object.values(agg.profiles || { x: 1 }));
  return order.map((k) => { const n = agg.profiles[k] || 0; const p = S.meta.profiles[k];
    return `<div class="row" style="gap:10px;margin:6px 0"><div style="width:120px" class="small"><b>${esc(p.name)}</b></div>
      <div style="flex:1;background:#f2f0ea;border-radius:6px;height:16px"><div style="height:100%;width:${(n / max) * 100}%;background:var(--mata);border-radius:6px" title="${n} pessoas"></div></div>
      <div class="small mono" style="width:70px;text-align:right">${n} · ${fmt((n / total) * 100, 0)}%</div></div>`; }).join("");
}
function elementHeat(agg) {
  const els = Object.entries(agg.elements || {}).sort((a, b) => LEVELS.indexOf(a[1].level) - LEVELS.indexOf(b[1].level));
  const cell = (n, tot, b) => { const pct = tot ? n / tot : 0;
    return `<td class="c" style="background:${BCOL[b]}${Math.round(pct * 200 + 20).toString(16).padStart(2, "0")};color:${pct > 0.55 ? "#fff" : "var(--carvao)"}">${fmt(pct * 100, 0)}%</td>`; };
  return `<div class="tablewrap"><table class="heat"><tr><th>Nível</th><th>Elemento</th>${BONDS.map((b) => `<th style="text-align:center">${S.meta.bonds[b].name}</th>`).join("")}<th>Força</th></tr>
    ${els.map(([, e]) => { const t = e.via.CO + e.via.CN + e.via.EN; return `<tr><td class="small muted">${S.meta.levels[e.level].name}</td><td><b>${esc(e.name)}</b></td>${BONDS.map((b) => cell(e.via[b], t, b)).join("")}<td class="small mono">${fmt(e.presence, 0)}%</td></tr>`; }).join("")}
    </table></div><p class="tiny muted">Percentual de pessoas para quem o elemento chega principalmente por cada vínculo.</p>`;
}
function aggSummary(agg, label) {
  return `<div class="grid g3">
    <div class="card"><div class="small muted">Perfil predominante</div><div style="margin:8px 0">${profileChip(agg.dominant)}</div><div class="small muted">Perfil da média: ${esc(S.meta.profiles[agg.mean_profile].name)}</div></div>
    <div class="card"><div class="small muted">Respondentes</div><div class="kpi">${agg.n}</div></div>
    <div class="card"><div class="small muted">Via cultural dominante</div><div class="kpi" style="font-size:1.4rem">${S.meta.bonds[BONDS.reduce((a, b) => (agg.culture_share[a] >= agg.culture_share[b] ? a : b))].name}</div></div></div>
    <div class="grid g2"><div class="card"><h3>Vínculos médios ${label}</h3>${bondBars(agg.bonds)}</div>
    <div class="card"><h3>Distribuição de perfis</h3>${profileDist(agg, agg.n)}</div></div>
    <div class="card"><h3>Níveis da cultura a partir do vínculo</h3>${levelsBlock(agg.levels)}</div>
    <div class="card"><h3>Elementos da cultura</h3>${elementHeat(agg)}</div>`;
}
function chart(canvas, cfg) {
  Chart.defaults.font.family = "Figtree"; Chart.defaults.color = "#5C6B63";
  const c = new Chart(canvas, cfg); S.charts.push(c); return c;
}

/* ─── Time (gestor e master) ────────────────────────────────── */
async function viewTeam() {
  const d = await api("/api/team" + cq());
  const ppl = d.people, withRes = ppl.filter((p) => p.bonds);
  const isMaster = S.me.role === "master";
  if (!ppl.length) { app().innerHTML = `<h1>Meu time</h1><div class="card"><p>Nenhuma pessoa vinculada a você ainda.</p></div>`; return; }
  let selected = new Set(withRes.filter((p) => isMaster || p.direct).slice(0, 8).map((p) => p.id));
  let filterArea = "";
  const areas = [...new Set(ppl.map((p) => p.area).filter(Boolean))];
  app().innerHTML = `<h1>${isMaster ? "Pessoas e times" : "Meu time"}</h1>
    <p class="muted">${ppl.length} pessoas · ${withRes.length} com resultado. Selecione pessoas para comparar.</p>
    ${d.aggregate.n ? `<div id="aggTeam"></div>` : ""}
    <div class="grid" style="grid-template-columns:320px 1fr">
      <div class="card"><div class="row between"><h3 style="margin:0">Pessoas</h3><div class="row" style="gap:6px"><button class="ghost sm" id="all">Todas</button><button class="ghost sm" id="none">Nenhuma</button></div></div>
        ${areas.length > 1 ? `<select id="fArea" style="margin:10px 0"><option value="">Todas as áreas</option>${areas.map((a) => `<option>${esc(a)}</option>`).join("")}</select>` : ""}
        <div class="personlist" id="plist"></div></div>
      <div><div class="card"><h3>Comparação dos vínculos</h3>${bondLegend()}<div class="chartbox"><canvas id="cmp"></canvas></div></div>
        <div class="card"><h3>Mapa de vínculos</h3><p class="small muted">Horizontal: Comprometimento. Vertical: Entrincheiramento. Círculo cheio: Consentimento alto. Círculo vazio: Consentimento baixo. As linhas marcam o ponto de corte.</p><div class="chartbox"><canvas id="map"></canvas></div></div>
        <div class="card"><h3>Selecionados</h3><div id="seltable" class="tablewrap"></div></div></div>
    </div>`;
  if (window.innerWidth < 860) app().querySelector(".grid[style]").style.gridTemplateColumns = "1fr";
  const cutPlugin = { id: "cut", afterDraw(c) { if (c.canvas.id !== "map") return; const { ctx, scales: { x, y } } = c; ctx.save(); ctx.strokeStyle = "rgba(26,26,26,.55)"; ctx.lineWidth = 1.5; ctx.setLineDash([5, 4]);
    ctx.beginPath(); ctx.moveTo(x.getPixelForValue(S.meta.cutoff || 4), y.top); ctx.lineTo(x.getPixelForValue(S.meta.cutoff || 4), y.bottom); ctx.moveTo(x.left, y.getPixelForValue(S.meta.cutoff || 4)); ctx.lineTo(x.right, y.getPixelForValue(S.meta.cutoff || 4)); ctx.stroke(); ctx.restore(); } };
  const cmp = chart($("#cmp"), { type: "bar", data: { labels: [], datasets: BONDS.map((b) => ({ label: S.meta.bonds[b].name, data: [], backgroundColor: BCOL[b], borderRadius: 4, borderSkipped: "bottom", maxBarThickness: 22 })) },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.raw)}` } } }, scales: { y: { min: 1, max: 6, grid: { color: "#eee" } }, x: { grid: { display: false } } } } });
  const map = chart($("#map"), { type: "scatter", plugins: [cutPlugin], data: { datasets: [
      { label: "Consentimento alto", data: [], backgroundColor: BCOL.CN, borderColor: "#fff", borderWidth: 2, pointRadius: 8, pointHoverRadius: 10 },
      { label: "Consentimento baixo", data: [], backgroundColor: "#fff", borderColor: BCOL.CN, borderWidth: 2, pointRadius: 8, pointHoverRadius: 10 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: (c) => `${c.raw.name}: CO ${fmt(c.raw.x)} · EN ${fmt(c.raw.y)} · CN ${fmt(c.raw.cn)}` } } },
      scales: { x: { min: 1, max: 6, title: { display: true, text: "Comprometimento" } }, y: { min: 1, max: 6, title: { display: true, text: "Entrincheiramento" } } } } });
  function draw() {
    const vis = ppl.filter((p) => !filterArea || p.area === filterArea);
    $("#plist").innerHTML = vis.map((p) => `<label><input type="checkbox" data-id="${p.id}" ${selected.has(p.id) ? "checked" : ""} ${p.bonds ? "" : "disabled"}>
      <span style="flex:1">${esc(p.name)}<span class="tiny muted" style="display:block">${esc(p.area || "")}${p.direct ? " · direto" : ""}</span></span>${p.profile ? profileChip(p.profile) : `<span class="pill">pendente</span>`}</label>`).join("");
    $("#plist").querySelectorAll("input").forEach((i) => (i.onchange = () => { i.checked ? selected.add(+i.dataset.id) : selected.delete(+i.dataset.id); draw(); }));
    const sel = withRes.filter((p) => selected.has(p.id));
    cmp.data.labels = sel.map((p) => p.name.split(" ")[0] + " " + (p.name.split(" ")[1] || "").charAt(0) + ".");
    BONDS.forEach((b, i) => (cmp.data.datasets[i].data = sel.map((p) => p.bonds[b])));
    cmp.update();
    const pts = (hi) => sel.filter((p) => (p.bonds.CN >= (S.meta.cutoff || 4)) === hi).map((p) => ({ x: p.bonds.CO, y: p.bonds.EN, cn: p.bonds.CN, name: p.name }));
    map.data.datasets[0].data = pts(true); map.data.datasets[1].data = pts(false); map.update();
    $("#seltable").innerHTML = sel.length ? `<table><tr><th>Pessoa</th><th>Perfil</th>${BONDS.map((b) => `<th>${b}</th>`).join("")}<th>Via cultural</th><th></th></tr>
      ${sel.map((p) => { const v = BONDS.reduce((a, b) => (p.culture_share[a] >= p.culture_share[b] ? a : b)); return `<tr><td><b>${esc(p.name)}</b><div class="tiny muted">${esc(p.area || "")}</div></td><td>${profileChip(p.profile)}</td>
      ${BONDS.map((b) => `<td class="mono">${fmt(p.bonds[b])}</td>`).join("")}<td class="small">${S.meta.bonds[v].name}</td><td><a href="#/resultado/${p.id}" class="small">Relatório</a></td></tr>`; }).join("")}</table>` : `<p class="muted">Selecione pessoas na lista.</p>`;
  }
  $("#all").onclick = () => { ppl.filter((p) => p.bonds && (!filterArea || p.area === filterArea)).forEach((p) => selected.add(p.id)); draw(); };
  $("#none").onclick = () => { selected.clear(); draw(); };
  if ($("#fArea")) $("#fArea").onchange = (e) => { filterArea = e.target.value; draw(); };
  if ($("#aggTeam")) $("#aggTeam").innerHTML = `<h2 style="margin-top:8px">Visão consolidada ${isMaster ? "da empresa" : "do time"}</h2>` + aggSummary(d.aggregate, isMaster ? "da empresa" : "do time") + `<h2>Comparar pessoas</h2>`;
  draw();
}

/* ─── Áreas e empresa (admin e master) ──────────────────────── */
async function viewOrg() {
  let campaign = "";
  async function load() {
    killCharts();
    const d = await api("/api/org" + cq({ campaign_id: campaign }));
    const vis = d.areas.filter((a) => a.aggregate && a.aggregate.n);
    let chosen = new Set(vis.map((a) => a.name));
    app().innerHTML = `<div class="row between"><h1>${esc(d.company.name)}</h1>
      <select id="camp" style="width:auto"><option value="">Resultado mais recente de cada pessoa</option>${d.campaigns.map((c) => `<option value="${c.id}" ${String(c.id) === campaign ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></div>
      <div class="grid g3"><div class="card"><div class="small muted">Pessoas cadastradas</div><div class="kpi">${d.members}</div></div>
      <div class="card"><div class="small muted">Com resultado</div><div class="kpi">${d.responded} <small>${fmt(d.members ? (d.responded / d.members) * 100 : 0, 0)}% de adesão</small></div></div>
      <div class="card"><div class="small muted">Áreas</div><div class="kpi">${d.areas.filter((a) => a.id).length}</div></div></div>
      ${d.aggregate.suppressed ? `<div class="card"><p>São necessárias pelo menos ${S.meta.min_group} respostas para exibir a visão da empresa.</p></div>` : d.aggregate.n ? `<h2>Empresa</h2>` + aggSummary(d.aggregate, "da empresa") : ""}
      <h2>Comparar áreas</h2>
      <div class="card"><div class="row" id="achips">${vis.map((a) => `<label class="chip" style="cursor:pointer"><input type="checkbox" checked data-a="${esc(a.name)}" style="width:auto"> ${esc(a.name)} <span class="muted">(${a.aggregate.n})</span></label>`).join("")}</div>
        ${d.areas.filter((a) => a.suppressed).length ? `<p class="tiny muted" style="margin-top:10px">Áreas com menos de ${S.meta.min_group} respostas ficam ocultas para preservar o anonimato: ${d.areas.filter((a) => a.suppressed).map((a) => esc(a.name)).join(", ")}.</p>` : ""}
        ${bondLegend()}<div class="chartbox"><canvas id="ac"></canvas></div></div>
      <div class="card"><h3>Perfis por área</h3><div class="tablewrap" id="ptab"></div></div>
      <div class="card"><h3>Níveis da cultura por área</h3><div id="ltab"></div></div>`;
    $("#camp").onchange = (e) => { campaign = e.target.value; load(); };
    const ac = chart($("#ac"), { type: "bar", data: { labels: [], datasets: BONDS.map((b) => ({ label: S.meta.bonds[b].name, data: [], backgroundColor: BCOL[b], borderRadius: 4, maxBarThickness: 26 })) },
      options: { maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.raw)}` } } }, scales: { y: { min: 1, max: 6 }, x: { grid: { display: false } } } } });
    const order = ["PROTAGONISTA", "GUARDIAO", "ENRAIZADO", "ANCORA", "CUMPRIDOR", "RESIGNADO", "NA_TRINCHEIRA", "EM_TRANSITO"];
    function draw() {
      const sel = vis.filter((a) => chosen.has(a.name));
      ac.data.labels = sel.map((a) => a.name); BONDS.forEach((b, i) => (ac.data.datasets[i].data = sel.map((a) => a.aggregate.bonds[b]))); ac.update();
      $("#ptab").innerHTML = `<table><tr><th>Área</th>${order.map((k) => `<th style="text-align:center">${esc(S.meta.profiles[k].name)}</th>`).join("")}<th>Predominante</th></tr>
        ${sel.map((a) => `<tr><td><b>${esc(a.name)}</b></td>${order.map((k) => { const n = a.aggregate.profiles[k] || 0, pct = n / a.aggregate.n;
          return `<td class="c mono" style="text-align:center;background:rgba(45,122,90,${pct * 0.85});color:${pct > 0.45 ? "#fff" : "inherit"}">${n || ""}</td>`; }).join("")}<td>${profileChip(a.aggregate.dominant)}</td></tr>`).join("")}</table>`;
      $("#ltab").innerHTML = bondLegend() + sel.map((a) => `<h4 style="margin:18px 0 4px">${esc(a.name)}</h4>` + LEVELS.filter((l) => a.aggregate.levels[l]).map((l) => `<div class="levelrow"><div class="small"><b>${S.meta.levels[l].name}</b></div>${stack(a.aggregate.levels[l].share)}<div class="small mono">força ${fmt(a.aggregate.levels[l].intensity, 0)}%</div></div>`).join("")).join("");
    }
    app().querySelectorAll("[data-a]").forEach((i) => (i.onchange = () => { i.checked ? chosen.add(i.dataset.a) : chosen.delete(i.dataset.a); draw(); }));
    draw();
  }
  await load();
}

/* ─── Cadastro de pessoas e áreas ───────────────────────────── */
function modal(html) {
  const m = document.createElement("div"); m.className = "modal"; m.innerHTML = `<div class="card">${html}</div>`;
  m.onclick = (e) => { if (e.target === m) m.remove(); }; document.body.appendChild(m); return m;
}
async function viewPeople() {
  const [ppl, areas] = await Promise.all([api("/api/people" + cq()), api("/api/areas" + cq())]);
  const roles = S.meta.roles;
  app().innerHTML = `<div class="row between"><h1>Cadastro</h1><div class="row"><button class="ghost" id="bulk">Importar lista</button><button id="add">Adicionar pessoa</button></div></div>
    <div class="card"><div class="row between"><h3 style="margin:0">Áreas</h3><form id="af" class="row"><input id="an" placeholder="Nova área" style="width:220px" required><button class="sm">Adicionar</button></form></div>
      <div class="row" style="margin-top:12px">${areas.map((a) => `<span class="chip">${esc(a.name)} <span class="muted">${a.people}</span> <button class="ghost sm" data-delarea="${a.id}" aria-label="Excluir área" style="padding:0 6px;border:0">×</button></span>`).join("") || `<span class="muted small">Nenhuma área.</span>`}</div></div>
    <div class="card"><input id="q" placeholder="Buscar por nome, e-mail ou área" style="margin-bottom:12px"><div class="tablewrap"><table><thead><tr><th>Nome</th><th>Acesso</th><th>Área</th><th>Gestor(a)</th><th>Status</th><th></th></tr></thead><tbody id="tb"></tbody></table></div></div>`;
  const tb = $("#tb");
  function rows(f = "") {
    const fl = f.toLowerCase();
    tb.innerHTML = ppl.filter((p) => !fl || [p.name, p.email, p.area].join(" ").toLowerCase().includes(fl)).map((p) => `<tr>
      <td><b>${esc(p.name)}</b><div class="tiny muted">${esc(p.email)}${p.job_title ? " · " + esc(p.job_title) : ""}</div></td>
      <td>${esc(roles[p.role])}</td><td>${esc(p.area || "–")}</td><td>${esc(p.manager || "–")}</td>
      <td>${!p.active ? `<span class="pill">inativo</span>` : p.pending_invite ? `<span class="pill warn">convite pendente</span>` : `<span class="pill ok">ativo</span>`} ${p.answered ? `<span class="pill ok">${p.answered} resp.</span>` : ""}</td>
      <td class="row" style="gap:6px;flex-wrap:nowrap"><button class="ghost sm" data-edit="${p.id}">Editar</button><button class="ghost sm" data-inv="${p.id}">${p.pending_invite ? "Link" : "Reenviar acesso"}</button></td></tr>`).join("");
    tb.querySelectorAll("[data-edit]").forEach((b) => (b.onclick = () => edit(ppl.find((p) => p.id === +b.dataset.edit))));
    tb.querySelectorAll("[data-inv]").forEach((b) => (b.onclick = async () => {
      const p = ppl.find((x) => x.id === +b.dataset.inv);
      if (p.pending_invite && p.invite_link) return copy(p.invite_link);
      if (!confirm(`Gerar novo link de acesso para ${p.name}? A senha atual deixa de valer.`)) return;
      const r = await api(`/api/people/${p.id}/invite`, { method: "POST" });
      r.email_sent ? toast("Convite enviado por e-mail.") : copy(r.invite_link);
    }));
  }
  rows(); $("#q").oninput = (e) => rows(e.target.value);
  $("#af").onsubmit = async (e) => { e.preventDefault(); await api("/api/areas", { method: "POST", body: { name: $("#an").value, company_id: S.companyId } }); viewPeople(); };
  app().querySelectorAll("[data-delarea]").forEach((b) => (b.onclick = async () => { if (!confirm("Excluir esta área? As pessoas ficam sem área.")) return; await api("/api/areas/" + b.dataset.delarea, { method: "DELETE" }); viewPeople(); }));
  $("#add").onclick = () => edit(null);
  function edit(p) {
    const roleOpts = Object.entries(roles).filter(([k]) => k !== "master" || S.me.role === "master");
    const m = modal(`<h2>${p ? "Editar pessoa" : "Adicionar pessoa"}</h2><form id="pf">
      <div class="field"><label>Nome</label><input name="name" required value="${esc(p?.name)}"></div>
      <div class="field"><label>E-mail</label><input name="email" type="email" required value="${esc(p?.email)}"></div>
      <div class="field"><label>Cargo</label><input name="job_title" value="${esc(p?.job_title)}"></div>
      <div class="grid g2" style="gap:12px"><div class="field"><label>Nível de acesso</label><select name="role">${roleOpts.map(([k, l]) => `<option value="${k}" ${(p?.role || "colaborador") === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
      <div class="field"><label>Área</label><select name="area_id"><option value="">Sem área</option>${areas.map((a) => `<option value="${a.id}" ${p?.area_id === a.id ? "selected" : ""}>${esc(a.name)}</option>`).join("")}</select></div></div>
      <div class="field"><label>Gestor(a) direto(a)</label><select name="manager_id"><option value="">Ninguém</option>${ppl.filter((x) => x.id !== p?.id).map((x) => `<option value="${x.id}" ${p?.manager_id === x.id ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select>
        <p class="tiny muted">Quem é gestor(a) vê o resultado das pessoas abaixo dela na hierarquia.</p></div>
      ${p ? `<label style="display:flex;gap:8px;align-items:center"><input type="checkbox" name="active" style="width:auto" ${p.active ? "checked" : ""}> Ativo</label>` : ""}
      <p class="tiny muted">Colaborador vê só o próprio resultado · Gestor vê também o time · Admin cadastra pessoas e dispara coletas · Master tem acesso total.</p>
      <p id="err" class="small" style="color:#a33"></p>
      <div class="row between"><div>${p ? `<button type="button" class="danger" id="del">Excluir pessoa</button>` : ""}</div><div class="row"><button type="button" class="ghost" id="cancel">Cancelar</button><button>Salvar</button></div></div></form>`);
    $("#cancel", m).onclick = () => m.remove();
    if (p) $("#del", m).onclick = async () => { if (!confirm(`Excluir ${p.name} e todas as respostas dela? Esta ação não pode ser desfeita.`)) return; await api("/api/people/" + p.id, { method: "DELETE" }); m.remove(); viewPeople(); };
    $("#pf", m).onsubmit = async (e) => {
      e.preventDefault(); const f = new FormData(e.target);
      const body = { name: f.get("name"), email: f.get("email"), job_title: f.get("job_title") || null, role: f.get("role"),
        area_id: f.get("area_id") ? +f.get("area_id") : null, manager_id: f.get("manager_id") ? +f.get("manager_id") : null, active: p ? f.get("active") === "on" : true, company_id: S.companyId ? +S.companyId : null };
      try {
        if (p) await api("/api/people/" + p.id, { method: "PUT", body });
        else { const r = await api("/api/people", { method: "POST", body }); copy(r.invite_link); }
        m.remove(); viewPeople();
      } catch (er) { $("#err", m).textContent = er.message; }
    };
  }
  $("#bulk").onclick = () => {
    const m = modal(`<h2>Importar lista</h2><p class="small muted">Cole uma pessoa por linha no formato: <b>Nome; e-mail; área; e-mail do gestor; nível</b>. Área, gestor e nível são opcionais (nível: colaborador, gestor ou admin). Áreas novas são criadas automaticamente. Importe primeiro os gestores.</p>
      <textarea id="bt" style="min-height:180px" placeholder="Maria Silva; maria@empresa.com; Comercial; joao@empresa.com; colaborador"></textarea>
      <p id="bo" class="small"></p><div class="row" style="justify-content:flex-end"><button class="ghost" id="bc">Fechar</button><button id="bg">Importar</button></div>`);
    $("#bc", m).onclick = () => { m.remove(); viewPeople(); };
    $("#bg", m).onclick = async () => {
      const lines = $("#bt", m).value.split("\n").map((l) => l.trim()).filter(Boolean);
      let ok = 0; const errs = []; const areaMap = Object.fromEntries(areas.map((a) => [a.name.toLowerCase(), a.id]));
      const emailMap = Object.fromEntries(ppl.map((p) => [p.email.toLowerCase(), p.id]));
      for (const l of lines) {
        const [name, email, area, mgr, role] = l.split(/[;\t]/).map((s) => (s || "").trim());
        try {
          let area_id = null;
          if (area) { area_id = areaMap[area.toLowerCase()]; if (!area_id) { area_id = (await api("/api/areas", { method: "POST", body: { name: area, company_id: S.companyId } })).id; areaMap[area.toLowerCase()] = area_id; } }
          const r = await api("/api/people", { method: "POST", body: { name, email, area_id, manager_id: mgr ? emailMap[mgr.toLowerCase()] || null : null, role: ["gestor", "admin"].includes(role) ? role : "colaborador", company_id: S.companyId ? +S.companyId : null } });
          emailMap[email.toLowerCase()] = r.id; ok++;
        } catch (e) { errs.push(`${name || l}: ${e.message}`); }
      }
      $("#bo", m).innerHTML = `${ok} pessoas importadas.${errs.length ? "<br>" + errs.map(esc).join("<br>") : ""}`;
    };
  };
}

/* ─── Coletas ───────────────────────────────────────────────── */
async function viewCampaigns() {
  const [cs, areas, ppl] = await Promise.all([api("/api/campaigns" + cq()), api("/api/areas" + cq()), api("/api/people" + cq())]);
  app().innerHTML = `<div class="row between"><h1>Coletas</h1><button id="new">Disparar nova coleta</button></div>
    <p class="muted">Uma coleta envia o questionário para um grupo de pessoas. Cada coleta usa a versão do questionário vigente no momento do disparo.</p>
    <div class="card tablewrap"><table><tr><th>Coleta</th><th>Criada em</th><th>Prazo</th><th>Respostas</th><th>Status</th><th></th></tr>
    ${cs.map((c) => `<tr><td><b>${esc(c.name)}</b></td><td>${fdate(c.created_at)}</td><td>${c.deadline ? esc(c.deadline.split("-").reverse().join("/")) : "–"}</td>
      <td><div class="row" style="gap:8px"><div style="width:90px;height:8px;background:#eee;border-radius:9px"><div style="height:100%;width:${c.total ? (c.done / c.total) * 100 : 0}%;background:var(--mata);border-radius:9px"></div></div><span class="small mono">${c.done}/${c.total}</span></div></td>
      <td><span class="pill ${c.status === "aberta" ? "ok" : ""}">${c.status}</span></td><td><a href="#/coletas/${c.id}" class="small">Acompanhar</a></td></tr>`).join("") || `<tr><td colspan="6" class="muted">Nenhuma coleta ainda.</td></tr>`}</table></div>`;
  $("#new").onclick = () => {
    const m = modal(`<h2>Disparar coleta</h2><form id="cf">
      <div class="field"><label>Nome da coleta</label><input name="name" required placeholder="Ex.: Ciclo 2026.2"></div>
      <div class="field"><label>Prazo (opcional)</label><input name="deadline" type="date"></div>
      <div class="field"><label>Quem responde</label><select name="target"><option value="all">Todas as pessoas ativas</option><option value="areas">Áreas específicas</option><option value="people">Pessoas específicas</option></select></div>
      <div id="tA" class="field hidden">${areas.map((a) => `<label style="font-weight:500;display:flex;gap:8px"><input type="checkbox" value="${a.id}" style="width:auto"> ${esc(a.name)}</label>`).join("")}</div>
      <div id="tP" class="field hidden personlist" style="max-height:220px">${ppl.filter((p) => p.active).map((p) => `<label><input type="checkbox" value="${p.id}"> ${esc(p.name)} <span class="tiny muted">${esc(p.area || "")}</span></label>`).join("")}</div>
      <p class="tiny muted">Se o servidor tiver e-mail configurado, cada pessoa recebe o aviso. Caso contrário, você recebe os links para enviar como preferir.</p>
      <p id="err" class="small" style="color:#a33"></p><div class="row" style="justify-content:flex-end"><button type="button" class="ghost" id="cc">Cancelar</button><button>Disparar</button></div></form>`);
    const tsel = $("[name=target]", m);
    tsel.onchange = () => { $("#tA", m).classList.toggle("hidden", tsel.value !== "areas"); $("#tP", m).classList.toggle("hidden", tsel.value !== "people"); };
    $("#cc", m).onclick = () => m.remove();
    $("#cf", m).onsubmit = async (e) => {
      e.preventDefault(); const f = new FormData(e.target);
      const ids = (id) => [...m.querySelectorAll(`#${id} input:checked`)].map((i) => +i.value);
      try {
        const r = await api("/api/campaigns", { method: "POST", body: { name: f.get("name"), deadline: f.get("deadline") || null, company_id: S.companyId ? +S.companyId : null,
          area_ids: tsel.value === "areas" ? ids("tA") : null, user_ids: tsel.value === "people" ? ids("tP") : null } });
        m.remove(); toast(`Coleta disparada para ${r.count} pessoas${r.emails_sent ? `, ${r.emails_sent} e-mails enviados` : ""}.`);
        location.hash = "#/coletas/" + r.id;
      } catch (er) { $("#err", m).textContent = er.message; }
    };
  };
}
async function viewCampaign(cid) {
  const d = await api("/api/campaigns/" + cid);
  const c = d.campaign, done = d.assignments.filter((a) => a.status === "concluida").length;
  const pending = d.assignments.filter((a) => a.status !== "concluida");
  const msg = (a) => `Olá, ${a.name.split(" ")[0]}! Você foi convidado(a) para o Diagnóstico de Vínculos e Cultura (${c.name}). Leva cerca de 7 minutos. Acesse: ${a.link}`;
  app().innerHTML = `<a href="#/coletas" class="small">← Coletas</a><div class="row between"><h1>${esc(c.name)}</h1>
    <div class="row"><button class="ghost" id="copyAll">Copiar mensagens dos pendentes</button><button class="ghost" id="tog">${c.status === "aberta" ? "Encerrar coleta" : "Reabrir coleta"}</button>${S.me.role === "master" ? `<button class="danger" id="delc">Excluir</button>` : ""}</div></div>
    <div class="grid g3"><div class="card"><div class="small muted">Respostas</div><div class="kpi">${done}/${d.assignments.length}</div></div>
    <div class="card"><div class="small muted">Adesão</div><div class="kpi">${fmt(d.assignments.length ? (done / d.assignments.length) * 100 : 0, 0)}%</div></div>
    <div class="card"><div class="small muted">Status</div><div class="kpi" style="font-size:1.4rem">${esc(c.status)}</div></div></div>
    <div class="card tablewrap"><table><tr><th>Pessoa</th><th>Área</th><th>Status</th><th>Concluído em</th><th></th></tr>
    ${d.assignments.map((a) => `<tr><td><b>${esc(a.name)}</b><div class="tiny muted">${esc(a.email)}</div></td><td>${esc(a.area || "–")}</td>
      <td><span class="pill ${a.status === "concluida" ? "ok" : "warn"}">${a.status === "concluida" ? "respondido" : "pendente"}</span></td><td>${fdate(a.completed_at)}</td>
      <td class="row" style="gap:6px;flex-wrap:nowrap">${a.status !== "concluida" ? `<button class="ghost sm" data-copy="${a.id}">Copiar link</button><a class="btn sm ghost" style="background:#fff;color:var(--floresta);border:1px solid var(--nevoa)" href="mailto:${esc(a.email)}?subject=${encodeURIComponent("Diagnóstico de Vínculos: " + c.name)}&body=${encodeURIComponent(msg(a))}">E-mail</a>` : ""}</td></tr>`).join("")}</table></div>`;
  app().querySelectorAll("[data-copy]").forEach((b) => (b.onclick = () => copy(d.assignments.find((a) => a.id === +b.dataset.copy).link)));
  $("#copyAll").onclick = () => copy(pending.map(msg).join("\n\n"));
  $("#tog").onclick = async () => { await api(`/api/campaigns/${cid}/status?status=${c.status === "aberta" ? "encerrada" : "aberta"}`, { method: "POST" }); viewCampaign(cid); };
  if ($("#delc")) $("#delc").onclick = async () => { if (!confirm("Excluir esta coleta e todas as respostas dela? Esta ação não pode ser desfeita.")) return; await api("/api/campaigns/" + cid, { method: "DELETE" }); location.hash = "#/coletas"; };
}

/* ─── Questionário: edição (Master) ─────────────────────────── */
async function viewInstrument() {
  const d = await api("/api/instrument");
  let data = JSON.parse(JSON.stringify(d.active.data));
  function render() {
    app().innerHTML = `<div class="row between"><h1>Questionário</h1><div class="row"><button class="ghost" id="reset">Restaurar versão original</button><button id="save">Publicar nova versão</button></div></div>
      <p class="muted">Versão ativa nº ${d.active.id}${d.active.note ? " · " + esc(d.active.note) : ""}. Mudanças valem para coletas disparadas depois da publicação. Coletas antigas continuam com a versão delas.</p>
      <div class="card"><h3>Abertura e corte</h3>
        <div class="field"><label>Título</label><input id="i_title" value="${esc(data.title)}"></div>
        <div class="field"><label>Texto de abertura</label><textarea id="i_intro">${esc(data.intro)}</textarea></div>
        <div class="grid g2" style="gap:12px"><div class="field"><label>Ponto de corte alto/baixo (média de 1 a 6)</label><input id="i_high" type="number" step="0.05" min="2" max="5" value="${data.cutoffs.high}"></div>
        <div class="field"><label>Margem da zona de fronteira</label><input id="i_border" type="number" step="0.05" min="0" max="1" value="${data.cutoffs.border}"></div></div></div>
      <div class="card"><h3>Parte 1 · Afirmativas de vínculo (escala 1 a 6)</h3><p class="small muted">Mínimo de 2 itens por vínculo. Recomendado: 4, para manter a confiabilidade. Itens invertidos são pontuados ao contrário.</p>
        ${["CO", "CN", "EN"].map((b) => `<h4 style="margin-top:18px;color:${BCOL[b]}">${S.meta.bonds[b].name}</h4>` + data.likert.map((it, i) => it.bond !== b ? "" : `
          <div class="row" style="align-items:flex-start;margin-bottom:8px;flex-wrap:nowrap"><span class="pill" style="margin-top:10px">${esc(it.id)}</span>
          <textarea data-lt="${i}" style="min-height:44px;flex:1">${esc(it.text)}</textarea>
          <div style="width:170px"><input data-ls="${i}" value="${esc(it.sub)}" title="Subdimensão" placeholder="Subdimensão"><label class="tiny" style="display:flex;gap:6px;margin-top:4px;font-weight:500"><input type="checkbox" data-lr="${i}" style="width:auto" ${it.reverse ? "checked" : ""}> invertido</label></div>
          <button class="ghost sm" data-ld="${i}" aria-label="Remover" style="margin-top:6px">×</button></div>`).join("") + `<button class="ghost sm" data-add="${b}">+ Afirmativa</button>`).join("")}</div>
      <div class="card"><h3>Parte 2 · Cultura a partir do vínculo (ordenação)</h3><p class="small muted">Cada elemento tem uma frase para cada vínculo. A pessoa ordena as três.</p>
        ${data.culture.map((el, i) => `<div style="border-top:1px solid var(--line);padding-top:14px;margin-top:14px">
          <div class="grid g2" style="gap:12px"><div class="field"><label>Elemento</label><input data-cn="${i}" value="${esc(el.name)}"></div>
          <div class="field"><label>Nível de Schein</label><select data-cl="${i}">${LEVELS.map((l) => `<option value="${l}" ${el.level === l ? "selected" : ""}>${S.meta.levels[l].name}</option>`).join("")}</select></div></div>
          <div class="field"><label>Enunciado</label><input data-cp="${i}" value="${esc(el.prompt)}"></div>
          ${BONDS.map((b) => `<div class="field"><label style="color:${BCOL[b]}">Frase de ${S.meta.bonds[b].name}</label><input data-co="${i}|${b}" value="${esc(el.options[b])}"></div>`).join("")}
          <button class="ghost sm" data-cd="${i}">Remover elemento</button></div>`).join("")}
        <button class="ghost sm" id="addEl" style="margin-top:12px">+ Elemento da cultura</button></div>
      <div class="card"><h3>Versões</h3><table>${d.versions.map((v) => `<tr><td>nº ${v.id}</td><td>${esc(v.note || "")}</td><td>${fdate(v.created_at)}</td><td>${v.active ? `<span class="pill ok">ativa</span>` : ""}</td></tr>`).join("")}</table></div>`;
    const sync = () => {
      data.title = $("#i_title").value; data.intro = $("#i_intro").value;
      data.cutoffs = { high: +$("#i_high").value, border: +$("#i_border").value };
      app().querySelectorAll("[data-lt]").forEach((e) => (data.likert[e.dataset.lt].text = e.value));
      app().querySelectorAll("[data-ls]").forEach((e) => (data.likert[e.dataset.ls].sub = e.value || "Geral"));
      app().querySelectorAll("[data-lr]").forEach((e) => (data.likert[e.dataset.lr].reverse = e.checked));
      app().querySelectorAll("[data-cn]").forEach((e) => (data.culture[e.dataset.cn].name = e.value));
      app().querySelectorAll("[data-cl]").forEach((e) => (data.culture[e.dataset.cl].level = e.value));
      app().querySelectorAll("[data-cp]").forEach((e) => (data.culture[e.dataset.cp].prompt = e.value));
      app().querySelectorAll("[data-co]").forEach((e) => { const [i, b] = e.dataset.co.split("|"); data.culture[i].options[b] = e.value; });
    };
    app().querySelectorAll("[data-ld]").forEach((b) => (b.onclick = () => { sync(); data.likert.splice(+b.dataset.ld, 1); render(); }));
    app().querySelectorAll("[data-add]").forEach((b) => (b.onclick = () => { sync(); const bond = b.dataset.add; let n = 1; while (data.likert.some((x) => x.id === bond + n)) n++;
      data.likert.push({ id: bond + n, bond, sub: "Geral", reverse: false, text: "" }); render(); }));
    app().querySelectorAll("[data-cd]").forEach((b) => (b.onclick = () => { sync(); data.culture.splice(+b.dataset.cd, 1); render(); }));
    $("#addEl").onclick = () => { sync(); data.culture.push({ id: "EL" + Date.now().toString(36).toUpperCase(), level: "ART", name: "Novo elemento", prompt: "", options: { CO: "", CN: "", EN: "" } }); render(); };
    $("#reset").onclick = () => { if (confirm("Carregar a versão original no editor? Nada é publicado até você clicar em Publicar.")) { data = JSON.parse(JSON.stringify(d.default)); render(); } };
    $("#save").onclick = async () => {
      sync(); const note = prompt("Descreva rapidamente o que mudou nesta versão:", ""); if (note === null) return;
      try { await api("/api/instrument", { method: "PUT", body: { data, note } }); toast("Nova versão publicada."); viewInstrument(); } catch (e) { toast(e.message); }
    };
  }
  render();
}

/* ─── Empresas (Master) ─────────────────────────────────────── */
async function viewCompanies() {
  const cs = await api("/api/companies");
  app().innerHTML = `<h1>Empresas</h1><div class="card"><form id="nf" class="row"><input id="nn" placeholder="Nome da empresa cliente" style="flex:1" required><button>Cadastrar</button></form></div>
    <div class="card tablewrap"><table><tr><th>Empresa</th><th>Pessoas</th><th>Criada em</th><th></th></tr>
    ${cs.map((c) => `<tr><td><b>${esc(c.name)}</b></td><td>${c.people}</td><td>${fdate(c.created_at)}</td><td class="row" style="gap:6px"><button class="ghost sm" data-go="${c.id}">Abrir</button><button class="danger sm" data-del="${c.id}">Excluir</button></td></tr>`).join("")}</table></div>
    <p class="small muted">Para dar acesso de Admin a alguém do RH do cliente, abra a empresa, vá em Cadastro e crie a pessoa com nível Admin.</p>`;
  $("#nf").onsubmit = async (e) => { e.preventDefault(); const r = await api("/api/companies", { method: "POST", body: { name: $("#nn").value } }); S.companyId = r.id; await buildCompanySel(); viewCompanies(); };
  app().querySelectorAll("[data-go]").forEach((b) => (b.onclick = async () => { S.companyId = b.dataset.go; try { localStorage.setItem("uv_company", S.companyId); } catch {} await buildCompanySel(); location.hash = "#/organizacao"; }));
  app().querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
    const c = cs.find((x) => x.id === +b.dataset.del);
    if (prompt(`Isso apaga ${c.name}, todas as pessoas e respostas. Digite o nome da empresa para confirmar:`) !== c.name) return;
    await api("/api/companies/" + c.id, { method: "DELETE" }); S.companyId = null; await buildCompanySel(); viewCompanies();
  }));
}

/* ─── Conta ─────────────────────────────────────────────────── */
async function viewAccount() {
  app().innerHTML = `<h1>Minha conta</h1><div class="card" style="max-width:480px"><p><b>${esc(S.me.name)}</b><br><span class="muted">${esc(S.me.email)} · ${esc(S.me.role_label)}</span></p>
    <form id="pf"><div class="field"><label>Senha atual</label><input id="c" type="password" autocomplete="current-password" required></div>
    <div class="field"><label>Nova senha (mínimo 8 caracteres)</label><input id="n" type="password" minlength="8" autocomplete="new-password" required></div>
    <p id="err" class="small" style="color:#a33"></p><button>Trocar senha</button></form></div>`;
  $("#pf").onsubmit = async (e) => { e.preventDefault(); try { await api("/api/me/password", { method: "POST", body: { current: $("#c").value, new: $("#n").value } }); toast("Senha alterada."); e.target.reset(); } catch (er) { $("#err").textContent = er.message; } };
}
