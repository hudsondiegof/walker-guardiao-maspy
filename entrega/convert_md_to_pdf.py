import os
import re
import subprocess
import html

entrega_dir = os.path.dirname(os.path.abspath(__file__))
md_path = os.path.join(entrega_dir, "relatorio_pi.md")
html_out = os.path.join(entrega_dir, "relatorio_pi_from_md.html")
pdf_out = os.path.join(entrega_dir, "Projeto_Inicial_SMA_Walker_Guardiao.pdf")
user_dir = os.path.join(r"C:\Users\Hudson\.gemini\antigravity\brain\37a9fa47-5ca6-4541-9f0f-0bd3b35ae94e\scratch\chrome_prof")

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

lines = md_content.splitlines()

html_lines = []
in_code_block = False
code_block_lang = ""
code_block_lines = []
in_table = False
table_headers = []
table_rows = []
in_formula_blockquote = False
formula_lines = []

def parse_inline(text):
    text = text.replace(r"\text{valor}", "valor")
    text = text.replace(r"\text{manhattan}", "manhattan")
    text = text.replace(r"\text{pos}", "pos")
    text = text.replace(r"\text{risco}", "risco")
    text = text.replace(r"\text{vezes\_interceptado}", "vezes_interceptado")
    text = text.replace(r"\text{ se }", " se ")
    text = text.replace(r"\cdot", "·")
    text = text.replace(r"\approx", "≈")
    text = text.replace(r"\gg", "≫")
    text = text.replace(r"\le", "≤")
    text = text.replace(r"\quad", " ")
    text = text.replace(r"\{", "{").replace(r"\}", "}")
    text = text.replace(r"{,}", ",")

    # Math blocks: $$...$$
    text = re.sub(r'\$\$(.*?)\$\$', r'<div class="formula-math">\1</div>', text)
    # Inline math: $...$
    text = re.sub(r'\$(.*?)\$', r'<span class="math">\1</span>', text)
    # Bold italic
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text

i = 0
has_title = False
authors_list = []

while i < len(lines):
    line = lines[i]

    # Top header meta (e.g. Projeto Inicial (PI) — Sistemas Multiagentes - UTFPR - 2026/2)
    if i == 0 and not line.startswith("#"):
        html_lines.append(f'<div class="doc-header-meta">{parse_inline(line)}</div>')
        i += 1
        continue

    # Authors list before main title
    if not has_title and line.strip().startswith("- "):
        author_text = parse_inline(line.strip()[2:].strip())
        authors_list.append(author_text)
        i += 1
        continue

    # Main title #
    if line.startswith("# "):
        if authors_list:
            authors_str = " &nbsp;&bull;&nbsp; ".join(authors_list)
            html_lines.append(f'<div class="doc-authors"><strong>Autores:</strong> {authors_str}</div>')
            authors_list = []
        has_title = True
        title_text = parse_inline(line[2:].strip())
        html_lines.append(f'<h1 class="doc-title">{title_text}</h1>')
        i += 1
        continue

    # Code blocks (Light clean GitHub markdown style, no heavy dark terminal)
    if line.startswith("```"):
        if not in_code_block:
            in_code_block = True
            code_block_lang = line[3:].strip()
            code_block_lines = []
        else:
            in_code_block = False
            code_text = html.escape("\n".join(code_block_lines))
            html_lines.append(f"<pre><code>{code_text}</code></pre>")
        i += 1
        continue

    if in_code_block:
        code_block_lines.append(line)
        i += 1
        continue

    # Formula Box in Section 3 (> ...)
    if line.startswith("> **Função de Utilidade") or (in_formula_blockquote and line.startswith(">")):
        in_formula_blockquote = True
        content = line[1:].strip()
        if content:
            formula_lines.append(content)
        i += 1
        # peek ahead
        if i >= len(lines) or not lines[i].startswith(">"):
            in_formula_blockquote = False
            parsed_box = []
            for fl in formula_lines:
                parsed_fl = parse_inline(fl)
                if parsed_fl.startswith("<div class=\"formula-math\">"):
                    parsed_box.append(parsed_fl)
                elif "Função de Utilidade" in parsed_fl:
                    parsed_box.append(f"<p><strong>{parsed_fl}</strong></p>")
                else:
                    parsed_box.append(f"<p>{parsed_fl}</p>")
            html_lines.append(f'<blockquote>{"".join(parsed_box)}</blockquote>')
            formula_lines = []
        continue

    # Handle Figure 1 (Goal Overview + System Overview)
    if "pdt_goal_overview.png" in line:
        fig1_lines = [line]
        i += 1
        while i < len(lines) and not lines[i].startswith("*Figura 1"):
            fig1_lines.append(lines[i])
            i += 1
        caption = lines[i].strip()[1:-1] if i < len(lines) else ""
        caption_parsed = parse_inline(caption)
        html_lines.append(f"""
<div class="figure-card" style="padding: 10px 12px 8px 12px; margin: 8px 0 12px 0;">
  <img src="../pdt/pdt_goal_overview.png" alt="Goal Overview Diagram PDT 3.2b" style="width: 96%; max-height: 125px; object-fit: contain; display: block; margin: 0 auto 8px auto;" />
  <hr style="border: 0; border-top: 1px dashed #d0d7de; margin: 8px 0 8px 0;" />
  <img src="../pdt/pdt_system_overview.png" alt="System Overview Diagram PDT 3.2b" style="width: 82%; max-height: 390px; object-fit: contain; display: block; margin: 0 auto;" />
  <div class="figure-caption" style="margin-top: 8px;">{caption_parsed}</div>
</div>
""")
        i += 1
        continue

    # Handle Simulation Screens (tela_simulacao side by side)
    if "tela_simulacao" in line and "|" in line:
        inicio_cap = ""
        fim_cap = ""
        i += 1
        if i < len(lines) and "---" in lines[i]:
            i += 1
        if i < len(lines) and "|" in lines[i]:
            caps = [c.strip() for c in lines[i].strip()[1:-1].split("|")]
            if len(caps) >= 2:
                inicio_cap = parse_inline(caps[0].strip()[1:-1] if caps[0].startswith("*") and caps[0].endswith("*") else caps[0])
                fim_cap = parse_inline(caps[1].strip()[1:-1] if caps[1].startswith("*") and caps[1].endswith("*") else caps[1])
            i += 1
        html_lines.append(f"""
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 8px 0 10px 0;">
  <div class="figure-card" style="padding: 6px 8px 6px 8px; margin: 0;">
    <img src="tela_simulacao_inicio.png" alt="Início da Simulação" style="width: 100%; max-height: 300px; object-fit: contain; display: block; margin: 0 auto;" />
    <div class="figure-caption" style="margin-top: 6px;">{inicio_cap}</div>
  </div>
  <div class="figure-card" style="padding: 6px 8px 6px 8px; margin: 0;">
    <img src="tela_simulacao_fim.png" alt="Fim da Simulação" style="width: 100%; max-height: 300px; object-fit: contain; display: block; margin: 0 auto;" />
    <div class="figure-caption" style="margin-top: 6px;">{fim_cap}</div>
  </div>
</div>
""")
        continue

    # Handle Figure 2 (Agent Overview Walker & Guardião stacked and enlarged)
    if "pdt_walker_overview.png" in line and "|" in line:
        walker_cap = ""
        guardiao_cap = ""
        i += 1
        if i < len(lines) and "---" in lines[i]:
            i += 1
        if i < len(lines) and "|" in lines[i]:
            caps = [c.strip() for c in lines[i].strip()[1:-1].split("|")]
            if len(caps) >= 2:
                walker_cap = parse_inline(caps[0].strip()[1:-1] if caps[0].startswith("*") and caps[0].endswith("*") else caps[0])
                guardiao_cap = parse_inline(caps[1].strip()[1:-1] if caps[1].startswith("*") and caps[1].endswith("*") else caps[1])
            i += 1
        html_lines.append(f"""
<div class="page-break" style="margin-top: 4px;"></div>
<div class="figure-card" style="padding: 8px 12px 6px 12px; margin: 6px 0 12px 0;">
  <img src="../pdt/pdt_walker_overview.png" alt="Walker Agent Overview Diagram PDT 3.2b" style="width: 98%; max-height: 330px; object-fit: contain; display: block; margin: 0 auto;" />
  <div class="figure-caption" style="margin-top: 6px;">{walker_cap}</div>
</div>
<div class="figure-card" style="padding: 8px 12px 6px 12px; margin: 6px 0 10px 0;">
  <img src="../pdt/pdt_guardiao_overview.png" alt="Guardiao Agent Overview Diagram PDT 3.2b" style="width: 80%; max-height: 260px; object-fit: contain; display: block; margin: 0 auto;" />
  <div class="figure-caption" style="margin-top: 6px;">{guardiao_cap}</div>
</div>
""")
        continue

    # Handle Figure 3 (SVG Diagram)
    if "figura3_arquitetura_bdi.svg" in line or "figura3_arquitetura_bdi" in line:
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        caption = "Figura 3 — Arquitetura BDI pura no MASPY: sensores e atuadores físicos na Arena e seleção de planos por contexto em Walker e Guardiao."
        if i < len(lines) and lines[i].startswith("*Figura 3"):
            caption = parse_inline(lines[i].strip()[1:-1])
            i += 1
        
        svg_path = os.path.join(entrega_dir, "figura3_arquitetura_bdi.svg")
        svg_content = ""
        if os.path.exists(svg_path):
            with open(svg_path, "r", encoding="utf-8") as sf:
                svg_content = sf.read()
        else:
            svg_content = f'<img src="figura3_arquitetura_bdi.svg" alt="{caption}" style="width: 100%;" />'

        html_lines.append(f"""
<div class="figure-card" style="padding: 6px 10px 4px 10px; margin: 6px 0 10px 0;">
  {svg_content}
  <div class="figure-caption">{caption}</div>
</div>
""")
        continue

    # Handle Figure 4 (Sequence Diagram SVG)
    if "figura4_sequencia_bdi" in line:
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        caption = "Figura 4 — Diagrama de sequência da dinâmica multiagente: ronda, interceptação com migração de utilidade e captura atômica via canal KQML."
        if i < len(lines) and lines[i].startswith("*Figura 4"):
            caption = parse_inline(lines[i].strip()[1:-1])
            i += 1

        svg_path = os.path.join(entrega_dir, "figura4_sequencia_bdi.svg")
        svg_content = ""
        if os.path.exists(svg_path):
            with open(svg_path, "r", encoding="utf-8") as sf:
                svg_content = sf.read()
        else:
            svg_content = f'<img src="figura4_sequencia_bdi.svg" alt="{caption}" style="width: 100%;" />'

        html_lines.append(f"""
<div class="figure-card" style="padding: 6px 10px 4px 10px; margin: 6px 0 10px 0;">
  {svg_content}
  <div class="figure-caption">{caption}</div>
</div>
""")
        continue

    # Handle Terminal Log Screenshot
    if "log_execucao_terminal" in line:
        caption = "Registro real de execução no terminal evidenciando a deliberação BDI dos Walkers, captura atômica de alvo e encerramento coordenado via KQML."
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i < len(lines) and lines[i].startswith("*Figura"):
            caption = parse_inline(lines[i].strip()[1:-1])
            i += 1
        html_lines.append(f"""
<div class="figure-card" style="padding: 6px 10px 4px 10px; margin: 6px 0 8px 0; background: #0c1017; border-color: #30363d;">
  <img src="log_execucao_terminal.png" alt="{caption}" style="width: 100%; max-height: 220px; object-fit: contain; display: block; margin: 0 auto; border-radius: 4px;" />
  <div class="figure-caption" style="color: #8b949e;">{caption}</div>
</div>
""")
        continue

    # Tables (Standard clean markdown table without colored badges)
    if line.strip().startswith("|") and line.strip().endswith("|"):
        if not in_table:
            in_table = True
            table_headers = [parse_inline(c.strip()) for c in line.strip()[1:-1].split("|")]
            table_rows = []
            i += 1
            if i < len(lines) and "---" in lines[i]:
                i += 1
            continue
        else:
            cols = [parse_inline(c.strip()) for c in line.strip()[1:-1].split("|")]
            table_rows.append(cols)
            i += 1
            continue
    else:
        if in_table:
            in_table = False
            tbl_html = ["<table><thead><tr>"]
            header_strs = [h.strip() for h in table_headers]
            if len(header_strs) > 0 and "Component" in header_strs[0]:
                widths = ["width: 22%;", ""]
            elif len(header_strs) > 0 and "Dimensão" in header_strs[0]:
                widths = ["width: 26%;", "width: 24%;", ""]
            elif len(header_strs) > 0 and "Categoria" in header_strs[0]:
                widths = ["width: 24%;", "width: 22%;", ""]
            elif len(header_strs) > 0 and "Agente" in header_strs[0]:
                widths = ["width: 17%;", "width: 24%;", "width: 33%;", ""]
            elif len(header_strs) > 0 and "Arquivo" in header_strs[0]:
                widths = ["width: 24%;", ""]
            else:
                widths = ["" for _ in header_strs]

            for idx, h in enumerate(table_headers):
                w_style = f' style="{widths[idx]}"' if idx < len(widths) and widths[idx] else ''
                tbl_html.append(f"<th{w_style}>{h}</th>")
            tbl_html.append("</tr></thead><tbody>")
            for row in table_rows:
                tbl_html.append("<tr>")
                for c in row:
                    tbl_html.append(f"<td>{c}</td>")
                tbl_html.append("</tr>")
            tbl_html.append("</tbody></table>")
            html_lines.append("".join(tbl_html))

    # HR
    if line.strip() == "---":
        html_lines.append("<hr />")
        i += 1
        continue

    # Headers
    if line.startswith("## "):
        h2 = parse_inline(line[3:])
        page_break_class = ' class="page-break"' if any(k in h2 for k in ["3. Definição", "4. Modelagem"]) else ''
        extra_style = ' style="margin: 10px 0 5px 0;"' if "5. Organização" in h2 else ''
        html_lines.append(f"<h2{page_break_class}{extra_style}>{h2}</h2>")
        i += 1
        continue

    if line.startswith("### "):
        h3 = parse_inline(line[4:])
        page_break_class = ' class="page-break"' if "4.1 Especificação" in h3 else ''
        extra_style = ' style="margin: 8px 0 4px 0;"' if any(k in h3 for k in ["4.2 Diagrama", "4.3 Diagrama"]) else ''
        html_lines.append(f"<h3{page_break_class}{extra_style}>{h3}</h3>")
        i += 1
        continue

    # Blank lines
    if not line.strip() or line.strip() == "<br/>":
        i += 1
        continue

    # Lists
    if line.strip().startswith("- "):
        item_text = parse_inline(line.strip()[2:].strip())
        html_lines.append(f"<ul><li>{item_text}</li></ul>")
        i += 1
        continue

    # Normal paragraph
    parsed_p = parse_inline(line.strip())
    html_lines.append(f"<p>{parsed_p}</p>")
    i += 1

full_body = "\n".join(html_lines)
full_body = re.sub(r'</ul>\s*<ul>', '', full_body)

full_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Projeto Inicial (PI) — Sistemas Multiagentes — UTFPR</title>
  <style>
    @page {{
      size: A4;
      margin: 14mm 16mm 14mm 16mm;
    }}
    * {{
      box-sizing: border-box;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
      color: #1f2328;
      font-size: 10pt;
      line-height: 1.45;
      margin: 0;
      padding: 0;
      background: #ffffff;
    }}
    .doc-header-meta {{
      font-size: 8.8pt;
      color: #57606a;
      font-weight: 600;
      margin: 0 0 3px 0;
    }}
    .doc-authors {{
      font-size: 8.9pt;
      color: #57606a;
      margin: 0 0 8px 0;
    }}
    .doc-authors strong {{
      color: #1f2328;
    }}
    h1.doc-title {{
      font-size: 15pt;
      font-weight: 700;
      color: #1f2328;
      border-bottom: 1px solid #d0d7de;
      padding-bottom: 6px;
      margin: 0 0 10px 0;
      line-height: 1.35;
    }}
    p.doc-subtitle {{
      font-size: 10.5pt;
      color: #1f2328;
      margin: 0 0 10px 0;
    }}
    h2 {{
      font-size: 12.5pt;
      font-weight: 600;
      color: #1f2328;
      border-bottom: 1px solid #d0d7de;
      padding-bottom: 4px;
      margin: 16px 0 8px 0;
      page-break-after: avoid;
    }}
    h3 {{
      font-size: 10.8pt;
      font-weight: 600;
      color: #1f2328;
      margin: 12px 0 6px 0;
      page-break-after: avoid;
    }}
    p {{
      margin: 0 0 8px 0;
      text-align: justify;
    }}
    hr {{
      border: 0;
      border-top: 1px solid #d0d7de;
      margin: 12px 0;
    }}
    blockquote {{
      border-left: 3.5px solid #d0d7de;
      color: #57606a;
      padding: 6px 12px;
      margin: 8px 0 10px 0;
      background: #f6f8fa;
      border-radius: 0 4px 4px 0;
      break-inside: avoid;
    }}
    blockquote p {{
      margin: 0 0 4px 0;
      color: #1f2328;
    }}
    blockquote p:last-child {{
      margin-bottom: 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 8px 0 12px 0;
      font-size: 9.3pt;
      break-inside: avoid;
    }}
    th, td {{
      border: 1px solid #d0d7de;
      padding: 6px 9px;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: #f6f8fa;
      color: #1f2328;
      font-weight: 600;
    }}
    tr:nth-child(even) td {{
      background: #fcfcfd;
    }}
    .formula-math {{
      font-family: "Cambria Math", Georgia, serif;
      font-size: 10.8pt;
      text-align: center;
      margin: 4px 0;
      color: #1f2328;
    }}
    .math {{
      font-family: "Cambria Math", Georgia, serif;
      font-style: italic;
    }}
    .figure-card {{
      border: 1px solid #d0d7de;
      border-radius: 6px;
      padding: 8px 10px 6px 10px;
      margin: 8px 0 10px 0;
      background: #ffffff;
      break-inside: avoid;
      text-align: center;
    }}
    .figure-caption {{
      font-size: 8.6pt;
      color: #57606a;
      text-align: center;
      margin-top: 5px;
      font-style: italic;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
      font-size: 8.8pt;
      background-color: rgba(175, 184, 193, 0.2);
      padding: 2px 4px;
      border-radius: 3px;
      color: #1f2328;
    }}
    pre {{
      background-color: #f6f8fa;
      border: 1px solid #d0d7de;
      color: #1f2328;
      padding: 8px 10px;
      border-radius: 6px;
      font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
      font-size: 7.9pt;
      line-height: 1.32;
      margin: 5px 0 8px 0;
      overflow-x: hidden;
      white-space: pre-wrap;
      break-inside: avoid;
    }}
    pre code {{
      background-color: transparent;
      padding: 0;
      border-radius: 0;
      color: inherit;
      font-size: inherit;
    }}
    .page-break {{
      page-break-before: always;
    }}
    ul {{
      margin: 4px 0 8px 18px;
      padding: 0;
    }}
    li {{
      margin-bottom: 3px;
    }}
  </style>
</head>
<body>
{full_body}
</body>
</html>
"""

with open(html_out, "w", encoding="utf-8") as f:
    f.write(full_html)

print("Generated HTML from Markdown:", html_out)

# Call Chrome to print to PDF
html_url = f"file:///{html_out.replace(os.sep, '/')}"
chrome_bin = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(chrome_bin):
    chrome_bin = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

res = subprocess.run([
    chrome_bin,
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--user-data-dir={user_dir}",
    f"--print-to-pdf={pdf_out}",
    html_url
], capture_output=True, text=True)

print("Chrome return code:", res.returncode)
print("PDF output exists:", os.path.exists(pdf_out), "Size:", os.path.getsize(pdf_out) if os.path.exists(pdf_out) else 0)
