#!/usr/bin/env python3
"""Generate interactive factory location map as self-contained HTML."""
import json
import math

SEARCH_RADIUS = 50_000  # 500m
MINER_RATES = {'impure': 300, 'normal': 600, 'pure': 780}
OIL_RATES = {'impure': 150, 'normal': 300, 'pure': 600}

MINING_TOWNS = [
    {
        'id': 'siderith',
        'name': 'Siderith',
        'theme': 'Iron Mining Outpost',
        'resource': 'iron',
        'cx': 241941, 'cy': 3242,
        'color': '#ff6b6b',
        'supplies': ['Naphtheon (2,007/min)', 'Luxara (40/min)'],
    },
    {
        'id': 'calcara',
        'name': 'Calcara',
        'theme': 'Limestone Quarry',
        'resource': 'limestone',
        'cx': 169486, 'cy': -45968,
        'color': '#dfe6e9',
        'supplies': ['Ferrium (764/min)', 'Luxara (157/min)'],
    },
]

def dist(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def main():
    with open('/Users/deepak/AI/satisfy/selected-factory-locations.json') as f:
        sel = json.load(f)
    with open('/Users/deepak/AI/satisfy/resource_nodes.json') as f:
        rn = json.load(f)

    raw_nodes = rn['resource_nodes']

    # Compact all resource nodes: {x, y, t(type), p(urity first char)}
    all_nodes = []
    for n in raw_nodes:
        all_nodes.append({
            'x': round(n['x']),
            'y': round(n['y']),
            't': n['type'],
            'p': n['purity'][0],  # i/n/p
        })

    # Build factory data from selected locations (skip mining towns)
    factories = {}
    for fid, fd in sel['selections'].items():
        if fd.get('type') == 'mining_town':
            continue
        factories[fid] = {
            'name': fd['factory_name'],
            'theme': fd['theme'],
            'req': fd['required_resources'],
            'cx': fd['center']['x'],
            'cy': fd['center']['y'],
            'totalNodes': fd['total_nodes'],
            'nodes': fd['nodes'],
            'resources': fd['resources'],
        }
        print(f"  {fd['factory_name']}: ({fd['center']['x']}, {fd['center']['y']}) "
              f"- {fd['total_nodes']} nodes")

    # Build mining town data — find nodes within 500m of each town center
    mining_towns = []
    for mt in MINING_TOWNS:
        nearby = []
        total_cap = 0
        purity_counts = {'pure': 0, 'normal': 0, 'impure': 0}
        for n in raw_nodes:
            if n['type'] != mt['resource']:
                continue
            if dist(mt['cx'], mt['cy'], n['x'], n['y']) <= SEARCH_RADIUS:
                nearby.append({
                    'x': round(n['x']),
                    'y': round(n['y']),
                    't': n['type'],
                    'p': n['purity'][0],
                })
                rates = OIL_RATES if n['type'] == 'oil' else MINER_RATES
                total_cap += rates[n['purity']]
                purity_counts[n['purity']] += 1

        mining_towns.append({
            'id': mt['id'],
            'name': mt['name'],
            'theme': mt['theme'],
            'resource': mt['resource'],
            'color': mt['color'],
            'cx': mt['cx'],
            'cy': mt['cy'],
            'nodes': nearby,
            'capacity': total_cap,
            'nodeCount': len(nearby),
            'purity': purity_counts,
            'supplies': mt['supplies'],
        })
        print(f"  {mt['name']}: {len(nearby)} {mt['resource']} nodes, "
              f"{total_cap}/min capacity "
              f"({purity_counts['pure']}P/{purity_counts['normal']}N/{purity_counts['impure']}I)")

    nodes_js = json.dumps(all_nodes, separators=(',', ':'))
    factories_js = json.dumps(factories, separators=(',', ':'))
    towns_js = json.dumps(mining_towns, separators=(',', ':'))

    html = TEMPLATE.replace('/*ALL_NODES*/', nodes_js)
    html = html.replace('/*FACTORIES*/', factories_js)
    html = html.replace('/*MINING_TOWNS*/', towns_js)

    out = '/Users/deepak/AI/satisfy/factory-map.html'
    with open(out, 'w') as f:
        f.write(html)
    print(f"Generated {out}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Factory Location Planner</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Courier New',monospace;display:flex;height:100vh;overflow:hidden;background:#111}
#sidebar{width:300px;background:#1a1a2e;color:#ccc;overflow-y:auto;border-right:2px solid #333;display:flex;flex-direction:column}
#sidebar h1{font-size:14px;padding:10px 12px;background:#16213e;color:#e0e0e0;letter-spacing:1px;text-transform:uppercase}
#legend{padding:8px 12px;border-bottom:1px solid #333;font-size:11px}
#legend .row{display:flex;align-items:center;gap:6px;margin:2px 0}
#legend .dot{width:10px;height:10px;border-radius:50%;display:inline-block;flex-shrink:0}
#factory-list{flex:1;overflow-y:auto;padding:0}
.factory-section{border-bottom:1px solid #333;padding:10px 12px}
.factory-header{display:flex;align-items:center;gap:8px;margin-bottom:4px}
.factory-header input[type=checkbox]{cursor:pointer;accent-color:inherit;width:14px;height:14px;flex-shrink:0}
.factory-section.hidden-factory{opacity:0.4}
.factory-section.hidden-factory .loc-option,.factory-section.hidden-factory .zoom-btn{pointer-events:none;opacity:0.3}
.factory-swatch{width:14px;height:14px;border-radius:3px;flex-shrink:0}
.factory-name{font-weight:bold;font-size:13px;color:#fff}
.factory-theme{font-size:11px;color:#888;margin-bottom:6px}
.factory-resources{font-size:10px;color:#666;margin-bottom:8px}
.loc-option{display:flex;align-items:center;gap:6px;padding:3px 0;cursor:pointer;font-size:11px}
.loc-option:hover{color:#fff}
.loc-option input{cursor:pointer;accent-color:inherit}
.loc-option .score{color:#aaa}
.loc-option .quad{color:#666;font-size:10px}
.loc-summary{font-size:10px;color:#555;margin-left:22px;margin-bottom:2px}
.zoom-btn{display:block;margin:6px 0 0 0;padding:4px 10px;background:#16213e;color:#7f8fa6;border:1px solid #333;border-radius:3px;cursor:pointer;font-size:11px;font-family:inherit}
.zoom-btn:hover{background:#1f3060;color:#fff}
#controls{padding:10px 12px;border-top:1px solid #333}
#export-btn{width:100%;padding:8px;background:#0f3460;color:#e0e0e0;border:1px solid #444;border-radius:4px;cursor:pointer;font-family:inherit;font-size:12px;font-weight:bold;letter-spacing:1px}
#export-btn:hover{background:#1a5276}
#reset-btn{width:100%;padding:6px;margin-top:6px;background:#1a1a2e;color:#7f8fa6;border:1px solid #333;border-radius:4px;cursor:pointer;font-family:inherit;font-size:11px}
#reset-btn:hover{background:#16213e;color:#fff}
canvas{flex:1;display:block;cursor:grab}
canvas.grabbing{cursor:grabbing}
#tooltip{position:fixed;background:rgba(20,20,40,0.95);color:#ddd;padding:6px 10px;border-radius:4px;font-size:11px;font-family:'Courier New',monospace;pointer-events:none;display:none;border:1px solid #444;max-width:250px;z-index:100}
</style>
</head>
<body>
<div id="sidebar">
  <h1>Factory Location Planner</h1>
  <div id="legend"></div>
  <div id="factory-list"></div>
  <div id="controls">
    <button id="export-btn">EXPORT SELECTIONS</button>
    <button id="reset-btn">Reset View</button>
  </div>
</div>
<canvas id="map"></canvas>
<div id="tooltip"></div>

<script>
// === DATA ===
const ALL_NODES = /*ALL_NODES*/;
const FACTORIES = /*FACTORIES*/;
const MINING_TOWNS = /*MINING_TOWNS*/;

// === MAP IMAGE ===
const MAP_IMG = new Image();
let mapImgLoaded = false;
MAP_IMG.onload = () => { mapImgLoaded = true; draw(); };
MAP_IMG.src = 'satisfactory-map.jpg';

// Map image covers these game coordinate bounds (from tiles.json)
const IMG_MIN_X = -324999, IMG_MAX_X = 424999;
const IMG_MIN_Y = -374999, IMG_MAX_Y = 374999;
const IMG_GAME_W = IMG_MAX_X - IMG_MIN_X; // 749998
const IMG_GAME_H = IMG_MAX_Y - IMG_MIN_Y; // 749998

// === CONSTANTS ===
const RESOURCE_COLORS = {
  iron:'#e74c3c', limestone:'#95a5a6', copper:'#e67e22', coal:'#555',
  oil:'#9b59b6', caterium:'#f1c40f', bauxite:'#e91e63', quartz:'#00bcd4',
  sulfur:'#cddc39', sam:'#2196f3', uranium:'#4caf50', nitrogen:'#80deea',
  water:'#4fc3f7'
};
const FACTORY_COLORS = {
  ferrium:'#e74c3c', naphtheon:'#9b59b6', forgeholm:'#3498db',
  luxara:'#f1c40f', cathera:'#1abc9c'
};
const PURITY_SCALE = {p:1.3, n:1.0, i:0.7};
const PURITY_ALPHA = {p:1.0, n:0.7, i:0.5};
const PURITY_LABEL = {p:'Pure', n:'Normal', i:'Impure'};

const SEARCH_RADIUS = 50000; // 500m in game units

// Zoom thresholds
const ZOOM_SHOW_BG_NODES = 0.0018;
const ZOOM_SHOW_FACTORY_NODES = 0.0015;
const ZOOM_SHOW_LINES = 0.0025;
const ZOOM_SHOW_RADIUS = 0.002;
const ZOOM_SHOW_PURITY_TEXT = 0.01;

// === STATE ===
const canvas = document.getElementById('map');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');

// Map bounds
const MAP_MIN_X = -300000, MAP_MAX_X = 420000;
const MAP_MIN_Y = -320000, MAP_MAX_Y = 320000;
const MAP_W = MAP_MAX_X - MAP_MIN_X;
const MAP_H = MAP_MAX_Y - MAP_MIN_Y;
const MAP_CX = (MAP_MIN_X + MAP_MAX_X) / 2;
const MAP_CY = (MAP_MIN_Y + MAP_MAX_Y) / 2;

let viewX = MAP_CX, viewY = MAP_CY;
let zoom = 0.001; // will be set on init
let dragging = false, dragStartX = 0, dragStartY = 0, dragViewX = 0, dragViewY = 0;
let W = 800, H = 600;

let visible = {};
for (const fid of Object.keys(FACTORIES)) { visible[fid] = true; }
let townVisible = {};
for (const mt of MINING_TOWNS) { townVisible[mt.id] = true; }

// === TRANSFORM ===
function g2s(gx, gy) {
  return {
    x: (gx - viewX) * zoom + W / 2,
    y: (gy - viewY) * zoom + H / 2,
  };
}
function s2g(sx, sy) {
  return {
    x: (sx - W / 2) / zoom + viewX,
    y: (sy - H / 2) / zoom + viewY,
  };
}

// === DRAWING ===
function draw() {
  ctx.fillStyle = '#0d1117';
  ctx.fillRect(0, 0, W, H);

  drawMapBackground();
  drawGrid();

  // Background resource nodes (faint)
  if (zoom > ZOOM_SHOW_BG_NODES) {
    drawBackgroundNodes();
  }

  // Factory data
  const fids = Object.keys(FACTORIES);
  for (const fid of fids) {
    if (!visible[fid]) continue;
    const f = FACTORIES[fid];

    if (zoom > ZOOM_SHOW_RADIUS) drawSearchRadius(fid, f);
    if (zoom > ZOOM_SHOW_LINES) drawConnections(fid, f);
    if (zoom > ZOOM_SHOW_FACTORY_NODES) drawFactoryNodes(fid, f);
  }

  // Mining towns
  for (const mt of MINING_TOWNS) {
    if (!townVisible[mt.id]) continue;
    if (zoom > ZOOM_SHOW_RADIUS) drawSearchRadius_mt(mt);
    if (zoom > ZOOM_SHOW_LINES) drawConnections_mt(mt);
    if (zoom > ZOOM_SHOW_FACTORY_NODES) drawTownNodes(mt);
  }

  // Factory centers always on top
  for (const fid of fids) {
    if (!visible[fid]) continue;
    const f = FACTORIES[fid];
    drawFactoryCenter(fid, f);
  }

  // Mining town centers on top
  for (const mt of MINING_TOWNS) {
    if (!townVisible[mt.id]) continue;
    drawTownCenter(mt);
  }
}

function drawMapBackground() {
  if (!mapImgLoaded) return;
  const tl = g2s(IMG_MIN_X, IMG_MIN_Y);
  const screenW = IMG_GAME_W * zoom;
  const screenH = IMG_GAME_H * zoom;
  ctx.drawImage(MAP_IMG, tl.x, tl.y, screenW, screenH);
}

function drawGrid() {
  // Draw faint grid lines at 100k game unit intervals (1km)
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.lineWidth = 1;
  const step = 100000;
  const tlg = s2g(0, 0);
  const brg = s2g(W, H);
  const startX = Math.floor(tlg.x / step) * step;
  const startY = Math.floor(tlg.y / step) * step;
  ctx.beginPath();
  for (let gx = startX; gx <= brg.x; gx += step) {
    const s = g2s(gx, 0);
    ctx.moveTo(s.x, 0);
    ctx.lineTo(s.x, H);
  }
  for (let gy = startY; gy <= brg.y; gy += step) {
    const s = g2s(0, gy);
    ctx.moveTo(0, s.y);
    ctx.lineTo(W, s.y);
  }
  ctx.stroke();
}

function drawBackgroundNodes() {
  const tlg = s2g(0, 0);
  const brg = s2g(W, H);
  for (const n of ALL_NODES) {
    // Frustum cull
    if (n.x < tlg.x - 5000 || n.x > brg.x + 5000) continue;
    if (n.y < tlg.y - 5000 || n.y > brg.y + 5000) continue;
    const s = g2s(n.x, n.y);
    const r = 2 * PURITY_SCALE[n.p];
    ctx.globalAlpha = 0.15 * PURITY_ALPHA[n.p];
    ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
    ctx.beginPath();
    ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

function drawSearchRadius(fid, f) {
  const s = g2s(f.cx, f.cy);
  const r = SEARCH_RADIUS * zoom;
  ctx.strokeStyle = FACTORY_COLORS[fid] + '30';
  ctx.lineWidth = 1;
  ctx.setLineDash([6, 4]);
  ctx.beginPath();
  ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawConnections(fid, f) {
  const sc = g2s(f.cx, f.cy);
  ctx.strokeStyle = FACTORY_COLORS[fid] + '40';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (const n of f.nodes) {
    const sn = g2s(n.x, n.y);
    ctx.moveTo(sc.x, sc.y);
    ctx.lineTo(sn.x, sn.y);
  }
  ctx.stroke();
}

function drawFactoryNodes(fid, f) {
  const color = FACTORY_COLORS[fid];
  for (const n of f.nodes) {
    const s = g2s(n.x, n.y);
    const baseR = 4 * PURITY_SCALE[n.p];

    // Filled dot in resource color
    ctx.globalAlpha = PURITY_ALPHA[n.p];
    ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR, 0, Math.PI * 2);
    ctx.fill();

    // Ring in factory color
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR + 1.5, 0, Math.PI * 2);
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Purity + type label at high zoom
    if (zoom > ZOOM_SHOW_PURITY_TEXT) {
      ctx.font = '9px Courier New';
      const label = PURITY_LABEL[n.p] + ' ' + n.t;
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 2;
      ctx.strokeText(label, s.x + baseR + 4, s.y + 3);
      ctx.fillStyle = '#ddd';
      ctx.fillText(label, s.x + baseR + 4, s.y + 3);
    }
  }
}

function drawFactoryCenter(fid, f) {
  const s = g2s(f.cx, f.cy);
  const color = FACTORY_COLORS[fid];
  const r = Math.max(8, 12 / Math.max(zoom / 0.001, 0.5));

  // Outer glow
  ctx.fillStyle = color + '30';
  ctx.beginPath();
  ctx.arc(s.x, s.y, r + 4, 0, Math.PI * 2);
  ctx.fill();

  // Main circle
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
  ctx.fill();

  // Border
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
  ctx.stroke();

  // Label
  ctx.font = 'bold 12px Courier New';
  ctx.textAlign = 'center';
  ctx.strokeStyle = '#000';
  ctx.lineWidth = 3;
  ctx.strokeText(f.name, s.x, s.y - r - 8);
  ctx.fillStyle = '#fff';
  ctx.fillText(f.name, s.x, s.y - r - 8);
  ctx.textAlign = 'left';
}

// === MINING TOWN DRAWING ===
function drawSearchRadius_mt(mt) {
  const s = g2s(mt.cx, mt.cy);
  const r = SEARCH_RADIUS * zoom;
  ctx.strokeStyle = mt.color + '30';
  ctx.lineWidth = 1;
  ctx.setLineDash([6, 4]);
  ctx.beginPath();
  ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawConnections_mt(mt) {
  const sc = g2s(mt.cx, mt.cy);
  ctx.strokeStyle = mt.color + '40';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (const n of mt.nodes) {
    const sn = g2s(n.x, n.y);
    ctx.moveTo(sc.x, sc.y);
    ctx.lineTo(sn.x, sn.y);
  }
  ctx.stroke();
}

function drawTownNodes(mt) {
  for (const n of mt.nodes) {
    const s = g2s(n.x, n.y);
    const baseR = 4 * PURITY_SCALE[n.p];
    ctx.globalAlpha = PURITY_ALPHA[n.p];
    ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = mt.color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR + 1.5, 0, Math.PI * 2);
    ctx.stroke();
    ctx.globalAlpha = 1;
    if (zoom > ZOOM_SHOW_PURITY_TEXT) {
      ctx.font = '9px Courier New';
      const label = PURITY_LABEL[n.p] + ' ' + n.t;
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 2;
      ctx.strokeText(label, s.x + baseR + 4, s.y + 3);
      ctx.fillStyle = '#ddd';
      ctx.fillText(label, s.x + baseR + 4, s.y + 3);
    }
  }
}

function drawTownCenter(mt) {
  const s = g2s(mt.cx, mt.cy);
  const r = Math.max(8, 12 / Math.max(zoom / 0.001, 0.5));

  // Outer glow
  ctx.fillStyle = mt.color + '30';
  ctx.save();
  ctx.translate(s.x, s.y);
  ctx.rotate(Math.PI / 4);
  ctx.fillRect(-r - 4, -r - 4, (r + 4) * 2, (r + 4) * 2);
  ctx.restore();

  // Diamond shape
  ctx.fillStyle = mt.color;
  ctx.save();
  ctx.translate(s.x, s.y);
  ctx.rotate(Math.PI / 4);
  ctx.fillRect(-r, -r, r * 2, r * 2);
  ctx.restore();

  // Border
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 2;
  ctx.save();
  ctx.translate(s.x, s.y);
  ctx.rotate(Math.PI / 4);
  ctx.strokeRect(-r, -r, r * 2, r * 2);
  ctx.restore();

  // Label
  ctx.font = 'bold 12px Courier New';
  ctx.textAlign = 'center';
  ctx.strokeStyle = '#000';
  ctx.lineWidth = 3;
  ctx.strokeText(mt.name, s.x, s.y - r - 10);
  ctx.fillStyle = '#fff';
  ctx.fillText(mt.name, s.x, s.y - r - 10);

  // Pickaxe icon text inside
  ctx.font = 'bold 9px Courier New';
  ctx.fillStyle = '#000';
  ctx.fillText('\u26CF', s.x, s.y + 4);
  ctx.textAlign = 'left';
}

// === SIDEBAR ===
function buildLegend() {
  const el = document.getElementById('legend');
  let html = '<div style="font-weight:bold;margin-bottom:4px;color:#fff;font-size:12px">Resource Types</div>';
  const types = ['iron','limestone','copper','coal','oil','caterium','bauxite','quartz','sulfur','sam','uranium'];
  for (const t of types) {
    html += `<div class="row"><span class="dot" style="background:${RESOURCE_COLORS[t]}"></span>${t}</div>`;
  }
  html += '<div style="margin-top:6px;font-weight:bold;color:#fff;font-size:12px">Purity</div>';
  html += '<div class="row"><span class="dot" style="background:#ccc;width:13px;height:13px"></span>Pure (large)</div>';
  html += '<div class="row"><span class="dot" style="background:#ccc;width:10px;height:10px"></span>Normal</div>';
  html += '<div class="row"><span class="dot" style="background:#ccc;width:7px;height:7px"></span>Impure (small)</div>';
  el.innerHTML = html;
}

function buildSidebar() {
  const el = document.getElementById('factory-list');
  let html = '';
  for (const [fid, f] of Object.entries(FACTORIES)) {
    const color = FACTORY_COLORS[fid];
    const resSummary = Object.entries(f.resources).map(([rt, rd]) =>
      `${rt}: ${rd.pure}P/${rd.normal}N/${rd.impure}I`
    ).join(', ');
    html += `<div class="factory-section" id="fsec-${fid}">`;
    html += `<div class="factory-header"><input type="checkbox" checked onchange="toggleVis('${fid}',this.checked)" style="accent-color:${color}"><span class="factory-swatch" style="background:${color}"></span><span class="factory-name">${f.name}</span></div>`;
    html += `<div class="factory-theme">${f.theme}</div>`;
    html += `<div class="factory-resources">${f.totalNodes} nodes: ${resSummary}</div>`;
    html += `<button class="zoom-btn" onclick="zoomTo('${fid}')">Zoom to ${f.name} &rarr;</button>`;
    html += `</div>`;
  }

  // Mining towns
  html += '<div style="padding:8px 12px;border-bottom:1px solid #333;font-weight:bold;font-size:12px;color:#fff;background:#16213e;letter-spacing:1px;text-transform:uppercase">Mining Towns</div>';
  for (const mt of MINING_TOWNS) {
    html += `<div class="factory-section" id="tsec-${mt.id}">`;
    html += `<div class="factory-header"><input type="checkbox" checked onchange="toggleTownVis('${mt.id}',this.checked)" style="accent-color:${mt.color}"><span class="factory-swatch" style="background:${mt.color};transform:rotate(45deg)"></span><span class="factory-name">${mt.name}</span></div>`;
    html += `<div class="factory-theme">${mt.theme}</div>`;
    html += `<div class="factory-resources">${mt.nodeCount} ${mt.resource} nodes | ${mt.capacity}/min capacity</div>`;
    html += `<div class="factory-resources">${mt.purity.pure}P / ${mt.purity.normal}N / ${mt.purity.impure}I</div>`;
    html += `<div class="factory-resources" style="margin-top:4px">Supplies:</div>`;
    for (const s of mt.supplies) {
      html += `<div class="factory-resources" style="color:#aaa">&nbsp;&bull; ${s}</div>`;
    }
    html += `<button class="zoom-btn" onclick="zoomToTown('${mt.id}')">Zoom to ${mt.name} &rarr;</button>`;
    html += `</div>`;
  }

  el.innerHTML = html;
}

function toggleVis(fid, on) {
  visible[fid] = on;
  document.getElementById('fsec-' + fid).classList.toggle('hidden-factory', !on);
  draw();
}

function zoomTo(fid) {
  const f = FACTORIES[fid];
  viewX = f.cx;
  viewY = f.cy;
  zoom = 0.004;
  draw();
}

function toggleTownVis(tid, on) {
  townVisible[tid] = on;
  document.getElementById('tsec-' + tid).classList.toggle('hidden-factory', !on);
  draw();
}

function zoomToTown(tid) {
  const mt = MINING_TOWNS.find(t => t.id === tid);
  if (!mt) return;
  viewX = mt.cx;
  viewY = mt.cy;
  zoom = 0.004;
  draw();
}

function resetView() {
  viewX = MAP_CX;
  viewY = MAP_CY;
  fitZoom();
  draw();
}

function exportSelections() {
  const result = {
    meta: {
      description: 'Selected factory and mining town locations for Satisfactory',
      exported_at: new Date().toISOString(),
      coordinate_system: {
        x: 'positive = east/right',
        y: 'positive = south/bottom',
        units: 'centimeters (100 units = 1 meter)'
      }
    },
    selections: {}
  };
  for (const [fid, f] of Object.entries(FACTORIES)) {
    result.selections[fid] = {
      factory_name: f.name,
      theme: f.theme,
      center: {x: f.cx, y: f.cy},
      required_resources: f.req,
      total_nodes: f.totalNodes,
      resources: f.resources,
      nodes: f.nodes,
    };
  }
  for (const mt of MINING_TOWNS) {
    result.selections[mt.id] = {
      factory_name: mt.name,
      theme: mt.theme,
      type: 'mining_town',
      center: {x: mt.cx, y: mt.cy},
      required_resources: [mt.resource],
      total_nodes: mt.nodeCount,
      capacity_per_min: mt.capacity,
      supplies: mt.supplies,
      purity: mt.purity,
      nodes: mt.nodes,
    };
  }
  const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'selected-factory-locations.json';
  a.click();
  URL.revokeObjectURL(url);
}

// === INTERACTION ===
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const mg = s2g(e.offsetX, e.offsetY);
  const factor = e.deltaY > 0 ? 0.88 : 1.14;
  zoom = Math.max(0.0003, Math.min(0.05, zoom * factor));
  viewX = mg.x - (e.offsetX - W / 2) / zoom;
  viewY = mg.y - (e.offsetY - H / 2) / zoom;
  draw();
}, {passive: false});

canvas.addEventListener('mousedown', (e) => {
  if (e.button === 0) {
    dragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragViewX = viewX;
    dragViewY = viewY;
    canvas.classList.add('grabbing');
  }
});

window.addEventListener('mousemove', (e) => {
  if (dragging) {
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    viewX = dragViewX - dx / zoom;
    viewY = dragViewY - dy / zoom;
    draw();
  }
  // Tooltip for factory centers
  if (!dragging) {
    const mg = s2g(e.clientX - canvas.getBoundingClientRect().left,
                    e.clientY - canvas.getBoundingClientRect().top);
    let hit = null;
    for (const [fid, f] of Object.entries(FACTORIES)) {
      if (!visible[fid]) continue;
      const dx = mg.x - f.cx, dy = mg.y - f.cy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const hitR = 15 / zoom;
      if (dist < hitR) { hit = {fid, f}; break; }
    }
    // Also check mining towns
    let hitTown = null;
    if (!hit) {
      for (const mt of MINING_TOWNS) {
        if (!townVisible[mt.id]) continue;
        const dx = mg.x - mt.cx, dy = mg.y - mt.cy;
        const d = Math.sqrt(dx * dx + dy * dy);
        const hitR = 15 / zoom;
        if (d < hitR) { hitTown = mt; break; }
      }
    }
    if (hit) {
      const {f} = hit;
      let tt = `<b>${f.name}</b> (${f.theme})<br>`;
      tt += `${f.totalNodes} resource nodes`;
      tooltip.innerHTML = tt;
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX + 14) + 'px';
      tooltip.style.top = (e.clientY + 14) + 'px';
    } else if (hitTown) {
      let tt = `<b>${hitTown.name}</b> (${hitTown.theme})<br>`;
      tt += `${hitTown.nodeCount} ${hitTown.resource} nodes | ${hitTown.capacity}/min<br>`;
      tt += `${hitTown.purity.pure}P / ${hitTown.purity.normal}N / ${hitTown.purity.impure}I<br>`;
      tt += `Supplies: ${hitTown.supplies.join(', ')}`;
      tooltip.innerHTML = tt;
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX + 14) + 'px';
      tooltip.style.top = (e.clientY + 14) + 'px';
    } else {
      tooltip.style.display = 'none';
    }
  }
});

window.addEventListener('mouseup', () => {
  dragging = false;
  canvas.classList.remove('grabbing');
});

document.getElementById('export-btn').addEventListener('click', exportSelections);
document.getElementById('reset-btn').addEventListener('click', resetView);

// Keyboard shortcuts
window.addEventListener('keydown', (e) => {
  if (e.key === 'r') resetView();
  if (e.key === 'e') exportSelections();
  const fids = Object.keys(FACTORIES);
  const num = parseInt(e.key);
  if (num >= 1 && num <= fids.length) zoomTo(fids[num - 1]);
});

// === INIT ===
function fitZoom() {
  zoom = Math.min(W / MAP_W, H / MAP_H) * 0.9;
}

function resize() {
  const rect = canvas.getBoundingClientRect();
  W = rect.width;
  H = rect.height;
  canvas.width = W;
  canvas.height = H;
}

function init() {
  resize();
  fitZoom();
  buildLegend();
  buildSidebar();
  draw();
}

window.addEventListener('resize', () => { resize(); draw(); });
init();
</script>
</body>
</html>
"""

if __name__ == '__main__':
    main()
