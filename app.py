"""
PhotonField :: Spektral Konstellasyon Web Arayüzü
"""

import io
import base64

from flask import Flask, render_template_string, request, jsonify
from PIL import Image

import photonfield as pf

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB upload


HTML = '''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#06060f">
<title>PhotonField :: Spektral Konstellasyon</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@450;600&family=Outfit:wght@400..800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-deep: #06060f;
    --bg: #0c0c18;
    --bg2: #121228;
    --bg3: #1a1a36;
    --bg4: #232348;
    --panel: rgba(14, 14, 32, 0.94);
    --border: rgba(140, 120, 255, 0.22);
    --border2: rgba(58, 232, 255, 0.18);
    --text: #f0f2ff;
    --text2: #9a9ab8;
    --text3: #656584;
    --accent: #3ae8ff;
    --accent-hot: #ff3edc;
    --accent-dim: #1cb8d4;
    --r-glow: #ff5c8a;
    --g-glow: #5cff9d;
    --b-glow: #78a8ff;
    --success: #3dff9a;
    --danger: #ff6b8a;
    --info: #8eb8ff;
    --warn: #ffc94d;
    --radius: 16px;
    --font-display: "Outfit", system-ui, sans-serif;
    --font-sans: "Outfit", system-ui, sans-serif;
    --font-mono: "IBM Plex Mono", ui-monospace, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--font-sans);
    font-size: 15px;
    line-height: 1.55;
    letter-spacing: -0.02em;
    color: var(--text);
    background: var(--bg-deep);
    min-height: 100vh;
    background-image:
      radial-gradient(ellipse 90% 70% at 8% -5%, rgba(255, 62, 220, 0.14), transparent 48%),
      radial-gradient(ellipse 75% 55% at 92% 8%, rgba(58, 232, 255, 0.11), transparent 45%),
      radial-gradient(ellipse 65% 85% at 50% 105%, rgba(90, 70, 200, 0.09), transparent 52%);
  }

  .shell { max-width: 1120px; margin: 0 auto; padding: 22px 18px 56px; position: relative; }

  header { margin-bottom: 0; }

  .hero-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 24px;
    align-items: center;
    margin-bottom: 26px;
    padding: 26px 22px 28px;
    border-radius: calc(var(--radius) + 10px);
    background: linear-gradient(155deg, rgba(30, 28, 58, 0.65), rgba(10, 10, 26, 0.92));
    border: 1px solid var(--border);
    box-shadow:
      0 0 0 1px rgba(58, 232, 255, 0.06),
      0 28px 70px rgba(0, 0, 0, 0.55),
      inset 0 1px 0 rgba(255, 255, 255, 0.07);
  }
  @media (min-width: 900px) {
    .hero-grid {
      grid-template-columns: 1fr minmax(200px, 260px);
      gap: 36px;
      padding: 34px 38px 36px;
    }
  }

  .hero-main { min-width: 0; }

  .hero-visual {
    display: none;
    justify-content: center;
    align-items: center;
    min-height: 200px;
  }
  @media (min-width: 900px) {
    .hero-visual { display: flex; }
  }

  .spectrum-wrap {
    position: relative;
    width: 210px;
    height: 210px;
  }
  .spectrum-art {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: conic-gradient(
      from 200deg,
      var(--accent-hot),
      var(--accent),
      var(--b-glow),
      var(--g-glow),
      var(--r-glow),
      var(--accent-hot)
    );
    opacity: 0.88;
    animation: spin-slow 32s linear infinite;
    box-shadow:
      0 0 70px rgba(255, 62, 220, 0.28),
      0 0 45px rgba(58, 232, 255, 0.18),
      inset 0 0 50px rgba(0, 0, 0, 0.45);
  }
  .spectrum-art::after {
    content: "";
    position: absolute;
    inset: 24%;
    border-radius: 50%;
    background: var(--bg-deep);
    border: 2px solid rgba(58, 232, 255, 0.45);
    box-shadow: inset 0 0 50px rgba(0, 0, 0, 0.65);
  }
  @keyframes spin-slow {
    to { transform: rotate(360deg); }
  }

  .logo-row { display: flex; align-items: center; gap: 18px; margin-bottom: 10px; }
  .logo-box {
    width: 64px;
    height: 64px;
    border-radius: 18px;
    background: linear-gradient(135deg, var(--accent-hot), var(--accent));
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow:
      0 0 48px rgba(255, 62, 220, 0.4),
      0 0 28px rgba(58, 232, 255, 0.22),
      inset 0 1px 0 rgba(255, 255, 255, 0.22);
  }
  .logo-box svg {
    width: 34px;
    height: 34px;
    filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.35));
  }

  h1 {
    font-family: var(--font-display);
    font-size: clamp(2rem, 5.5vw, 2.85rem);
    font-weight: 800;
    letter-spacing: -0.045em;
    line-height: 1.02;
    background: linear-gradient(100deg, #fff 5%, var(--accent) 52%, var(--accent-hot) 95%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  h1 em {
    font-style: normal;
    font-weight: 800;
    background: linear-gradient(90deg, var(--accent), var(--accent-hot));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .tagline {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    color: var(--accent);
    letter-spacing: 0.17em;
    text-transform: uppercase;
    margin-top: 8px;
    opacity: 0.92;
  }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(124px, 1fr));
    gap: 10px;
    margin-top: 20px;
  }
  .stat {
    font-size: 11px;
    color: var(--text2);
    padding: 13px 13px;
    background: rgba(6, 6, 18, 0.72);
    border: 1px solid var(--border2);
    border-radius: 12px;
    backdrop-filter: blur(10px);
  }
  .stat strong {
    font-family: var(--font-mono);
    color: var(--accent);
    font-size: 13px;
    display: block;
    margin-bottom: 6px;
    font-weight: 600;
    text-shadow: 0 0 22px rgba(58, 232, 255, 0.35);
  }

  .hero-copy {
    margin-top: 18px;
    max-width: 52rem;
    color: var(--text2);
    font-size: 0.94rem;
    line-height: 1.68;
  }
  .hero-copy strong { color: var(--text); font-weight: 600; }

  .chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
  .chip {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 500;
    padding: 8px 13px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: rgba(8, 8, 22, 0.88);
    color: var(--text2);
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .chip.ok {
    border-color: rgba(61, 255, 154, 0.42);
    color: var(--success);
    box-shadow: 0 0 18px rgba(61, 255, 154, 0.1);
  }

  .workspace {
    border-radius: calc(var(--radius) + 8px);
    padding: 3px;
    background: linear-gradient(
      125deg,
      rgba(255, 62, 220, 0.55),
      rgba(58, 232, 255, 0.42),
      rgba(120, 90, 255, 0.48)
    );
    margin-bottom: 10px;
    box-shadow: 0 28px 90px rgba(0, 0, 0, 0.5);
  }
  .workspace-inner {
    background: var(--panel);
    border-radius: var(--radius);
    padding: 18px 18px 24px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    backdrop-filter: blur(14px);
  }

  .tabs {
    display: flex;
    gap: 8px;
    background: rgba(8, 8, 24, 0.92);
    border: 1px solid var(--border2);
    border-radius: 14px;
    padding: 8px;
    margin: 0 0 20px;
  }
  .tab {
    flex: 1;
    padding: 14px 14px;
    font-size: 11px;
    font-weight: 700;
    text-align: center;
    cursor: pointer;
    background: transparent;
    border: 1px solid transparent;
    color: var(--text3);
    border-radius: 11px;
    transition: color 0.2s, background 0.2s, box-shadow 0.2s, border-color 0.2s;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-family: var(--font-display);
  }
  .tab.active {
    background: linear-gradient(135deg, rgba(58, 232, 255, 0.2), rgba(255, 62, 220, 0.14));
    color: var(--text);
    border: 1px solid rgba(58, 232, 255, 0.35);
    box-shadow:
      0 0 28px rgba(58, 232, 255, 0.12),
      inset 0 1px 0 rgba(255, 255, 255, 0.08);
  }
  .tab:hover:not(.active) {
    color: var(--text2);
    background: rgba(255, 255, 255, 0.045);
  }

  .panel { display: none; }
  .panel.active { display: block; }

  /* Drop zone */
  .drop-zone {
    border: 2px dashed rgba(58, 232, 255, 0.22);
    border-radius: var(--radius);
    padding: 48px 24px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.25s, background 0.25s, box-shadow 0.25s;
    background: rgba(8, 8, 26, 0.65);
    margin-bottom: 18px;
  }
  .drop-zone:hover, .drop-zone.drag {
    border-color: rgba(255, 62, 220, 0.55);
    background: rgba(40, 12, 48, 0.35);
    box-shadow: 0 0 40px rgba(58, 232, 255, 0.08), inset 0 0 60px rgba(255, 62, 220, 0.04);
  }
  .drop-icon { font-size: 38px; margin-bottom: 10px; opacity: 0.85; }
  .drop-zone p { font-size: 14px; color: var(--text2); }
  .drop-zone strong { color: var(--text); }
  .drop-zone small { font-size: 11px; color: var(--text3); display: block; margin-top: 6px; }

  .file-pill {
    background: var(--bg3); border: 1px solid var(--border2);
    border-radius: 8px; padding: 12px 16px; display: none;
    align-items: center; gap: 12px; margin-bottom: 18px;
  }
  .file-pill.show { display: flex; }
  .file-pill .name { flex: 1; font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .file-pill .size { font-size: 11px; color: var(--text2); }
  .file-pill .remove { background: none; border: none; color: var(--text3); cursor: pointer; font-size: 18px; padding: 2px 6px; }
  .file-pill .remove:hover { color: var(--danger); }

  .btn {
    padding: 14px 22px; border: none; border-radius: var(--radius);
    font-size: 13px; font-weight: 700; cursor: pointer; transition: all 0.15s;
    font-family: inherit; text-transform: uppercase; letter-spacing: 0.07em;
    display: inline-flex; align-items: center; gap: 8px;
  }
  .btn-primary {
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 55%, var(--accent-hot) 130%);
    color: #061018;
    width: 100%;
    justify-content: center;
    font-size: 14px;
    font-weight: 800;
    box-shadow: 0 4px 28px rgba(58, 232, 255, 0.22), 0 2px 12px rgba(255, 62, 220, 0.12);
  }
  .btn-primary:hover {
    filter: brightness(1.07);
    box-shadow: 0 6px 36px rgba(58, 232, 255, 0.3);
  }
  .btn-primary:disabled { opacity: 0.3; cursor: not-allowed; }
  .btn-ghost { background: var(--bg3); color: var(--text); border: 1px solid var(--border2); }
  .btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
  .btn-success { background: var(--success); color: #000; }
  .btn-success:hover { opacity: 0.85; }

  /* Progress */
  .progress { margin: 18px 0; display: none; }
  .progress.show { display: block; }
  .progress-label { font-size: 12px; color: var(--text2); margin-bottom: 8px; }
  .progress-track { background: var(--bg3); border-radius: 4px; height: 3px; overflow: hidden; position: relative; }
  .progress-fill { height: 3px; background: linear-gradient(90deg, var(--accent-hot), var(--accent)); border-radius: 4px; transition: width 0.4s; }
  .progress-fill.indeterminate {
    width: 30%;
    animation: indeterminate 1.5s infinite linear;
    position: absolute; top: 0; left: 0;
  }
  @keyframes indeterminate {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
  }

  /* Symbol view */
  .symbol-frame {
    background: rgba(6, 6, 22, 0.85);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 18px;
    margin-top: 22px;
    position: relative;
    box-shadow: 0 0 50px rgba(255, 62, 220, 0.06), 0 0 40px rgba(58, 232, 255, 0.05);
  }
  .symbol-frame img {
    width: 100%; display: block;
    border-radius: 8px; image-rendering: -webkit-optimize-contrast;
  }
  .symbol-meta {
    margin-top: 14px; display: flex; align-items: center;
    justify-content: space-between; gap: 12px;
  }
  .symbol-tag {
    display: inline-block; padding: 4px 10px;
    background: var(--bg3); border: 1px solid var(--border2);
    border-radius: 20px; font-size: 10px; font-weight: 700;
    color: var(--text2); letter-spacing: 0.1em; text-transform: uppercase;
  }
  .channel-pills { display: flex; gap: 6px; }
  .ch-pill { width: 10px; height: 10px; border-radius: 50%; box-shadow: 0 0 8px currentColor; }
  .ch-pill.r { background: var(--r-glow); color: var(--r-glow); }
  .ch-pill.g { background: var(--g-glow); color: var(--g-glow); }
  .ch-pill.b { background: var(--b-glow); color: var(--b-glow); }
  .ch-pill.off { background: var(--bg4); color: transparent; box-shadow: none; }

  /* Info grid */
  .info-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 10px; margin-top: 18px;
  }
  .info-card {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 8px; padding: 12px 14px;
  }
  .info-card .key { font-size: 10px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }
  .info-card .val { font-family: var(--font-mono); font-size: 13px; font-weight: 600; color: var(--accent); }
  .info-card .val.ok { color: var(--success); }
  .info-card .val.warn { color: var(--warn); }

  /* Bilgi bölümü */
  .edu {
    margin-top: 48px;
    padding-top: 36px;
    border-top: 1px solid rgba(58, 232, 255, 0.12);
  }
  .edu-heading {
    font-family: var(--font-display);
    font-size: 1.45rem;
    font-weight: 800;
    letter-spacing: -0.035em;
    margin-bottom: 10px;
    background: linear-gradient(95deg, var(--text), var(--accent));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  .edu-lead { color: var(--text2); font-size: 0.92rem; max-width: 42rem; margin-bottom: 28px; line-height: 1.65; }
  .edu-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px; margin-bottom: 22px;
  }
  .edu-card {
    background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 20px 22px;
  }
  .edu-card.pos { border-left: 3px solid var(--success); }
  .edu-card.neg { border-left: 3px solid var(--danger); }
  .edu-card h3 {
    font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em;
    color: var(--text3); margin-bottom: 14px;
  }
  .edu-card ul { list-style: none; }
  .edu-card li {
    position: relative; padding-left: 18px; margin-bottom: 10px;
    color: var(--text2); font-size: 0.9rem; line-height: 1.55;
  }
  .edu-card li:last-child { margin-bottom: 0; }
  .edu-card.pos li::before {
    content: ""; position: absolute; left: 0; top: 0.55em; width: 6px; height: 6px;
    border-radius: 50%; background: var(--success); opacity: 0.85;
  }
  .edu-card.neg li::before {
    content: ""; position: absolute; left: 0; top: 0.55em; width: 6px; height: 6px;
    border-radius: 50%; background: var(--danger); opacity: 0.75;
  }

  details.learn {
    background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius);
    margin-bottom: 12px; overflow: hidden;
  }
  details.learn summary {
    cursor: pointer; padding: 16px 20px; font-weight: 700; font-size: 0.92rem;
    list-style: none; display: flex; align-items: center; justify-content: space-between;
  }
  details.learn summary::-webkit-details-marker { display: none; }
  details.learn summary::after {
    content: "▼"; font-size: 10px; color: var(--text3); transition: transform 0.2s;
  }
  details.learn[open] summary::after { transform: rotate(-180deg); }
  details.learn .learn-body {
    padding: 0 20px 18px; color: var(--text2); font-size: 0.88rem; line-height: 1.65;
    border-top: 1px solid var(--border);
  }
  details.learn .learn-body ol { margin: 12px 0 0 1.1rem; }
  details.learn .learn-body li { margin-bottom: 8px; }

  .cap-wrap { overflow-x: auto; margin-top: 10px; border-radius: 10px; border: 1px solid var(--border); }
  .cap-table {
    width: 100%; border-collapse: collapse; font-family: var(--font-mono); font-size: 12px;
  }
  .cap-table th, .cap-table td {
    padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border);
  }
  .cap-table th { color: var(--text3); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; font-size: 10px; }
  .cap-table tr:last-child td { border-bottom: none; }
  .cap-table td:last-child { color: var(--accent); font-weight: 600; }

  .panel-intro {
    font-size: 0.9rem;
    color: var(--text2);
    margin-bottom: 16px;
    line-height: 1.58;
    padding: 16px 18px;
    background: rgba(58, 232, 255, 0.06);
    border-radius: 12px;
    border: 1px solid rgba(58, 232, 255, 0.14);
  }
  .panel-intro strong { color: var(--text); font-weight: 600; }

  .site-footer {
    margin-top: 40px; padding-top: 24px; border-top: 1px solid var(--border);
    font-size: 11px; color: var(--text3); font-family: var(--font-mono);
    line-height: 1.7;
  }

  .result-box {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 28px; text-align: center;
    display: none; margin-top: 18px;
  }
  .result-box.show { display: block; }
  .result-icon { font-size: 48px; margin-bottom: 10px; }
  .result-name { font-size: 18px; font-weight: 700; margin-bottom: 4px; word-break: break-all; }
  .result-size { font-size: 12px; color: var(--text2); margin-bottom: 18px; }
  .checksum-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 11px; font-weight: 700; margin-bottom: 18px;
  }
  .badge-ok { background: #00e87a20; color: var(--success); border: 1px solid #00e87a40; }
  .badge-warn { background: #ffaa0020; color: var(--warn); border: 1px solid #ffaa0040; }

  /* Decode upload */
  .decode-zone {
    background: rgba(8, 8, 28, 0.72);
    border: 2px dashed rgba(140, 120, 255, 0.28);
    border-radius: var(--radius);
    padding: 32px 20px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
    margin-bottom: 18px;
    min-height: 180px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }
  .decode-zone:hover {
    border-color: rgba(255, 62, 220, 0.45);
    background: rgba(36, 10, 42, 0.35);
    box-shadow: inset 0 0 40px rgba(58, 232, 255, 0.04);
  }
  .decode-zone.loaded {
    border-style: solid;
    border-color: rgba(61, 255, 154, 0.55);
    background: rgba(4, 28, 22, 0.55);
    padding: 12px;
  }
  .dec-label {
    font-size: 13px;
    font-weight: 800;
    color: var(--accent);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-family: var(--font-display);
  }
  .dec-hint { font-size: 11px; color: var(--text3); font-family: var(--font-mono); }
  .decode-zone img { width: 100%; max-width: 320px; border-radius: 8px; }

  /* Log */
  .log { font-size: 11px; color: var(--text2); margin-top: 14px; line-height: 2; text-align: left; }
  .log .ok { color: var(--success); }
  .log .err { color: var(--danger); }
  .log .info { color: var(--info); }
  .log .warn { color: var(--warn); }

  /* Error */
  .error-box {
    background: #1a0000; border: 1px solid #ff404040;
    border-radius: var(--radius); padding: 14px 18px;
    color: var(--danger); font-size: 13px; display: none; margin-top: 14px;
    line-height: 1.6; white-space: pre-wrap;
  }
  .error-box.show { display: block; }
  .error-box.soft {
    background: rgba(6, 28, 42, 0.65);
    border-color: rgba(58, 232, 255, 0.35);
    color: var(--info);
  }

  .pw-row { margin-top: 18px; text-align: left; }
  .pw-row label {
    display: block;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 8px;
    font-family: var(--font-display);
  }
  .pw-field {
    width: 100%;
    max-width: 420px;
    box-sizing: border-box;
    padding: 12px 14px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: rgba(8, 8, 22, 0.85);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 13px;
    margin-bottom: 10px;
  }
  .pw-field:focus {
    outline: none;
    border-color: rgba(58, 232, 255, 0.45);
    box-shadow: 0 0 0 1px rgba(58, 232, 255, 0.2);
  }
  .pw-hint {
    display: block;
    font-size: 11px;
    color: var(--text3);
    line-height: 1.5;
    max-width: 520px;
  }

  hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }

  @media (max-width: 600px) {
    .info-grid { grid-template-columns: 1fr 1fr; }
    .stats-row { grid-template-columns: 1fr 1fr; }
    .tabs { flex-direction: column; }
  }
</style>
</head>
<body>
<div class="shell">

  <header>
    <div class="hero-grid">
      <div class="hero-main">
        <div class="logo-row">
          <div class="logo-box">
            <svg viewBox="0 0 24 24" fill="none" stroke="#061018" stroke-width="2.2" stroke-linecap="round">
              <circle cx="12" cy="12" r="2.5" fill="#061018"/>
              <circle cx="12" cy="12" r="6" stroke-dasharray="2 2"/>
              <circle cx="12" cy="12" r="10" stroke-dasharray="1 3"/>
            </svg>
          </div>
          <div>
            <h1>Photon<em>Field</em></h1>
            <div class="tagline">Spektral konstellasyon · FFT faz kodlama</div>
          </div>
        </div>
        <div class="stats-row">
          <div class="stat"><strong>~{{ capacity_kb }} KB</strong>Maks PNG kapasitesi</div>
          <div class="stat"><strong>Adaptif</strong>{{ size_min }}→{{ size_max }} px</div>
          <div class="stat"><strong>3 kanal</strong>RGB spektral</div>
          <div class="stat"><strong>~{{ cells_max }}</strong>Maks frekans hücresi</div>
          <div class="stat"><strong>RS-{{ rs_parity }}</strong>Hata düzeltme</div>
        </div>

        <p class="hero-copy">
          <strong>PhotonField</strong>, dosyanızı tek bir RGB görsel içinde taşıyan deneysel bir kodlayıcıdır.
          Bilgi piksellerde değil; spektrumda — her frekans hücresinin <strong>fazında</strong> saklanır.
          Üç renk kanalı (R, G, B) birbirinden bağımsız taşıyıcıdır; görsel boyutu veriye göre otomatik seçilir.
        </p>
        <div class="chip-row">
          <span class="chip ok">İnternet gerektirmez</span>
          <span class="chip">ZLIB + Reed-Solomon</span>
          <span class="chip">16 faz · Gray kod</span>
          <span class="chip">Adaptif {{ size_min }}–{{ size_max }} px</span>
        </div>
      </div>
      <div class="hero-visual" aria-hidden="true">
        <div class="spectrum-wrap">
          <div class="spectrum-art"></div>
        </div>
      </div>
    </div>
  </header>

  <div class="workspace">
    <div class="workspace-inner">
      <div class="tabs">
    <button class="tab active" onclick="switchTab(event, 'encode')">⚡ Dosya → PhotonField</button>
    <button class="tab" onclick="switchTab(event, 'decode')">🔍 PhotonField → Dosya</button>
  </div>

  <!-- ENCODE -->
  <div class="panel active" id="panel-encode">
    <div class="panel-intro">
      Dosyanızı seçin; sistem sıkıştırıp spektral olarak kodlar ve tek bir <strong>PNG</strong> üretir.
      Küçük dosyalar küçük karelerde çıkar; büyük ikili veriler en geniş boyuta kadar ölçeklenir.
    </div>
    <div class="drop-zone" id="drop-zone"
         onclick="document.getElementById('file-in').click()"
         ondragover="event.preventDefault(); this.classList.add('drag')"
         ondrop="dropFile(event)"
         ondragleave="this.classList.remove('drag')">
      <div class="drop-icon">📂</div>
      <p><strong>Dosya seçin</strong> veya sürükleyip bırakın</p>
      <small>Görsel boyutu veriye göre uyarlanır · Maks ~{{ capacity_kb }} KB / 1 MB+ sıkıştırılabilir veri</small>
    </div>
    <input type="file" id="file-in" style="display:none" onchange="pickFile(event)">

    <div class="file-pill" id="file-pill">
      <span id="pill-icon">📄</span>
      <span class="name" id="pill-name">-</span>
      <span class="size" id="pill-size">-</span>
      <button class="remove" onclick="clearFile()">✕</button>
    </div>

    <div class="pw-row">
      <label for="enc-pw">İsteğe bağlı şifre</label>
      <input type="password" id="enc-pw" class="pw-field" placeholder="Boş bırakılırsa şifresiz PhotonField" autocomplete="new-password">
      <input type="password" id="enc-pw2" class="pw-field" placeholder="Şifre tekrar" autocomplete="new-password">
      <small class="pw-hint">İçerik AES-256-GCM ile şifrelenir; anahtar scrypt ile türetilir. Kısa veya tahmin edilebilir şifreler deneme saldırılarına karşı zayıftır — uzun bir parola kullanın.</small>
    </div>

    <button class="btn btn-primary" id="encode-btn" onclick="doEncode()" disabled>
      ⚡ PhotonField Üret
    </button>

    <div class="progress" id="enc-prog">
      <div class="progress-label">Spektral kodlama...</div>
      <div class="progress-track"><div class="progress-fill indeterminate"></div></div>
    </div>

    <div class="error-box" id="enc-error"></div>

    <div id="enc-output" style="display:none">
      <div class="symbol-frame">
        <img id="symbol-img" src="" alt="PhotonField">
        <div class="symbol-meta">
          <span class="symbol-tag" id="symbol-tag">PHF3 · RGB</span>
          <div class="channel-pills" id="ch-pills">
            <div class="ch-pill r" title="R kanalı"></div>
            <div class="ch-pill g" title="G kanalı"></div>
            <div class="ch-pill b" title="B kanalı"></div>
          </div>
        </div>
      </div>

      <div class="info-grid" id="info-grid"></div>
      <div class="log" id="enc-log"></div>

      <hr>
      <button class="btn btn-ghost" onclick="downloadSymbol()" style="width:100%; justify-content:center;">
        ⬇ PhotonField PNG İndir
      </button>
    </div>
  </div>

  <!-- DECODE -->
  <div class="panel" id="panel-decode">
    <div class="panel-intro">
      PhotonField görselini buraya yükleyin.
      <strong>PNG (kayıpsız)</strong> tam kapasite ve güvenilir çözüm için en iyisidir.
      JPEG / yeniden boyutlandırma bazen çalışır; özellikle yüksek dolulukta veriyi bozabilir.
    </div>

    <div class="decode-zone" id="dec-zone"
         onclick="document.getElementById('dec-in').click()"
         ondragover="event.preventDefault(); this.classList.add('drag')"
         ondrop="dropDecode(event)"
         ondragleave="this.classList.remove('drag')">
      <div class="drop-icon">🔲</div>
      <div class="dec-label">PhotonField görseli</div>
      <div class="dec-hint">Tıkla veya sürükle</div>
    </div>
    <input type="file" id="dec-in" style="display:none" accept="image/*" onchange="pickDecode(event)">

    <div class="pw-row">
      <label for="dec-pw">Şifre</label>
      <input type="password" id="dec-pw" class="pw-field" placeholder="Şifreli görselde zorunlu; şifresiz görselde boş bırakın" autocomplete="off">
    </div>

    <button class="btn btn-primary" id="decode-btn" onclick="doDecode()" disabled>
      🔍 Dosyayı Çöz
    </button>

    <div class="progress" id="dec-prog">
      <div class="progress-label">Spektral analiz...</div>
      <div class="progress-track"><div class="progress-fill indeterminate"></div></div>
    </div>

    <div class="error-box" id="dec-error"></div>

    <div class="result-box" id="result-box">
      <div class="result-icon">✅</div>
      <div class="result-name" id="res-name">-</div>
      <div class="result-size" id="res-size">-</div>
      <div id="res-checksum" class="checksum-badge badge-ok">SHA-256 ✓</div>
      <br>
      <button class="btn btn-success" onclick="downloadResult()">⬇ Dosyayı İndir</button>
      <div class="log" id="dec-log"></div>
    </div>
  </div>
    </div>
  </div>

  <section class="edu" aria-labelledby="edu-title">
    <h2 id="edu-title" class="edu-heading">Nedir, ne değildir?</h2>
    <p class="edu-lead">
      Bu araç <strong>QR kod değildir</strong>; standart barkod okuyucularla taranmaz.
      Kendi encoder/decoder mantığıyla çalışan spektral bir taşıyıcıdır — araştırma ve yerel paylaşım için uygundur.
    </p>

    <div class="edu-grid">
      <div class="edu-card pos">
        <h3>Bu nedir?</h3>
        <ul>
          <li>Dosyayı zlib ile sıkıştırır, Reed-Solomon ile korur, sonra FFT uzayında fazlar üzerinden görsele gömer.</li>
          <li>Üç RGB kanalı sırayla dolar; gerektiğinde yalnızca kırmızı kanal bile küçük dosyalar için yeterli olabilir.</li>
          <li>Görsel kenarı veri miktarına göre seçilir — gereksiz büyük PNG üretmez.</li>
          <li>Çözüm sonunda SHA-256 özetiyle bütünlük kontrolü yapılır.</li>
        </ul>
      </div>
      <div class="edu-card neg">
        <h3>Bu ne değildir?</h3>
        <ul>
          <li>Standart bir “yüksek kapasiteli QR” üreticisi veya endüstri standardı değildir.</li>
          <li>Telefon kamerası için optimize edilmiş güvenilir bir mobil protokol değildir.</li>
          <li>JPEG ile yeniden kaydetme veya küçültme her zaman güvenli değildir (özellikle görsel doluyken).</li>
          <li>Görsel dosya boyutu, sıkıştırılamayan veride çoğu zaman ham veriden büyük kalır.</li>
        </ul>
      </div>
    </div>

    <details class="learn">
      <summary>Nasıl çalışır? (kısa)</summary>
      <div class="learn-body">
        <ol>
          <li>Dosya zlib ile sıkıştırılır; başlıkta uzunluk, dosya adı ve checksum yer alır.</li>
          <li>Paket Reed-Solomon bloklarına bölünür (255 baytta 32 bayt parite).</li>
          <li>Her RGB kanalı için ayrı gri görsel üretilir: frekans hücrelerinin fazı 16 discrete seviyeye oturtulur (Gray kodlu).</li>
          <li>IFFT ile uzamsal görüntü elde edilir; üç kanal birleşerek tek PNG çıktısı oluşur.</li>
          <li>Çözümde ters işlem: FFT → faz okuma → RS düzeltme → zlib açma → checksum doğrulama.</li>
        </ol>
      </div>
    </details>

    <details class="learn">
      <summary>Adaptif boyutlar ve yaklaşık kapasite</summary>
      <div class="learn-body">
        <p>Aşağıdaki değerler Reed-Solomon sonrası net kullanıcı verisi için yaklaşık üst sınırlardır.
           Metin ve sıkıştırılabilir dosyalar gerçekte çok daha fazla sığabilir.</p>
        <div class="cap-wrap">
          <table class="cap-table">
            <thead><tr><th>Görsel</th><th>Yaklaşık net kapasite</th></tr></thead>
            <tbody>
            {% for px, kb in size_caps %}
              <tr><td>{{ px }}×{{ px }}</td><td>~{{ kb }} KB</td></tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </details>

    <details class="learn">
      <summary>İpuçları</summary>
      <div class="learn-body">
        <ul style="margin-left:1rem;">
          <li>Arşiv ve paylaşım için her zaman <strong>PNG</strong> kullanın.</li>
          <li>Sosyal medyaya JPEG ile yüklerseniz veya görseli boydan küçültürseniz veri silinebilir.</li>
          <li>Kapasite kullanımı yüksek çıktılarında (ör. %70+) JPEG’ten kaçının.</li>
          <li>Bu sunucu geliştirme modundadır; hassas veriyi üretim ortamında kullanmayın.</li>
        </ul>
      </div>
    </details>
  </section>

  <footer class="site-footer">
    PhotonField · PHF3 · Yerel Flask sunucusu · Açık kaynak deney · Standart barkodlarla uyumsuzdur.
  </footer>

</div>

<script>
let currentFile = null;
let symbolB64 = null;
let symbolFilename = null;
let decodeFile = null;
let resultData = null;
let resultFilename = null;

function switchTab(ev, tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  ev.currentTarget.classList.add('active');
  document.getElementById('panel-' + tab).classList.add('active');
}

function pickFile(e) { if (e.target.files[0]) setFile(e.target.files[0]); }
function dropFile(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
}

function setFile(f) {
  currentFile = f;
  const pill = document.getElementById('file-pill');
  pill.classList.add('show');
  document.getElementById('pill-name').textContent = f.name;
  document.getElementById('pill-size').textContent = fmtBytes(f.size);
  const ext = (f.name.split('.').pop() || '').toLowerCase();
  const icons = {pdf:'📕', doc:'📘', docx:'📘', png:'🖼️', jpg:'🖼️', jpeg:'🖼️',
                 mp3:'🎵', wav:'🎵', zip:'📦', rar:'📦', '7z':'📦',
                 py:'🐍', js:'📜', ts:'📜', json:'📜', txt:'📝', md:'📝'};
  document.getElementById('pill-icon').textContent = icons[ext] || '📄';
  document.getElementById('encode-btn').disabled = false;
  document.getElementById('enc-output').style.display = 'none';
  document.getElementById('enc-error').classList.remove('show');
}

function clearFile() {
  currentFile = null;
  document.getElementById('file-pill').classList.remove('show');
  document.getElementById('encode-btn').disabled = true;
  document.getElementById('file-in').value = '';
  document.getElementById('enc-pw').value = '';
  document.getElementById('enc-pw2').value = '';
}

function fmtBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
  return (b/1048576).toFixed(2) + ' MB';
}

async function doEncode() {
  if (!currentFile) return;
  const btn = document.getElementById('encode-btn');
  btn.disabled = true;
  document.getElementById('enc-prog').classList.add('show');
  document.getElementById('enc-output').style.display = 'none';
  const encErr = document.getElementById('enc-error');
  encErr.classList.remove('show');

  const pw = document.getElementById('enc-pw').value;
  const pw2 = document.getElementById('enc-pw2').value;
  if (pw !== pw2) {
    encErr.textContent = '✗ İki şifre alanı eşleşmiyor.';
    encErr.classList.add('show');
    document.getElementById('enc-prog').classList.remove('show');
    btn.disabled = false;
    return;
  }

  const fd = new FormData();
  fd.append('file', currentFile);
  if (pw) fd.append('password', pw);

  try {
    const r = await fetch('/encode', {method: 'POST', body: fd});
    const data = await r.json();

    document.getElementById('enc-prog').classList.remove('show');

    if (data.error) {
      const eb = document.getElementById('enc-error');
      eb.textContent = '✗ ' + data.error;
      eb.classList.add('show');
    } else {
      renderOutput(data);
    }
  } catch(e) {
    document.getElementById('enc-error').textContent = '✗ Bağlantı hatası: ' + e.message;
    document.getElementById('enc-error').classList.add('show');
    document.getElementById('enc-prog').classList.remove('show');
  }

  btn.disabled = false;
}

function renderOutput(data) {
  symbolB64 = data.image;
  symbolFilename = data.info.filename;

  document.getElementById('symbol-img').src = 'data:image/png;base64,' + symbolB64;
  document.getElementById('symbol-tag').textContent = `PHF3 · ${data.info.image_size} RGB`;

  // Update channel pills based on usage
  const chUsed = data.info.channels_used;
  const pills = document.querySelectorAll('#ch-pills .ch-pill');
  pills.forEach((p, i) => {
    if (i < chUsed) {
      p.classList.remove('off');
    } else {
      p.classList.add('off');
    }
  });

  const info = data.info;
  const infoGrid = document.getElementById('info-grid');
  infoGrid.innerHTML = '';

  const usedPct = parseFloat(info.used_pct);
  const items = [
    ['Orijinal', fmtBytes(info.original_size)],
    ['Sıkıştırılmış', fmtBytes(info.compressed_size)],
    ['Sıkıştırma', info.compression_ratio, 'ok'],
    ['Görsel Boyutu', info.image_size],
    ['Kapasite Kullanımı', info.used_pct, usedPct > 90 ? 'warn' : 'ok'],
    ['Kullanılan Kanal', `${info.channels_used}/${info.channels}`],
  ];

  items.forEach(([k, v, cls]) => {
    const c = document.createElement('div');
    c.className = 'info-card';
    c.innerHTML = `<div class="key">${k}</div><div class="val ${cls||''}">${v}</div>`;
    infoGrid.appendChild(c);
  });

  const log = document.getElementById('enc-log');
  const lines = [
    `<span class="ok">✓ Dosya okundu: ${info.filename}</span>`,
    info.encrypted
      ? `<span class="ok">✓ İç paket AES-256-GCM + scrypt ile şifrelendi (PHFE)</span>`
      : `<span class="info">○ Şifresiz mod (standart PHF3 iç gövde)</span>`,
    `<span class="ok">✓ ZLIB DEFLATE-9: ${info.original_size} → ${info.compressed_size} byte</span>`,
    `<span class="ok">✓ SHA-256 checksum eklendi</span>`,
    `<span class="ok">✓ Reed-Solomon ECC: 32 byte parity / 255 byte blok</span>`,
    `<span class="ok">✓ Faz quantization: ${info.phase_levels} seviye (Gray code)</span>`,
    `<span class="ok">✓ Adaptif boyut seçildi: ${info.image_size} (veriye göre)</span>`,
    `<span class="ok">✓ ${info.cells_used.toLocaleString()} frekans hücresi yazıldı (${info.channels_used} renk kanalı, ${info.encode_time})</span>`,
  ];
  if (usedPct > 60) {
    lines.push(`<span class="warn">⚠ Yüksek doluluk (${info.used_pct}) — yüksek frekanslar JPEG'de kaybolabilir, <strong>PNG önerilir</strong></span>`);
  }
  lines.push(`<span class="info">→ Görseli kaydet ve PhotonField → Dosya sekmesinden çöz</span>`);
  log.innerHTML = lines.join('');

  document.getElementById('enc-output').style.display = 'block';
}

function downloadSymbol() {
  if (!symbolB64) return;
  const a = document.createElement('a');
  a.href = 'data:image/png;base64,' + symbolB64;
  const baseName = (symbolFilename || 'data').replace(/\.[^.]*$/, '');
  a.download = `PHF_${baseName}_${Date.now()}.png`;
  a.click();
}

// DECODE
function pickDecode(e) { if (e.target.files[0]) setDecode(e.target.files[0]); }
function dropDecode(e) {
  e.preventDefault();
  document.getElementById('dec-zone').classList.remove('drag');
  if (e.dataTransfer.files[0]) setDecode(e.dataTransfer.files[0]);
}

function setDecode(f) {
  decodeFile = f;
  const zone = document.getElementById('dec-zone');
  const reader = new FileReader();
  reader.onload = ev => {
    zone.innerHTML = `
      <img src="${ev.target.result}" alt="PhotonField">
      <div style="font-size:12px; font-weight:700; color:var(--success); letter-spacing:0.1em;">${f.name}</div>
    `;
    zone.classList.add('loaded');
  };
  reader.readAsDataURL(f);
  document.getElementById('decode-btn').disabled = false;
  document.getElementById('result-box').classList.remove('show');
  const de = document.getElementById('dec-error');
  de.classList.remove('show');
  de.classList.remove('soft');
}

async function doDecode() {
  if (!decodeFile) return;
  const btn = document.getElementById('decode-btn');
  btn.disabled = true;
  document.getElementById('dec-prog').classList.add('show');
  document.getElementById('result-box').classList.remove('show');
  const deb = document.getElementById('dec-error');
  deb.classList.remove('show');
  deb.classList.remove('soft');

  const fd = new FormData();
  fd.append('image', decodeFile);
  const dpw = document.getElementById('dec-pw').value;
  if (dpw) fd.append('password', dpw);

  try {
    const r = await fetch('/decode', {method: 'POST', body: fd});
    const data = await r.json();

    document.getElementById('dec-prog').classList.remove('show');

    if (data.error) {
      const eb = document.getElementById('dec-error');
      eb.textContent = '✗ ' + data.error;
      eb.classList.add('show');
      if (data.needs_password) eb.classList.add('soft');
    } else {
      resultData = data.data_b64;
      resultFilename = data.filename;

      document.getElementById('res-name').textContent = data.filename;
      const frameInfo = data.image_size ? ` · Çözülen çerçeve ${data.image_size}` : '';
      document.getElementById('res-size').textContent =
        fmtBytes(data.original_size) + ' · ' + data.decode_time + ' içinde çözüldü' + frameInfo;

      const badge = document.getElementById('res-checksum');
      if (data.valid_checksum) {
        badge.textContent = 'SHA-256 Doğrulandı ✓';
        badge.className = 'checksum-badge badge-ok';
      } else {
        badge.textContent = 'SHA-256 Uyuşmazlık ⚠';
        badge.className = 'checksum-badge badge-warn';
      }

      const frameLog = data.image_size
        ? `<span class="ok">✓ Görsel işlendi (${data.image_size}, standart boyuta hizalandı)</span>`
        : `<span class="ok">✓ RGB kanalları okundu</span>`;

      const decLines = [
        frameLog,
        data.was_encrypted
          ? `<span class="ok">✓ Şifreli iç paket çözüldü (AES-GCM doğrulandı)</span>`
          : `<span class="info">○ Şifresiz iç paket (PHF3)</span>`,
        `<span class="ok">✓ 2D FFT spektrumu çıkarıldı</span>`,
        `<span class="ok">✓ Faz quantization (16 seviye, Gray decode)</span>`,
        `<span class="ok">✓ Reed-Solomon hata düzeltme uygulandı</span>`,
        `<span class="ok">✓ ZLIB decompress başarılı</span>`,
        data.valid_checksum
          ? `<span class="ok">✓ SHA-256 checksum doğrulandı</span>`
          : `<span class="warn">⚠ Checksum uyuşmazlığı — veri kısmen hatalı olabilir</span>`,
      ];
      document.getElementById('dec-log').innerHTML = decLines.join('');

      document.getElementById('result-box').classList.add('show');
    }
  } catch(e) {
    document.getElementById('dec-error').textContent = '✗ ' + e.message;
    document.getElementById('dec-error').classList.add('show');
    document.getElementById('dec-prog').classList.remove('show');
  }

  btn.disabled = false;
}

function downloadResult() {
  if (!resultData) return;
  const bytes = Uint8Array.from(atob(resultData), c => c.charCodeAt(0));
  const blob = new Blob([bytes]);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = resultFilename || 'photonfield_output';
  a.click();
}
</script>
</body>
</html>'''


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    n_max = pf.CFG.N_MAX
    cap_kb = pf.capacity_bytes(n_max) // 1024
    size_caps = [(n, pf.capacity_bytes(n) // 1024) for n in pf.CFG.SIZES]
    return render_template_string(
        HTML,
        capacity_kb=cap_kb,
        size_min=pf.CFG.SIZES[0],
        size_max=pf.CFG.SIZES[-1],
        cells_max=f'{len(pf.get_coords(n_max)) * pf.CFG.CHANNELS // 1000}K',
        rs_parity=pf.CFG.RS_PARITY,
        size_caps=size_caps,
    )


@app.route('/encode', methods=['POST'])
def encode_route():
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': 'Dosya bulunamadı'}), 400

        data = f.read()
        if not data:
            return jsonify({'error': 'Dosya boş'}), 400

        pw_raw = request.form.get('password', '')
        password = (pw_raw or '').strip() or None

        img, info = pf.encode(data, f.filename or 'file.bin', password=password)

        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=False)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()

        return jsonify({
            'image': b64,
            'info': info,
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Kodlama hatası: {e}'}), 500


@app.route('/decode', methods=['POST'])
def decode_route():
    try:
        f = request.files.get('image')
        if not f:
            return jsonify({'error': 'Görsel bulunamadı'}), 400

        img = Image.open(f.stream)
        pw_raw = request.form.get('password', '')
        password = (pw_raw or '').strip() or None

        result = pf.decode(img, password=password)

        if not result.get('success'):
            err = {'error': result.get('error', 'Çözüm başarısız')}
            if result.get('needs_password'):
                err['needs_password'] = True
            if result.get('wrong_password'):
                err['wrong_password'] = True
            return jsonify(err), 400

        payload = {
            'filename': result['filename'],
            'original_size': result['original_size'],
            'compressed_size': result['compressed_size'],
            'valid_checksum': result['valid_checksum'],
            'decode_time': result['decode_time'],
            'data_b64': base64.b64encode(result['data']).decode(),
            'was_encrypted': bool(result.get('was_encrypted')),
        }
        if result.get('image_size'):
            payload['image_size'] = result['image_size']
        return jsonify(payload)

    except Exception as e:
        return jsonify({'error': f'Çözüm hatası: {e}'}), 500


# ─────────────────────────────────────────────
#  ENTRY
# ─────────────────────────────────────────────

if __name__ == '__main__':
    print()
    print('  ██████╗ ██╗  ██╗███████╗')
    print('  ██╔══██╗██║  ██║██╔════╝')
    print('  ██████╔╝███████║█████╗  ')
    print('  ██╔═══╝ ██╔══██║██╔══╝  ')
    print('  ██║     ██║  ██║██║     ')
    print('  ╚═╝     ╚═╝  ╚═╝╚═╝     ')
    print()
    print('  PhotonField :: Spektral Konstellasyon Sistemi')
    print(f'  Adaptif RGB ({"-".join(str(s) for s in pf.CFG.SIZES)}) · '
          f'maks ~{pf.capacity_bytes(pf.CFG.N_MAX)//1024} KB / görsel · '
          f'{pf.CFG.CHANNELS} bağımsız renk kanalı')
    print('  Frekans domeni · Faz quantization · Reed-Solomon ECC')
    print()
    print('  ➜  http://localhost:5000')
    print()
    app.run(debug=False, port=5000)
