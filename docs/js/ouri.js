/*
 * Ouri web animator — a faithful browser port of src/ouri/display/face.py.
 * Renders the 128x64 OLED face on a scaled canvas with a soft cyan glow,
 * plus the pet -> heart-rate card. Pure vanilla JS, no dependencies.
 */
(function () {
  "use strict";

  const W = 128;
  const H = 64;
  const S = 7; // device pixel -> canvas pixel scale
  const FPS = 12; // match the real device cadence
  const ON = "#d6f3ff";
  const GLOW = "rgba(122, 222, 255, 0.55)";

  const HEARTBEAT_STATES = new Set([
    "idle",
    "happy",
    "recovering",
    "sleepy_night",
    "proud",
  ]);
  const BLUSH_STATES = new Set(["happy", "pet_reaction", "proud"]);

  // Offscreen device buffer (transparent bg so carve-outs use destination-out).
  const buf = document.createElement("canvas");
  buf.width = W * S;
  buf.height = H * S;
  const b = buf.getContext("2d");

  // ---- PIL-like drawing primitives (device coords, scaled by S) ---------- //
  function modeOn() {
    b.globalCompositeOperation = "source-over";
    b.fillStyle = ON;
    b.strokeStyle = ON;
  }
  function modeOff() {
    b.globalCompositeOperation = "destination-out";
    b.fillStyle = "#000";
    b.strokeStyle = "#000";
  }
  function rrect(x0, y0, x1, y1, r, fill) {
    const x = x0 * S,
      y = y0 * S,
      w = (x1 - x0) * S,
      h = (y1 - y0) * S,
      rad = r * S;
    b.beginPath();
    b.moveTo(x + rad, y);
    b.arcTo(x + w, y, x + w, y + h, rad);
    b.arcTo(x + w, y + h, x, y + h, rad);
    b.arcTo(x, y + h, x, y, rad);
    b.arcTo(x, y, x + w, y, rad);
    b.closePath();
    if (fill) b.fill();
    else b.stroke();
  }
  function ellipse(x0, y0, x1, y1, opts) {
    opts = opts || {};
    const cx = ((x0 + x1) / 2) * S;
    const cy = ((y0 + y1) / 2) * S;
    const rx = Math.max(0.2, ((x1 - x0) / 2) * S);
    const ry = Math.max(0.2, ((y1 - y0) / 2) * S);
    b.beginPath();
    b.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    if (opts.fill) b.fill();
    if (opts.outline) {
      b.lineWidth = (opts.width || 1) * S;
      b.stroke();
    }
  }
  function line(points, width) {
    b.lineWidth = (width || 1) * S;
    b.lineJoin = "round";
    b.lineCap = "round";
    b.beginPath();
    points.forEach((p, i) => {
      const x = p[0] * S,
        y = p[1] * S;
      if (i === 0) b.moveTo(x, y);
      else b.lineTo(x, y);
    });
    b.stroke();
  }
  function rect(x0, y0, x1, y1) {
    b.fillRect(x0 * S, y0 * S, (x1 - x0) * S, (y1 - y0) * S);
  }
  function point(x, y) {
    b.fillRect(x * S, y * S, S, S);
  }

  // ---- geometry constants (mirror face.py) ------------------------------ //
  const EYE_W = 20,
    EYE_H = 22,
    EYE_R = 7,
    LEFT_EYE_X = 43,
    RIGHT_EYE_X = 85;

  function layoutFor(bob) {
    return { bob, eye_cy: 32 + bob, mouth_y: 50 + bob, antenna_y: 9 + bob };
  }
  function bobOffset(state, f) {
    if (state === "motivate") return Math.round(2 * Math.sin(f * 0.35));
    if (state === "happy" || state === "pet_reaction" || state === "proud")
      return Math.round(1 * Math.sin(f * 0.25));
    if (state === "tired") return Math.floor(f / 30) % 2 ? 1 : 0;
    if (state === "sleepy_night" || state === "recovering" || state === "asleep")
      return Math.round(1 * Math.sin(f * 0.07));
    return 0;
  }

  // ---- antenna ---------------------------------------------------------- //
  function drawAntenna(L) {
    const by = L.antenna_y;
    [54, 74].forEach((ax) => {
      line(
        [
          [ax, by + 2],
          [ax, by + 6],
        ],
        1
      );
      ellipse(ax - 2, by - 2, ax + 2, by + 2, { fill: true, outline: true });
    });
  }

  // ---- eyes ------------------------------------------------------------- //
  function eyeBox(cx, cy, w, h) {
    w = w || EYE_W;
    h = h || EYE_H;
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2];
  }
  function openEye(cx, cy, look) {
    look = look || 0;
    const box = eyeBox(cx + look, cy);
    rrect(box[0], box[1], box[2], box[3], EYE_R, true);
    modeOff();
    ellipse(box[0] + 3, box[1] + 3, box[0] + 8, box[1] + 9, { fill: true });
    ellipse(box[0] + 10, box[1] + 4, box[0] + 12, box[1] + 6, { fill: true });
    modeOn();
  }
  function blinkEye(cx, cy) {
    rrect(cx - EYE_W / 2, cy - 2, cx + EYE_W / 2, cy + 2, 2, true);
  }
  function curveEye(cx, cy, amp, width) {
    const pts = [];
    for (let deg = 0; deg <= 180; deg += 15) {
      const a = (deg * Math.PI) / 180;
      pts.push([cx - (EYE_W / 2) * Math.cos(a), cy + 3 - amp * Math.sin(a)]);
    }
    line(pts, width);
  }
  function tiredEye(cx, cy, frac) {
    const box = eyeBox(cx, cy);
    rrect(box[0], box[1], box[2], box[3], EYE_R, true);
    const coverBottom = box[1] + EYE_H * frac;
    modeOff();
    rect(box[0] - 1, box[1] - 1, box[2] + 1, coverBottom);
    modeOn();
    line(
      [
        [box[0] + 1, coverBottom],
        [box[2] - 1, coverBottom],
      ],
      1
    );
  }
  function stressedEye(cx, cy, left) {
    const box = [cx - EYE_W / 2, cy - 2, cx + EYE_W / 2, cy + 6];
    rrect(box[0], box[1], box[2], box[3], 4, true);
    if (left)
      line(
        [
          [box[0], cy - 8],
          [box[2], cy - 4],
        ],
        2
      );
    else
      line(
        [
          [box[0], cy - 4],
          [box[2], cy - 8],
        ],
        2
      );
  }
  function xEye(cx, cy) {
    const r = 7;
    line(
      [
        [cx - r, cy - r],
        [cx + r, cy + r],
      ],
      2
    );
    line(
      [
        [cx + r, cy - r],
        [cx - r, cy + r],
      ],
      2
    );
  }
  function eyeLook(f) {
    const c = f % 200;
    if (c >= 70 && c < 86) return -2;
    if (c >= 110 && c < 126) return 2;
    return 0;
  }
  function closedEye(cx, cy) {
    const pts = [];
    for (let deg = 0; deg <= 180; deg += 30) {
      const a = (deg * Math.PI) / 180;
      pts.push([cx - 6 * Math.cos(a), cy + 2 * Math.sin(a)]);
    }
    line(pts, 2);
  }
  function drawEyes(style, f, L) {
    const cy = L.eye_cy,
      lx = LEFT_EYE_X,
      rx = RIGHT_EYE_X;
    if (style === "closed") {
      closedEye(lx, cy);
      closedEye(rx, cy);
      return;
    }
    if (style === "open") {
      if (f % 70 < 3) {
        blinkEye(lx, cy);
        blinkEye(rx, cy);
      } else {
        const look = eyeLook(f);
        openEye(lx, cy, look);
        openEye(rx, cy, look);
      }
      return;
    }
    if (style === "happy") {
      curveEye(lx, cy, 9, 3);
      curveEye(rx, cy, 9, 3);
      return;
    }
    if (style === "soft") {
      curveEye(lx, cy, 6, 2);
      curveEye(rx, cy, 6, 2);
      return;
    }
    if (style === "tired") {
      tiredEye(lx, cy, 0.5);
      tiredEye(rx, cy, 0.5);
      return;
    }
    if (style === "sleepy") {
      const droop = 0.66 + (f % 80 > 40 ? 0.06 : 0);
      tiredEye(lx, cy, droop);
      tiredEye(rx, cy, droop);
      return;
    }
    if (style === "stressed") {
      stressedEye(lx, cy, true);
      stressedEye(rx, cy, false);
      return;
    }
    if (style === "sick") {
      xEye(lx, cy);
      xEye(rx, cy);
      return;
    }
    openEye(lx, cy, 0);
    openEye(rx, cy, 0);
  }
  function drawBlush(L) {
    const cy = L.eye_cy + 9;
    [30, 98].forEach((cx) => {
      ellipse(cx - 3, cy - 2, cx + 3, cy + 2, { outline: true });
      point(cx, cy);
    });
  }

  // ---- mouth ------------------------------------------------------------ //
  function arcMouth(cx, cy, smile) {
    const pts = [];
    for (let dx = -6; dx <= 6; dx += 2) {
      const t = dx / 6.0;
      pts.push([cx + dx, cy - smile * (1 - t * t)]);
    }
    line(pts, 1);
  }
  function drawMouth(style, f, L) {
    const cx = 64,
      my = L.mouth_y;
    if (style === "smile") return arcMouth(cx, my, 3);
    if (style === "pet") return arcMouth(cx, my, 4);
    if (style === "motivate")
      return arcMouth(cx, my + Math.round(Math.sin(f * 0.5)), 3);
    if (style === "frown") return arcMouth(cx, my + 2, -3);
    if (style === "yawn") {
      const phase = f % 60;
      if (phase < 12) {
        const r = 2 + Math.floor(phase / 4);
        ellipse(cx - 4, my - r, cx + 4, my + r, { outline: true });
      } else arcMouth(cx, my, 0);
      return;
    }
    if (style === "wavy") {
      const pts = [];
      for (let i = 0; i < 13; i++) pts.push([cx - 6 + i, my + (i % 2 === 0 ? 1 : -1)]);
      line(pts, 1);
      return;
    }
    arcMouth(cx, my, 0);
  }

  // ---- decorative extras ------------------------------------------------ //
  function drawHeart(hx, hy) {
    const rows = [" # # ", "#####", " ### ", "  #  "];
    rows.forEach((row, ri) => {
      for (let ci = 0; ci < row.length; ci++)
        if (row[ci] === "#") point(hx + ci, hy + ri);
    });
  }
  function drawMoon(cx, cy, r) {
    r = r || 6;
    ellipse(cx - r, cy - r, cx + r, cy + r, { fill: true });
    const off = r - 2;
    modeOff();
    ellipse(cx - r + off, cy - r, cx + r + off, cy + r, { fill: true });
    modeOn();
  }
  function drawStar(cx, cy, size) {
    size = size || 2;
    line(
      [
        [cx - size, cy],
        [cx + size, cy],
      ],
      1
    );
    line(
      [
        [cx, cy - size],
        [cx, cy + size],
      ],
      1
    );
    point(cx - size + 1, cy - size + 1);
  }
  function breathingRing(cx, cy, f, period) {
    const phase = (Math.sin(f * period) + 1) / 2;
    const r = Math.round(3 + phase * 5);
    ellipse(cx - r, cy - r, cx + r, cy + r, { outline: true });
  }
  function tinyZ(x, y, h) {
    h = h || 3;
    line(
      [
        [x, y],
        [x + h, y],
        [x, y + h],
        [x + h, y + h],
      ],
      1
    );
  }
  function drawExtras(state, f, L) {
    const bob = L.bob;
    if (BLUSH_STATES.has(state)) drawBlush(L);
    if (state === "sick") {
      const tx = 110,
        ty = 14 + bob;
      rrect(tx, ty, tx + 3, ty + 10, 1, false);
      ellipse(tx - 1, ty + 9, tx + 4, ty + 14, { outline: true });
      if (f % 24 < 12)
        line(
          [
            [tx + 1, ty + 3],
            [tx + 1, ty + 9],
          ],
          1
        );
    }
    if (state === "motivate") {
      for (let i = 0; i < 3; i++) {
        const bx = 8 + i * 6;
        const by = 50 - Math.round(2 * Math.abs(Math.sin((f + i * 5) * 0.35)));
        rect(bx, by, bx + 2, by + 2);
      }
    }
    if (state === "pet_reaction" && f % 28 < 20) drawHeart(110, 28 + bob);
    if (state === "tired" && f % 50 > 32) {
      tinyZ(102, 8 + bob);
      tinyZ(106, 6 + bob);
    }
    if (state === "sleepy_night") {
      drawMoon(114, 14 + bob);
      const drift = Math.floor(f / 8) % 6;
      tinyZ(100, 30 - drift + bob);
    }
    if (state === "proud") {
      [
        [12, 12],
        [114, 12],
        [16, 34],
        [112, 34],
      ].forEach((p, i) => {
        if ((f + i * 7) % 28 < 16) drawStar(p[0], p[1] + bob);
      });
    }
    if (state === "stressed") {
      breathingRing(112, 30 + bob, f, 0.18);
      const sy = 12 + (Math.floor(f / 4) % 6);
      point(24, sy + bob);
      point(24, sy + 1 + bob);
    }
    if (state === "recovering") breathingRing(112, 30 + bob, f, 0.08);
    if (state === "asleep") {
      const cycle = Math.floor(f / 12) % 4;
      if (cycle < 3) tinyZ(74 + cycle * 4, 18 - cycle * 3 + bob);
    }
  }

  function stylesForState(state, f) {
    switch (state) {
      case "tired":
        return ["tired", f % 60 < 12 ? "yawn" : "flat"];
      case "motivate":
        return ["open", "motivate"];
      case "sick":
        return ["sick", "frown"];
      case "happy":
        return ["happy", "smile"];
      case "pet_reaction":
        return ["happy", "pet"];
      case "sleepy_night":
        return ["sleepy", "flat"];
      case "proud":
        return ["happy", "smile"];
      case "stressed":
        return ["stressed", "wavy"];
      case "recovering":
        return ["soft", "smile"];
      case "asleep":
        return ["closed", "flat"];
      default:
        return ["open", "flat"];
    }
  }
  function drawHeartbeat(f, bpm, L) {
    bpm = Math.max(30, Math.min(180, bpm));
    const fpb = Math.max(4, Math.round(FPS * 60 / bpm));
    const phase = f % fpb;
    const hx = 62,
      hy = Math.max(0, L.antenna_y - 5);
    if (phase < 2) drawHeart(hx, hy);
    else if (phase < 4) {
      point(hx + 1, hy + 1);
      point(hx + 2, hy + 1);
    }
  }

  function renderFace(state, f, bpm) {
    b.clearRect(0, 0, buf.width, buf.height);
    modeOn();
    const bob = bobOffset(state, f);
    const L = layoutFor(bob);
    drawAntenna(L);
    const [eyeStyle, mouthStyle] = stylesForState(state, f);
    drawEyes(eyeStyle, f, L);
    drawMouth(mouthStyle, f, L);
    drawExtras(state, f, L);
    if (bpm && HEARTBEAT_STATES.has(state)) drawHeartbeat(f, bpm, L);
  }

  // ---- pet -> heart-rate card (port of display/heartrate.py) ------------ //
  function pulseScale(f, bpm) {
    const fpb = Math.max(4, Math.round(FPS * 60 / Math.max(30, Math.min(200, bpm))));
    const phase = f % fpb;
    if (phase === 0) return 1.28;
    if (phase === 1) return 1.16;
    if (phase === 2) return 1.06;
    return 1.0;
  }
  function heartShape(cx, cy, size) {
    const lobeR = size * 0.3;
    [
      [cx - lobeR, cy],
      [cx + lobeR, cy],
    ].forEach((c) => {
      ellipse(c[0] - lobeR, c[1] - lobeR, c[0] + lobeR, c[1] + lobeR, {
        fill: true,
      });
    });
    const halfW = lobeR * 2;
    b.beginPath();
    b.moveTo((cx - halfW) * S, cy * S);
    b.lineTo((cx + halfW) * S, cy * S);
    b.lineTo(cx * S, (cy + size * 0.78) * S);
    b.closePath();
    b.fill();
  }
  function renderHeartCard(bpm, f) {
    b.clearRect(0, 0, buf.width, buf.height);
    modeOn();
    rrect(0, 0, W - 1, H - 1, 4, false);
    b.textBaseline = "top";
    b.font = `600 ${9 * S}px Inter, sans-serif`;
    b.textAlign = "center";
    b.fillText("HEART RATE", (W / 2) * S, 3 * S);
    const size = 13 * pulseScale(f, bpm);
    heartShape(34, 28, size);
    b.font = `700 ${26 * S}px Inter, sans-serif`;
    b.fillText(String(bpm), 84 * S, 22 * S);
    b.font = `600 ${10 * S}px Inter, sans-serif`;
    b.fillText("BPM", 84 * S, 48 * S);
    b.textAlign = "left";
  }

  // ---- compositing onto the visible screen ------------------------------ //
  function paint(screen) {
    const ctx = screen.ctx;
    const cw = screen.canvas.width,
      ch = screen.canvas.height;
    const g = ctx.createLinearGradient(0, 0, 0, ch);
    g.addColorStop(0, "#0a1018");
    g.addColorStop(1, "#05080d");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, cw, ch);
    ctx.save();
    ctx.shadowColor = GLOW;
    ctx.shadowBlur = 14;
    ctx.drawImage(buf, 0, 0, cw, ch);
    ctx.shadowBlur = 0;
    ctx.drawImage(buf, 0, 0, cw, ch);
    ctx.restore();
  }

  // ---- controller ------------------------------------------------------- //
  const MOODS = [
    ["idle", "Idle"],
    ["happy", "Happy"],
    ["tired", "Tired"],
    ["motivate", "Move!"],
    ["sick", "Sick"],
    ["proud", "Proud"],
    ["stressed", "Stressed"],
    ["recovering", "Recovering"],
    ["sleepy_night", "Sleepy"],
    ["asleep", "Asleep"],
  ];
  const CYCLE = [
    "idle",
    "happy",
    "tired",
    "motivate",
    "proud",
    "stressed",
    "sick",
    "recovering",
    "sleepy_night",
  ];

  function init() {
    const canvas = document.getElementById("ouri-screen");
    if (!canvas) return;
    canvas.width = W * S;
    canvas.height = H * S;
    const screen = { canvas, ctx: canvas.getContext("2d") };

    let state = "idle";
    let frame = 0;
    let bpm = 64;
    let petUntil = 0;
    let cardUntil = 0;
    let autoCycle = true;
    let cycleIdx = 0;
    let cycleAt = 0;

    function setMood(m, manual) {
      state = m;
      if (manual) {
        autoCycle = false;
        const cb = document.getElementById("ouri-autocycle");
        if (cb) cb.checked = false;
      }
      updateChips();
    }
    function updateChips() {
      document.querySelectorAll("[data-mood]").forEach((el) => {
        el.classList.toggle("is-active", el.getAttribute("data-mood") === state);
      });
    }

    // Build mood chips
    const chipWrap = document.getElementById("ouri-moods");
    if (chipWrap) {
      MOODS.forEach(([id, label]) => {
        const btn = document.createElement("button");
        btn.className = "chip";
        btn.textContent = label;
        btn.setAttribute("data-mood", id);
        btn.addEventListener("click", () => setMood(id, true));
        chipWrap.appendChild(btn);
      });
    }
    const petBtn = document.getElementById("ouri-pet");
    if (petBtn)
      petBtn.addEventListener("click", () => {
        bpm = 66 + Math.floor(Math.random() * 16); // a believable live-ish reading
        petUntil = performance.now() + 2000;
        cardUntil = performance.now() + 3000;
        autoCycle = false;
        const cb = document.getElementById("ouri-autocycle");
        if (cb) cb.checked = false;
      });
    canvas.addEventListener("click", () => {
      if (petBtn) petBtn.click();
    });
    const cycleCb = document.getElementById("ouri-autocycle");
    if (cycleCb)
      cycleCb.addEventListener("change", (e) => {
        autoCycle = e.target.checked;
      });

    updateChips();

    const interval = 1000 / FPS;
    let last = 0;
    function loop(now) {
      if (now - last >= interval) {
        last = now;
        frame++;

        if (autoCycle && now >= cycleAt && now >= cardUntil) {
          state = CYCLE[cycleIdx % CYCLE.length];
          cycleIdx++;
          cycleAt = now + 3600;
          updateChips();
        }

        if (now < cardUntil) {
          renderHeartCard(bpm, frame);
        } else if (now < petUntil) {
          renderFace("pet_reaction", frame, bpm);
        } else {
          renderFace(state, frame, bpm);
        }
        paint(screen);
      }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
})();
