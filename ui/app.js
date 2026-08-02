"use strict";

// ---------- Estado ----------
const state = {
  tracks: [],
  track: null,        // detalhe da pista (arrays densos)
  vehicles: [],
  vehicle: null,      // cópia editável dos parâmetros
  trajectories: [],
  trajectoryId: null,
  controlPoints: [],  // [{s, alpha}]
  lap: null,          // resposta de /api/laptime
  ghost: null,        // traçado anterior à otimização: {x, y, lapTime}
  drag: null,         // índice do ponto arrastado
  hoverPoint: null,   // índice do ponto sob o mouse
  chartHover: null,   // índice do sample sob o mouse no gráfico
};

const MARGIN = 0.5; // margem lateral (m) — meia largura de carro

// Rampa sequencial (azul, escuro→claro = lento→rápido) para colorir o traçado.
const SPEED_RAMP = ["#104281", "#184f95", "#1c5cab", "#256abf", "#2a78d6",
                    "#3987e5", "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4"];
const COLOR_V = "#3987e5";
const COLOR_GRIP = "#d95926";
const COLOR_GRID = "#2c2c2a";
const COLOR_BASELINE = "#383835";
const COLOR_MUTED = "#898781";
const COLOR_TEXT = "#c3c2b7";

// ---------- API ----------
async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.status === 204 ? null : res.json();
}

const postJSON = (path, body, method = "POST") =>
  api(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---------- Canvas / transformação ----------
const trackCanvas = document.getElementById("track-canvas");
const speedCanvas = document.getElementById("speed-canvas");
const tooltip = document.getElementById("chart-tooltip");
let view = { scale: 1, ox: 0, oy: 0, fitScale: 1 };
let pan = null; // {startX, startY, ox, oy} durante arrasto com botão direito

function setupCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.round(rect.width * dpr);
  canvas.height = Math.round(rect.height * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w: rect.width, h: rect.height };
}

function fitView() {
  const t = state.track;
  if (!t) return;
  const rect = trackCanvas.getBoundingClientRect();
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (let i = 0; i < t.x.length; i++) {
    const w = Math.max(t.w_left[i], t.w_right[i]);
    minX = Math.min(minX, t.x[i] - w); maxX = Math.max(maxX, t.x[i] + w);
    minY = Math.min(minY, t.y[i] - w); maxY = Math.max(maxY, t.y[i] + w);
  }
  const pad = 20;
  const scale = Math.min((rect.width - 2 * pad) / (maxX - minX), (rect.height - 2 * pad) / (maxY - minY));
  view = {
    scale,
    fitScale: scale,
    ox: pad + (rect.width - 2 * pad - scale * (maxX - minX)) / 2 - scale * minX,
    // eixo y invertido (tela cresce para baixo)
    oy: rect.height - pad - (rect.height - 2 * pad - scale * (maxY - minY)) / 2 + scale * minY,
  };
}

const toScreen = (x, y) => [view.ox + view.scale * x, view.oy - view.scale * y];
const toWorld = (sx, sy) => [(sx - view.ox) / view.scale, (view.oy - sy) / view.scale];

// Zoom mantendo o ponto sob o cursor (sx, sy) fixo na tela.
function zoomAt(sx, sy, factor) {
  const newScale = Math.min(Math.max(view.scale * factor, view.fitScale * 0.5), view.fitScale * 200);
  const [wx, wy] = toWorld(sx, sy);
  view.scale = newScale;
  view.ox = sx - newScale * wx;
  view.oy = sy + newScale * wy;
  render();
}

function canvasCenter() {
  const rect = trackCanvas.getBoundingClientRect();
  return [rect.width / 2, rect.height / 2];
}

// ---------- Geometria auxiliar ----------
function trackIndexAtS(s) {
  const t = state.track;
  const n = t.x.length;
  const step = t.length / n;
  return ((Math.round(s / step) % n) + n) % n;
}

function controlPointXY(cp) {
  const t = state.track;
  const i = trackIndexAtS(cp.s);
  return [t.x[i] + cp.alpha * t.normal_x[i], t.y[i] + cp.alpha * t.normal_y[i]];
}

// Ponto do mouse (mundo) → (s, alpha) mais próximo, com clamp na largura.
function nearestOnTrack(wx, wy) {
  const t = state.track;
  let best = 0, bestD = Infinity;
  for (let i = 0; i < t.x.length; i++) {
    const d = (t.x[i] - wx) ** 2 + (t.y[i] - wy) ** 2;
    if (d < bestD) { bestD = d; best = i; }
  }
  const dx = wx - t.x[best], dy = wy - t.y[best];
  let alpha = dx * t.normal_x[best] + dy * t.normal_y[best];
  alpha = Math.max(-(t.w_left[best] - MARGIN), Math.min(t.w_right[best] - MARGIN, alpha));
  return { s: t.s[best], alpha, dist: Math.sqrt(bestD) };
}

function hitControlPoint(sx, sy) {
  for (let i = 0; i < state.controlPoints.length; i++) {
    const [x, y] = controlPointXY(state.controlPoints[i]);
    const [px, py] = toScreen(x, y);
    if ((px - sx) ** 2 + (py - sy) ** 2 < 10 ** 2) return i;
  }
  return null;
}

// ---------- Render: pista ----------
function drawTrack() {
  const { ctx, w, h } = setupCanvas(trackCanvas);
  ctx.clearRect(0, 0, w, h);
  const t = state.track;
  if (!t) return;

  const n = t.x.length;
  // Asfalto: polígono borda direita + borda esquerda invertida.
  ctx.beginPath();
  for (let i = 0; i <= n; i++) {
    const j = i % n;
    const [px, py] = toScreen(t.x[j] + t.w_right[j] * t.normal_x[j], t.y[j] + t.w_right[j] * t.normal_y[j]);
    i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
  }
  for (let i = n; i >= 0; i--) {
    const j = i % n;
    const [px, py] = toScreen(t.x[j] - t.w_left[j] * t.normal_x[j], t.y[j] - t.w_left[j] * t.normal_y[j]);
    ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.fillStyle = "#242423";
  ctx.fill("evenodd");
  ctx.strokeStyle = COLOR_BASELINE;
  ctx.lineWidth = 1;
  ctx.stroke();

  // Center line tracejada.
  ctx.beginPath();
  ctx.setLineDash([6, 6]);
  for (let i = 0; i <= n; i++) {
    const j = i % n;
    const [px, py] = toScreen(t.x[j], t.y[j]);
    i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
  }
  ctx.strokeStyle = COLOR_GRID;
  ctx.stroke();
  ctx.setLineDash([]);

  // Ghost: traçado anterior à otimização, para comparação.
  if (state.ghost) {
    ctx.beginPath();
    ctx.setLineDash([4, 5]);
    for (let i = 0; i <= state.ghost.x.length; i++) {
      const j = i % state.ghost.x.length;
      const [px, py] = toScreen(state.ghost.x[j], state.ghost.y[j]);
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    }
    ctx.strokeStyle = COLOR_MUTED;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Traçado colorido pela velocidade.
  if (state.lap) {
    const lap = state.lap;
    const vMin = Math.min(...lap.v), vMax = Math.max(...lap.v);
    const m = lap.x.length;
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    for (let i = 0; i < m; i++) {
      const j = (i + 1) % m;
      const frac = vMax > vMin ? (lap.v[i] - vMin) / (vMax - vMin) : 0.5;
      const idx = Math.min(SPEED_RAMP.length - 1, Math.floor(frac * SPEED_RAMP.length));
      ctx.beginPath();
      const [ax, ay] = toScreen(lap.x[i], lap.y[i]);
      const [bx, by] = toScreen(lap.x[j], lap.y[j]);
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.strokeStyle = SPEED_RAMP[idx];
      ctx.stroke();
    }
  }

  // Pontos de controle.
  state.controlPoints.forEach((cp, i) => {
    const [x, y] = controlPointXY(cp);
    const [px, py] = toScreen(x, y);
    const active = i === state.drag || i === state.hoverPoint;
    ctx.beginPath();
    ctx.arc(px, py, active ? 7 : 5, 0, 2 * Math.PI);
    ctx.fillStyle = active ? "#ffffff" : "#e8e8e6";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = COLOR_V;
    ctx.stroke();
  });

  // Linha de largada.
  const [sx0, sy0] = toScreen(t.x[0] - t.w_left[0] * t.normal_x[0], t.y[0] - t.w_left[0] * t.normal_y[0]);
  const [sx1, sy1] = toScreen(t.x[0] + t.w_right[0] * t.normal_x[0], t.y[0] + t.w_right[0] * t.normal_y[0]);
  ctx.beginPath();
  ctx.moveTo(sx0, sy0);
  ctx.lineTo(sx1, sy1);
  ctx.strokeStyle = COLOR_MUTED;
  ctx.lineWidth = 2;
  ctx.stroke();
}

// ---------- Render: gráfico de velocidade ----------
function drawSpeedChart() {
  const { ctx, w, h } = setupCanvas(speedCanvas);
  ctx.clearRect(0, 0, w, h);
  const lap = state.lap;
  if (!lap) {
    ctx.fillStyle = COLOR_MUTED;
    ctx.font = "12px system-ui, sans-serif";
    ctx.fillText("Defina ao menos 3 pontos de controle para calcular.", 12, h / 2);
    return;
  }

  const padL = 44, padR = 10, padT = 8, padB = 22;
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const sMax = lap.length;
  const kmh = (v) => v * 3.6;
  // Teto do eixo: um pouco acima da velocidade máxima, arredondado a 50 km/h.
  const vTop = Math.ceil((kmh(Math.max(...lap.v)) * 1.15) / 50) * 50;

  const X = (s) => padL + (s / sMax) * plotW;
  const Y = (v) => padT + plotH - (kmh(v) / vTop) * plotH;

  // Grade horizontal + rótulos.
  ctx.font = "11px system-ui, sans-serif";
  ctx.textAlign = "right";
  for (let g = 0; g <= 4; g++) {
    const val = (vTop / 4) * g;
    const y = padT + plotH - (g / 4) * plotH;
    ctx.strokeStyle = g === 0 ? COLOR_BASELINE : COLOR_GRID;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
    ctx.fillStyle = COLOR_MUTED;
    ctx.fillText(String(Math.round(val)), padL - 6, y + 4);
  }
  // Rótulos do eixo x (km).
  ctx.textAlign = "center";
  for (let g = 0; g <= 4; g++) {
    const s = (sMax / 4) * g;
    ctx.fillText((s / 1000).toFixed(1) + " km", X(s), h - 6);
  }

  const drawSeries = (values, color, dash) => {
    ctx.beginPath();
    ctx.setLineDash(dash || []);
    for (let i = 0; i < lap.s.length; i++) {
      const v = Math.min(values[i], vTop / 3.6);
      i === 0 ? ctx.moveTo(X(lap.s[i]), Y(v)) : ctx.lineTo(X(lap.s[i]), Y(v));
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.setLineDash([]);
  };

  drawSeries(lap.v_grip, COLOR_GRIP, [4, 4]);
  drawSeries(lap.v, COLOR_V);

  // Crosshair.
  if (state.chartHover !== null) {
    const i = state.chartHover;
    const x = X(lap.s[i]);
    ctx.strokeStyle = COLOR_MUTED;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, padT);
    ctx.lineTo(x, padT + plotH);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x, Y(lap.v[i]), 4, 0, 2 * Math.PI);
    ctx.fillStyle = COLOR_V;
    ctx.fill();
  }
}

// ---------- Recalcular ----------
let computing = false, pendingCompute = false;

async function recompute() {
  if (!state.track || !state.vehicle) return;
  if (state.controlPoints.length < 3) {
    state.lap = null;
    render();
    return;
  }
  if (computing) { pendingCompute = true; return; }
  computing = true;
  try {
    const t0 = performance.now();
    state.lap = await postJSON("/api/laptime", {
      track_id: state.track.id,
      vehicle: state.vehicle,
      control_points: state.controlPoints,
    });
    setStatus(`recalculado em ${(performance.now() - t0).toFixed(0)} ms`);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    computing = false;
    render();
    if (pendingCompute) { pendingCompute = false; recompute(); }
  }
}

// ---------- UI ----------
const $ = (id) => document.getElementById(id);

function setStatus(msg, isError = false) {
  $("status").textContent = msg;
  $("status").className = "status" + (isError ? " error" : "");
}

function formatLapTime(t) {
  const min = Math.floor(t / 60);
  const sec = (t - 60 * min).toFixed(2).padStart(5, "0");
  return `${min}:${sec}`;
}

function render() {
  drawTrack();
  drawSpeedChart();
  $("stat-points").textContent = String(state.controlPoints.length);
  if (state.lap) {
    $("lap-time").textContent = formatLapTime(state.lap.lap_time);
    $("stat-length").textContent = (state.lap.length / 1000).toFixed(3) + " km";
    const vAvg = state.lap.length / state.lap.lap_time;
    $("stat-vavg").textContent = (vAvg * 3.6).toFixed(1) + " km/h";
    $("stat-vmax").textContent = (Math.max(...state.lap.v) * 3.6).toFixed(1) + " km/h";
  } else {
    $("lap-time").textContent = "—";
    $("stat-length").textContent = "—";
    $("stat-vavg").textContent = "—";
    $("stat-vmax").textContent = "—";
  }
}

// Veículo: linhas do formulário ↔ objeto (com conversões kW / km/h).
function vehicleToForm() {
  const v = state.vehicle;
  const set = (p, val) => { document.querySelector(`[data-param="${p}"]`).value = val; };
  set("mass", v.mass);
  set("power_kw", Math.round(v.power / 1000));
  set("a_accel_max", v.a_accel_max);
  set("a_brake_max", v.a_brake_max);
  set("a_lat_max", v.a_lat_max);
  set("cd_a", v.cd_a);
  set("cl_a", v.cl_a);
  set("crr", v.crr);
  set("v_max_kmh", Math.round(v.v_max * 3.6));
}

function formToVehicle() {
  const get = (p) => parseFloat(document.querySelector(`[data-param="${p}"]`).value) || 0;
  state.vehicle = {
    ...state.vehicle,
    mass: get("mass"),
    power: get("power_kw") * 1000,
    a_accel_max: get("a_accel_max"),
    a_brake_max: get("a_brake_max"),
    a_lat_max: get("a_lat_max"),
    cd_a: get("cd_a"),
    cl_a: get("cl_a"),
    crr: get("crr"),
    v_max: get("v_max_kmh") / 3.6,
  };
}

// ---------- Carregamento ----------
async function loadTrack(trackId) {
  state.track = await api(`/api/tracks/${trackId}`);
  state.ghost = null;
  fitView();
  await loadTrajectories();
  recompute();
}

async function loadTrajectories() {
  state.trajectories = await api(`/api/trajectories?track_id=${state.track.id}`);
  const sel = $("trajectory-select");
  sel.innerHTML = "";
  const optNew = new Option("— novo traçado —", "");
  sel.add(optNew);
  state.trajectories.forEach((tr) => sel.add(new Option(tr.name, String(tr.id))));
  if (state.trajectories.length > 0) {
    const first = state.trajectories[0];
    sel.value = String(first.id);
    state.trajectoryId = first.id;
    state.controlPoints = first.control_points.map((cp) => ({ ...cp }));
    $("trajectory-name").value = first.name;
  } else {
    state.trajectoryId = null;
    state.controlPoints = [];
    $("trajectory-name").value = "";
  }
}

async function init() {
  try {
    [state.tracks, state.vehicles] = await Promise.all([api("/api/tracks"), api("/api/vehicles")]);
    const trackSel = $("track-select");
    state.tracks.forEach((t) => trackSel.add(new Option(`${t.name} (${(t.length / 1000).toFixed(1)} km)`, String(t.id))));
    const vehicleSel = $("vehicle-select");
    state.vehicles.forEach((v) => vehicleSel.add(new Option(v.name, String(v.id))));

    if (state.vehicles.length > 0) {
      state.vehicle = { ...state.vehicles[0] };
      vehicleToForm();
    }
    if (state.tracks.length > 0) {
      await loadTrack(state.tracks[0].id);
    } else {
      setStatus("nenhuma pista no banco — rode: python -m app.seed", true);
    }
  } catch (err) {
    setStatus("falha ao carregar dados: " + err.message, true);
  }
  render();
}

// ---------- Eventos: canvas da pista ----------
let dragThrottle = 0;

trackCanvas.addEventListener("mousedown", (e) => {
  if (!state.track) return;
  const rect = trackCanvas.getBoundingClientRect();
  const sx = e.clientX - rect.left, sy = e.clientY - rect.top;
  // Botão direito ou do meio: pan da visualização.
  if (e.button === 1 || e.button === 2) {
    pan = { startX: sx, startY: sy, ox: view.ox, oy: view.oy };
    trackCanvas.style.cursor = "grabbing";
    e.preventDefault();
    return;
  }
  if (e.button !== 0) return;
  const hit = hitControlPoint(sx, sy);
  if (hit !== null) {
    state.drag = hit;
  } else {
    const [wx, wy] = toWorld(sx, sy);
    const near = nearestOnTrack(wx, wy);
    // Só cria ponto se o clique foi razoavelmente perto da pista.
    if (near.dist < Math.max(...state.track.w_left, ...state.track.w_right) * 3) {
      state.controlPoints.push({ s: near.s, alpha: near.alpha });
      state.drag = state.controlPoints.length - 1;
      recompute();
    }
  }
  render();
});

trackCanvas.addEventListener("mousemove", (e) => {
  if (!state.track) return;
  const rect = trackCanvas.getBoundingClientRect();
  const sx = e.clientX - rect.left, sy = e.clientY - rect.top;
  if (pan !== null) {
    view.ox = pan.ox + (sx - pan.startX);
    view.oy = pan.oy + (sy - pan.startY);
    render();
    return;
  }
  if (state.drag !== null) {
    const [wx, wy] = toWorld(sx, sy);
    const near = nearestOnTrack(wx, wy);
    state.controlPoints[state.drag] = { s: near.s, alpha: near.alpha };
    render();
    const now = performance.now();
    if (now - dragThrottle > 50) {
      dragThrottle = now;
      recompute();
    }
  } else {
    const prev = state.hoverPoint;
    state.hoverPoint = hitControlPoint(sx, sy);
    trackCanvas.style.cursor = state.hoverPoint !== null ? "grab" : "crosshair";
    if (prev !== state.hoverPoint) render();
  }
});

window.addEventListener("mouseup", () => {
  if (pan !== null) {
    pan = null;
    trackCanvas.style.cursor = "crosshair";
  }
  if (state.drag !== null) {
    state.drag = null;
    recompute();
  }
});

trackCanvas.addEventListener("contextmenu", (e) => e.preventDefault());

trackCanvas.addEventListener("wheel", (e) => {
  if (!state.track) return;
  e.preventDefault();
  const rect = trackCanvas.getBoundingClientRect();
  const factor = Math.pow(1.0015, -e.deltaY);
  zoomAt(e.clientX - rect.left, e.clientY - rect.top, factor);
}, { passive: false });

$("zoom-in").addEventListener("click", () => zoomAt(...canvasCenter(), 1.5));
$("zoom-out").addEventListener("click", () => zoomAt(...canvasCenter(), 1 / 1.5));
$("zoom-reset").addEventListener("click", () => { fitView(); render(); });

trackCanvas.addEventListener("dblclick", (e) => {
  const rect = trackCanvas.getBoundingClientRect();
  const hit = hitControlPoint(e.clientX - rect.left, e.clientY - rect.top);
  if (hit !== null) {
    state.controlPoints.splice(hit, 1);
    recompute();
  }
});

// ---------- Eventos: gráfico ----------
speedCanvas.addEventListener("mousemove", (e) => {
  if (!state.lap) return;
  const rect = speedCanvas.getBoundingClientRect();
  const padL = 44, padR = 10;
  const frac = (e.clientX - rect.left - padL) / (rect.width - padL - padR);
  if (frac < 0 || frac > 1) { state.chartHover = null; tooltip.hidden = true; drawSpeedChart(); return; }
  // s é quase uniforme, então a proporção já dá o índice do sample.
  const i = Math.round(frac * (state.lap.s.length - 1));
  state.chartHover = i;
  tooltip.hidden = false;
  tooltip.style.left = (e.clientX - rect.left + 24) + "px";
  tooltip.style.top = (e.clientY - rect.top + 4) + "px";
  tooltip.innerHTML =
    `s <b>${(state.lap.s[i] / 1000).toFixed(2)} km</b> · ` +
    `vel <b>${(state.lap.v[i] * 3.6).toFixed(0)} km/h</b> · ` +
    `grip <b>${Math.min(state.lap.v_grip[i] * 3.6, 999).toFixed(0)} km/h</b>`;
  drawSpeedChart();
});

speedCanvas.addEventListener("mouseleave", () => {
  state.chartHover = null;
  tooltip.hidden = true;
  drawSpeedChart();
});

// ---------- Eventos: sidebar ----------
$("track-select").addEventListener("change", (e) => loadTrack(parseInt(e.target.value)).then(render));

$("vehicle-select").addEventListener("change", (e) => {
  const v = state.vehicles.find((v) => v.id === parseInt(e.target.value));
  if (v) {
    state.vehicle = { ...v };
    vehicleToForm();
    recompute();
  }
});

$("vehicle-params").addEventListener("input", () => {
  formToVehicle();
  recompute();
});

$("trajectory-select").addEventListener("change", (e) => {
  const id = e.target.value ? parseInt(e.target.value) : null;
  state.trajectoryId = id;
  if (id === null) {
    state.controlPoints = [];
    $("trajectory-name").value = "";
  } else {
    const tr = state.trajectories.find((t) => t.id === id);
    state.controlPoints = tr.control_points.map((cp) => ({ ...cp }));
    $("trajectory-name").value = tr.name;
  }
  recompute();
});

$("optimize").addEventListener("click", async () => {
  if (!state.track || !state.vehicle) return;
  const btn = $("optimize");
  btn.disabled = true;
  setStatus("otimizando traçado (QP de curvatura mínima)…");
  try {
    // Guarda o traçado atual como ghost para comparação visual.
    const before = state.lap ? { x: state.lap.x, y: state.lap.y, lapTime: state.lap.lap_time } : null;
    const res = await postJSON("/api/optimize", {
      track_id: state.track.id,
      vehicle: state.vehicle,
    });
    state.ghost = before;
    state.controlPoints = res.control_points.map((cp) => ({ ...cp }));
    state.lap = res.lap;
    if (before) {
      const delta = before.lapTime - res.lap.lap_time;
      const sign = delta >= 0 ? "-" : "+";
      setStatus(`traçado otimizado: ${formatLapTime(res.lap.lap_time)} (${sign}${Math.abs(delta).toFixed(2)} s vs anterior, em cinza)`);
    } else {
      setStatus(`traçado otimizado: ${formatLapTime(res.lap.lap_time)}`);
    }
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    btn.disabled = false;
    render();
  }
});

$("save-trajectory").addEventListener("click", async () => {
  if (!state.track || state.controlPoints.length < 3) {
    setStatus("defina ao menos 3 pontos antes de salvar", true);
    return;
  }
  const name = $("trajectory-name").value.trim() || "sem nome";
  const payload = { name, track_id: state.track.id, control_points: state.controlPoints };
  try {
    if (state.trajectoryId !== null) {
      await postJSON(`/api/trajectories/${state.trajectoryId}`, payload, "PUT");
    } else {
      const created = await postJSON("/api/trajectories", payload);
      state.trajectoryId = created.id;
    }
    setStatus(`traçado "${name}" salvo`);
    const keepId = state.trajectoryId, keepPoints = state.controlPoints;
    await loadTrajectories();
    // Mantém a seleção atual em vez de voltar para o primeiro da lista.
    state.trajectoryId = keepId;
    state.controlPoints = keepPoints;
    $("trajectory-select").value = String(keepId);
    $("trajectory-name").value = name;
    recompute();
  } catch (err) {
    setStatus(err.message, true);
  }
});

window.addEventListener("resize", () => { fitView(); render(); });

init();
