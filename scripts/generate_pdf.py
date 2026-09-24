#!/usr/bin/env python3
"""
Google Cloud Enterprise Solution Blueprint & Markdown-to-PDF Generator
========================================================================

Converts Markdown blueprints and technical architecture specifications into
publication-ready, executive-quality PDF documents co-branded with Google Cloud
and enterprise partner themes (e.g., Siemens, Airbus, Automotive, Healthcare).

Key Capabilities:
  - Native in-browser rendering of Mermaid diagrams (flowcharts, sequence, ER diagrams).
  - KaTeX mathematical equations (inline $...$ and display $$...$$).
  - High-resolution vector typography with Google Fonts (Inter + JetBrains Mono).
  - Preprocessing for GitHub callout cards (> [!NOTE], > [!IMPORTANT], > [!WARNING], etc.).
  - Deterministic Chrome DevTools Protocol (CDP) rendering with DOM completion polling.
  - Multi-OS support: macOS, Linux (Debian/Ubuntu/Cloud Shell/Cloudtop), and Windows.
  - Built-in theme presets and customizable brand color palettes.

Usage:
  python3 generate_pdf.py <input.md> [output.pdf] [options]
  python3 generate_pdf.py --input docs/MY_BLUEPRINT.md --theme siemens
  python3 generate_pdf.py -i docs/MY_BLUEPRINT.md --partner "Airbus" --theme airbus
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "default": {
        "brand_name": "Google Cloud",
        "brand_badge": "Architecture Blueprint",
        "partner_name": "Enterprise Solution",
        "partner_badge": "Reference Pattern",
        "brand_primary": "#1a73e8",
        "brand_primary_dark": "#1557b0",
        "brand_primary_light": "#e8f0fe",
        "brand_secondary": "#1e8e3e",
        "brand_secondary_light": "#e6f4ea",
        "brand_accent": "#f9ab00",
    },
    "siemens": {
        "brand_name": "Google Cloud",
        "brand_badge": "Architecture Blueprint",
        "partner_name": "SIEMENS",
        "partner_badge": "Teamcenter PLM",
        "brand_primary": "#00646e",
        "brand_primary_dark": "#00373c",
        "brand_primary_light": "#ebf5f6",
        "brand_secondary": "#1a73e8",
        "brand_secondary_light": "#e8f0fe",
        "brand_accent": "#eb780a",
    },
    "airbus": {
        "brand_name": "Google Cloud",
        "brand_badge": "Architecture Blueprint",
        "partner_name": "AIRBUS",
        "partner_badge": "Commercial Aircraft",
        "brand_primary": "#00205b",
        "brand_primary_dark": "#001338",
        "brand_primary_light": "#e8eef8",
        "brand_secondary": "#005596",
        "brand_secondary_light": "#e8f2fa",
        "brand_accent": "#f2a900",
    },
    "automotive": {
        "brand_name": "Google Cloud",
        "brand_badge": "Mobility Solutions",
        "partner_name": "Automotive Engineering",
        "partner_badge": "Connected Vehicle",
        "brand_primary": "#1e2229",
        "brand_primary_dark": "#111317",
        "brand_primary_light": "#f0f2f5",
        "brand_secondary": "#c8102e",
        "brand_secondary_light": "#fde8eb",
        "brand_accent": "#ff6b00",
    },
    "healthcare": {
        "brand_name": "Google Cloud",
        "brand_badge": "Life Sciences",
        "partner_name": "Digital Health",
        "partner_badge": "Clinical AI",
        "brand_primary": "#007a87",
        "brand_primary_dark": "#004c54",
        "brand_primary_light": "#e6f7f8",
        "brand_secondary": "#00a699",
        "brand_secondary_light": "#e6faf7",
        "brand_accent": "#ff5a5f",
    },
    "finance": {
        "brand_name": "Google Cloud",
        "brand_badge": "Financial Services",
        "partner_name": "FinTech Core",
        "partner_badge": "Regulated Banking",
        "brand_primary": "#0f5132",
        "brand_primary_dark": "#083320",
        "brand_primary_light": "#e2f3ea",
        "brand_secondary": "#0d6efd",
        "brand_secondary_light": "#cfe2ff",
        "brand_accent": "#ffc107",
    },
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__DOC_TITLE__</title>
  
  <!-- CDN Dependencies: Markdown, Mermaid, KaTeX, Highlight.js -->
  <script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.css">
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/contrib/auto-render.min.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/sql.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/bash.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/json.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/yaml.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/typescript.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/go.min.js"></script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
      --gcp-blue: #1a73e8;
      --gcp-blue-dark: #1557b0;
      --gcp-blue-light: #e8f0fe;
      --gcp-green: #1e8e3e;
      --gcp-green-light: #e6f4ea;
      --gcp-yellow: #f9ab00;
      --gcp-yellow-light: #fef7e0;
      --gcp-red: #d93025;
      --gcp-red-light: #fce8e6;

      --brand-primary: __BRAND_PRIMARY__;
      --brand-primary-dark: __BRAND_PRIMARY_DARK__;
      --brand-primary-light: __BRAND_PRIMARY_LIGHT__;
      --brand-secondary: __BRAND_SECONDARY__;
      --brand-secondary-light: __BRAND_SECONDARY_LIGHT__;
      --brand-accent: __BRAND_ACCENT__;

      --text-main: #202124;
      --text-muted: #5f6368;
      --text-secondary: #3c4043;
      --border-color: #dadce0;
      --border-subtle: #edf2f7;
      --bg-surface: #ffffff;
      --bg-neutral: #f8f9fa;
      --bg-code: #f8f9fa;
    }

    * {
      box-sizing: border-box;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 9.2pt;
      line-height: 1.5;
      color: var(--text-main);
      background-color: #f1f3f4;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }

    .document-page {
      max-width: 860px;
      margin: 20px auto;
      background: var(--bg-surface);
      padding: 36px 44px;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(60,64,67, 0.08), 0 4px 8px rgba(60,64,67, 0.04);
    }

    /* Co-Branded Top Header */
    .brand-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 12px;
      margin-bottom: 18px;
      border-bottom: 2px solid var(--border-color);
    }

    .brand-left {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11.5pt;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.2px;
    }

    .brand-badge {
      background: var(--gcp-blue-light);
      color: var(--gcp-blue-dark);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 7.5pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border: 1px solid rgba(26,115,232,0.2);
    }

    .brand-right {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11pt;
      font-weight: 800;
      color: var(--brand-primary);
      letter-spacing: 0.8px;
    }

    .partner-badge {
      background: var(--brand-primary-light);
      color: var(--brand-primary-dark);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 7.5pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border: 1px solid var(--brand-primary-dark);
    }

    /* Typography & Hierarchy */
    h1 {
      font-size: 17.5pt;
      font-weight: 700;
      color: var(--brand-primary);
      margin-top: 12px;
      margin-bottom: 8px;
      letter-spacing: -0.35px;
      line-height: 1.25;
    }

    h2 {
      font-size: 12.5pt;
      font-weight: 600;
      color: var(--brand-primary-dark);
      margin-top: 22px;
      margin-bottom: 10px;
      padding-bottom: 4px;
      border-bottom: 1.5px solid var(--border-color);
      page-break-after: avoid;
      break-after: avoid;
    }

    h3 {
      font-size: 10.5pt;
      font-weight: 600;
      color: var(--gcp-blue-dark);
      margin-top: 15px;
      margin-bottom: 6px;
      page-break-after: avoid;
      break-after: avoid;
    }

    h4 {
      font-size: 9.5pt;
      font-weight: 600;
      color: var(--text-main);
      margin-top: 10px;
      margin-bottom: 4px;
      page-break-after: avoid;
      break-after: avoid;
    }

    p {
      margin-top: 0;
      margin-bottom: 8px;
      color: var(--text-secondary);
      line-height: 1.48;
    }

    ul, ol {
      margin-top: 0;
      margin-bottom: 10px;
      padding-left: 20px;
      color: var(--text-secondary);
      line-height: 1.45;
    }

    li {
      margin-bottom: 3px;
    }

    hr {
      border: none;
      border-top: 1px solid var(--border-color);
      margin: 16px 0;
    }

    /* Page Break Utility */
    .page-break {
      page-break-before: always !important;
      break-before: page !important;
      clear: both;
      height: 0;
      margin: 0;
      padding: 0;
    }

    /* Tables (Google Cloud Enterprise Styling) */
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      font-size: 8.2pt;
      page-break-inside: avoid;
      break-inside: avoid;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      overflow: hidden;
    }

    th {
      background-color: var(--bg-neutral);
      color: var(--brand-primary);
      font-weight: 600;
      text-align: left;
      padding: 6px 9px;
      border: 1px solid var(--border-color);
      border-bottom: 2px solid var(--brand-primary);
    }

    td {
      padding: 5px 9px;
      border: 1px solid var(--border-color);
      vertical-align: top;
      color: var(--text-secondary);
    }

    tr:nth-child(even) td {
      background-color: #fafbfc;
    }

    /* KPI Summary Cards Grid */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin: 14px 0;
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .kpi-card {
      background: var(--bg-neutral);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 10px 8px;
      text-align: center;
      box-shadow: 0 1px 2px rgba(60,64,67, 0.05);
    }

    .kpi-card.blue { border-top: 3.5px solid var(--gcp-blue); }
    .kpi-card.primary { border-top: 3.5px solid var(--brand-primary); }
    .kpi-card.green { border-top: 3.5px solid var(--gcp-green); }
    .kpi-card.accent { border-top: 3.5px solid var(--brand-accent); }

    .kpi-value {
      font-size: 11.5pt;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 2px;
      line-height: 1.2;
    }

    .kpi-label {
      font-size: 7.2pt;
      color: var(--text-muted);
      line-height: 1.25;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }

    /* Code Blocks and Inline Code */
    code {
      font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
      font-size: 8pt;
      background-color: var(--bg-code);
      padding: 1px 4px;
      border-radius: 3px;
      border: 1px solid #e1e4e8;
      color: #b31d28;
    }

    pre {
      background-color: var(--bg-code);
      border: 1px solid var(--border-color);
      border-left: 3.5px solid var(--gcp-blue);
      border-radius: 4px;
      padding: 9px 12px;
      overflow-x: auto;
      margin: 10px 0;
      page-break-inside: avoid;
      break-inside: avoid;
    }

    pre code {
      background: transparent;
      padding: 0;
      border: none;
      color: var(--text-main);
      font-size: 7.5pt;
      line-height: 1.4;
    }

    /* Google Cloud Callouts & Quotes */
    blockquote, .gcp-callout {
      margin: 11px 0;
      padding: 9px 13px;
      border-left: 3.5px solid var(--gcp-blue);
      background-color: var(--gcp-blue-light);
      color: var(--gcp-blue-dark);
      border-radius: 0 5px 5px 0;
      page-break-inside: avoid;
      break-inside: avoid;
      font-size: 8.5pt;
      line-height: 1.45;
    }

    .gcp-callout.note {
      border-left-color: var(--gcp-blue);
      background-color: #f1f6fd;
      color: var(--gcp-blue-dark);
    }

    .gcp-callout.tip {
      border-left-color: var(--gcp-green);
      background-color: var(--gcp-green-light);
      color: #0d652d;
    }

    .gcp-callout.important {
      border-left-color: var(--brand-primary);
      background-color: var(--brand-primary-light);
      color: var(--brand-primary-dark);
    }

    .gcp-callout.warning {
      border-left-color: var(--gcp-yellow);
      background-color: var(--gcp-yellow-light);
      color: #975300;
    }

    .gcp-callout.caution {
      border-left-color: var(--gcp-red);
      background-color: var(--gcp-red-light);
      color: #a51d24;
    }

    blockquote p, .gcp-callout p {
      color: inherit;
      margin-bottom: 4px;
    }

    blockquote p:last-child, .gcp-callout p:last-child {
      margin-bottom: 0;
    }

    /* Mermaid Diagrams Container */
    .mermaid {
      display: flex;
      justify-content: center;
      align-items: center;
      margin: 12px 0;
      padding: 10px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      page-break-inside: avoid;
      break-inside: avoid;
      box-shadow: 0 1px 3px rgba(60,64,67, 0.04);
    }

    .mermaid svg {
      max-width: 100% !important;
      height: auto !important;
    }

    /* KaTeX Math Formatting */
    .katex-display {
      margin: 8px 0 !important;
      padding: 4px 0;
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .katex {
      font-size: 1.0em;
    }

    /* Print & PDF Specific Overrides */
    @media print {
      @page {
        size: A4 portrait;
        margin: 10mm 12mm 10mm 12mm;
      }

      body {
        font-size: 8.8pt;
        line-height: 1.45;
        background: #ffffff;
      }

      .document-page {
        max-width: 100%;
        margin: 0;
        padding: 0;
        border: none;
        border-radius: 0;
        box-shadow: none;
      }

      .page-break {
        page-break-before: always !important;
        break-before: page !important;
        display: block;
        height: 0;
        margin: 0;
        padding: 0;
      }

      h1 { font-size: 16pt; margin-bottom: 5px; }
      h2 { font-size: 11.5pt; margin-top: 14px; margin-bottom: 8px; padding-bottom: 3px; }
      h3 { font-size: 9.8pt; margin-top: 10px; margin-bottom: 4px; }
      h4 { font-size: 8.8pt; margin-top: 8px; margin-bottom: 3px; }
      p { margin-bottom: 6px; }
      ul, ol { margin-bottom: 8px; }

      table, pre, .mermaid, blockquote, .gcp-callout, .kpi-grid {
        page-break-inside: avoid;
        break-inside: avoid;
      }

      a {
        text-decoration: none;
        color: var(--gcp-blue);
      }
    }
  </style>
</head>
<body>
  <div class="document-page">
    <div class="brand-bar">
      <div class="brand-left">
        <span>__BRAND_NAME__</span>
        <span class="brand-badge">__BRAND_BADGE__</span>
      </div>
      <div class="brand-right">
        <span>__PARTNER_NAME__</span>
        <span class="partner-badge">__PARTNER_BADGE__</span>
      </div>
    </div>
    
    <div id="content"></div>
  </div>

  <script>
    const rawMarkdown = __RAW_MARKDOWN__;

    const renderer = new marked.Renderer();
    const defaultCodeRenderer = renderer.code.bind(renderer);

    renderer.code = function(code, language) {
      if (typeof code === 'object') {
        language = code.lang;
        code = code.text;
      }
      if (language === 'mermaid') {
        return `<div class="mermaid">${code}</div>`;
      }
      return defaultCodeRenderer(code, language);
    };

    marked.setOptions({
      renderer: renderer,
      gfm: true,
      breaks: false,
      headerIds: true,
      mangle: false,
      highlight: function(code, lang) {
        const language = (lang && hljs.getLanguage(lang)) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
      }
    });

    // 1. Render Markdown to DOM
    document.getElementById('content').innerHTML = marked.parse(rawMarkdown);

    // 2. Initialize Mermaid with Theme Variables
    mermaid.initialize({
      startOnLoad: false,
      theme: 'neutral',
      themeVariables: {
        primaryColor: '__BRAND_PRIMARY_LIGHT__',
        primaryTextColor: '__BRAND_PRIMARY_DARK__',
        primaryBorderColor: '__BRAND_PRIMARY__',
        lineColor: '__BRAND_PRIMARY__',
        secondaryColor: '#f8f9fa',
        tertiaryColor: '#ffffff',
        fontFamily: 'Inter, sans-serif',
        fontSize: '11px',
        noteBkgColor: '#e8f0fe',
        noteTextColor: '#1557b0',
        noteBorderColor: '#1a73e8'
      },
      flowchart: { useMaxWidth: true, htmlLabels: false, curve: 'basis' },
      sequence: { useMaxWidth: true, showSequenceNumbers: true, actorFontSize: 11, messageFontSize: 11 },
      er: { useMaxWidth: true, fontSize: 11 }
    });

    async function renderAllMermaid() {
      if (document.fonts && document.fonts.ready) {
        await document.fonts.ready;
      }
      const elements = document.querySelectorAll('.mermaid');
      for (let i = 0; i < elements.length; i++) {
        const el = elements[i];
        const graphCode = el.textContent.trim();
        const id = `mermaid-svg-${i}`;
        try {
          const { svg } = await mermaid.render(id, graphCode);
          el.innerHTML = svg;
        } catch (err) {
          console.error(`Mermaid render error on diagram ${i}:`, err);
        }
      }
      
      // 3. Render KaTeX equations
      renderMathInElement(document.getElementById('content'), {
        delimiters: [
          {left: '$$', right: '$$', display: true},
          {left: '$', right: '$', display: false}
        ],
        ignoredClasses: ['mermaid', 'hljs', 'language-mermaid', 'no-math'],
        ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'svg'],
        throwOnError: false
      });

      window.__MERMAID_RENDER_COMPLETE__ = true;
    }

    renderAllMermaid();
  </script>
</body>
</html>
"""


def preprocess_markdown(md_text: str) -> str:
    """Converts GitHub alert callouts and custom tags to styled HTML components."""
    # 1. Alert callouts (> [!NOTE], etc.)
    def replace_alert(match):
        alert_type = match.group(1).lower()
        content = match.group(2)
        lines = [re.sub(r"^>\s?", "", line) for line in content.strip().split("\n")]
        inner_md = "\n".join(lines)
        return f'<div class="gcp-callout {alert_type}">\n\n{inner_md}\n\n</div>\n\n'

    pattern = r">\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*\n((?:>[^\n]*\n?)+)"
    md_text = re.sub(pattern, replace_alert, md_text, flags=re.MULTILINE)

    # 2. Page break comments
    md_text = re.sub(r"<!--\s*page-?break\s*-->", '<div class="page-break"></div>', md_text, flags=re.IGNORECASE)

    return md_text


def extract_title_from_md(md_text: str, default_title: str) -> str:
    """Finds the first H1 header in markdown to use as document title."""
    match = re.search(r"^#\s+(.+)$", md_text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return default_title


def find_chrome_binary(custom_path: Optional[str] = None) -> Optional[str]:
    """Locates Google Chrome, Chromium, or Edge binary cross-platform."""
    if custom_path and os.path.exists(custom_path) and os.access(custom_path, os.X_OK):
        return custom_path

    env_vars = ["CHROME_BIN", "GOOGLE_CHROME_BIN", "CHROME_PATH", "BROWSER"]
    for var in env_vars:
        p = os.environ.get(var)
        if p and os.path.exists(p) and os.access(p, os.X_OK):
            return p

    candidates = [
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        # Linux
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        # Windows
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    ]

    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c

    return None


def resolve_theme_config(args: argparse.Namespace) -> Dict[str, str]:
    """Merges selected preset with command line overrides."""
    theme_key = (args.theme or "default").lower()
    base = THEME_PRESETS.get(theme_key, THEME_PRESETS["default"]).copy()

    if args.partner:
        base["partner_name"] = args.partner
    if args.partner_color:
        base["brand_primary"] = args.partner_color
        base["brand_primary_dark"] = args.partner_color
    if args.badge:
        base["partner_badge"] = args.badge

    return base


def build_html_document(raw_markdown: str, title: str, theme: Dict[str, str]) -> str:
    """Populates HTML template with markdown payload and theme tokens."""
    processed_md = preprocess_markdown(raw_markdown)
    # Prevent closing script tag breakdown in injected JSON string
    json_safe_md = json.dumps(processed_md).replace("</script>", "<\\/script>")

    html = HTML_TEMPLATE
    html = html.replace("__DOC_TITLE__", title)
    html = html.replace("__BRAND_NAME__", theme["brand_name"])
    html = html.replace("__BRAND_BADGE__", theme["brand_badge"])
    html = html.replace("__PARTNER_NAME__", theme["partner_name"])
    html = html.replace("__PARTNER_BADGE__", theme["partner_badge"])
    html = html.replace("__BRAND_PRIMARY__", theme["brand_primary"])
    html = html.replace("__BRAND_PRIMARY_DARK__", theme.get("brand_primary_dark", theme["brand_primary"]))
    html = html.replace("__BRAND_PRIMARY_LIGHT__", theme.get("brand_primary_light", "#e8f0fe"))
    html = html.replace("__BRAND_SECONDARY__", theme.get("brand_secondary", "#1a73e8"))
    html = html.replace("__BRAND_SECONDARY_LIGHT__", theme.get("brand_secondary_light", "#e8f2fa"))
    html = html.replace("__BRAND_ACCENT__", theme.get("brand_accent", "#f9ab00"))
    html = html.replace("__RAW_MARKDOWN__", json_safe_md)

    return html


def convert_markdown_to_pdf(
    input_md: Path,
    output_pdf: Path,
    theme_cfg: Dict[str, str],
    custom_title: Optional[str] = None,
    custom_html: Optional[Path] = None,
    chrome_bin: Optional[str] = None,
    no_pdf: bool = False,
    verbose: bool = False,
) -> Tuple[bool, Path, Optional[Path]]:
    """Converts a Markdown file into HTML and PDF."""
    if not input_md.exists():
        raise FileNotFoundError(f"Input Markdown file not found: {input_md}")

    if verbose:
        print(f"Reading Markdown: {input_md}")
    with open(input_md, "r", encoding="utf-8") as f:
        raw_markdown = f.read()

    doc_title = custom_title or extract_title_from_md(raw_markdown, input_md.stem.replace("_", " ").title())
    html_content = build_html_document(raw_markdown, doc_title, theme_cfg)

    html_path = custom_html or (input_md.parent / f"{input_md.stem}.html")
    if verbose:
        print(f"Writing intermediate HTML: {html_path}")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    if no_pdf:
        return True, html_path, None

    detected_chrome = find_chrome_binary(chrome_bin)
    if not detected_chrome:
        print("Warning: Google Chrome or Chromium binary was not found.")
        print(f"Intermediate HTML generated successfully at: {html_path}")
        print("You can open this HTML file in your web browser and select File -> Print -> Save as PDF.")
        return False, html_path, None

    if verbose:
        print(f"Detected Chrome executable: {detected_chrome}")

    node_bin = shutil.which("node")
    cdp_script = Path(__file__).resolve().parent / "render_pdf_cdp.js"

    # 1. Attempt deterministic CDP rendering via Node.js
    if node_bin and cdp_script.exists():
        if verbose:
            print("Rendering via Chrome DevTools Protocol (CDP) WebSocket listener...")
        res = subprocess.run(
            [node_bin, str(cdp_script), str(html_path), str(output_pdf), detected_chrome],
            capture_output=not verbose,
            text=True,
        )
        if res.returncode == 0 and output_pdf.exists() and output_pdf.stat().st_size > 0:
            return True, html_path, output_pdf
        elif verbose:
            print(f"CDP runner returned code {res.returncode}, falling back to CLI print-to-pdf...")

    # 2. Fallback to direct Chrome headless CLI print-to-pdf
    if verbose:
        print("Rendering via Chrome headless CLI (--headless=new --print-to-pdf)...")
    cmd = [
        detected_chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={output_pdf}",
        f"file://{html_path.resolve()}",
    ]
    subprocess.run(cmd, check=True, capture_output=not verbose)

    if output_pdf.exists() and output_pdf.stat().st_size > 0:
        return True, html_path, output_pdf

    return False, html_path, None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Markdown blueprints to co-branded Google Cloud Enterprise PDFs with Mermaid & KaTeX.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_file", nargs="?", help="Path to input Markdown document (.md).")
    parser.add_argument("output_file", nargs="?", help="Path to output PDF file (.pdf).")
    parser.add_argument("-i", "--input", dest="opt_input", help="Explicit path to input Markdown file.")
    parser.add_argument("-o", "--output", dest="opt_output", help="Explicit path to output PDF file.")
    parser.add_argument("--html", help="Path to intermediate HTML file.")
    parser.add_argument("--title", help="Override document title in header bar and page metadata.")
    parser.add_argument(
        "--theme",
        default="default",
        choices=["default", "siemens", "airbus", "automotive", "healthcare", "finance"],
        help="Built-in branding preset for colors and badges.",
    )
    parser.add_argument("--partner", help="Partner brand name (e.g., 'Siemens', 'Airbus', 'Cymbal Retail').")
    parser.add_argument("--partner-color", help="Hex color code for primary partner branding (e.g., '#00646e').")
    parser.add_argument("--badge", help="Badge subtitle for the partner header (e.g., 'Teamcenter PLM').")
    parser.add_argument("--chrome-bin", help="Custom path to Google Chrome or Chromium executable.")
    parser.add_argument("--no-pdf", action="store_true", help="Generate HTML presentation only; skip PDF conversion.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug and progress logging.")
    return parser.parse_args()


def main():
    args = parse_args()
    input_str = args.opt_input or args.input_file
    output_str = args.opt_output or args.output_file

    if not input_str:
        print("Error: Input Markdown file is required. Use --help for usage details.")
        sys.exit(1)

    input_path = Path(input_str).resolve()
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}")
        sys.exit(1)

    if output_str:
        output_path = Path(output_str).resolve()
    else:
        output_path = input_path.parent / f"{input_path.stem}.pdf"

    html_path = Path(args.html).resolve() if args.html else None
    theme_cfg = resolve_theme_config(args)

    success, gen_html, gen_pdf = convert_markdown_to_pdf(
        input_md=input_path,
        output_pdf=output_path,
        theme_cfg=theme_cfg,
        custom_title=args.title,
        custom_html=html_path,
        chrome_bin=args.chrome_bin,
        no_pdf=args.no_pdf,
        verbose=args.verbose,
    )

    if success and gen_pdf:
        size_kb = gen_pdf.stat().st_size / 1024
        print(f"\n[SUCCESS] PDF created successfully:")
        print(f"  PDF:  {gen_pdf} ({size_kb:.1f} KB)")
        print(f"  HTML: {gen_html}")
    elif success and args.no_pdf:
        print(f"\n[SUCCESS] HTML generated successfully:")
        print(f"  HTML: {gen_html}")
    else:
        print(f"\n[PARTIAL] Intermediate HTML generated at: {gen_html}")
        print("PDF compilation could not be completed automatically.")
        sys.exit(1)


if __name__ == "__main__":
    main()
