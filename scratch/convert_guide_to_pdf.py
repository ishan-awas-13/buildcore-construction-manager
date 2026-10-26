import os
import sys
import subprocess
import markdown
import re

def convert_markdown_to_pdf():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_path = os.path.join(root_dir, 'BUILDCORE_ARCHITECTURE_AND_LEARNING_GUIDE.md')
    html_path = os.path.join(root_dir, 'scratch', 'guide_doc.html')
    pdf_path = os.path.join(root_dir, 'BuildCore_Architecture_and_Learning_Guide.pdf')
    svg_path = os.path.join(root_dir, 'BuildCore_ER_Diagram.svg')

    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found.")
        return False

    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Read vector SVG
    svg_content = ""
    if os.path.exists(svg_path):
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        # Ensure SVG scales responsively to container
        svg_content = re.sub(r'width="\d+"\s+height="\d+"', 'width="100%" height="auto"', svg_content)

    # 1. Replace the markdown image tag for BuildCore_ER_Diagram.png with the inline responsive SVG diagram
    def replace_er_image(match):
        return f"""
<div class="er-diagram-container">
    <div class="diagram-info-banner">
        <div class="diagram-title">BuildCore Visual Entity-Relationship Architecture</div>
        <div class="diagram-meta">15 Relational Tables &bull; CHECK Constraints &bull; Snapshot Rates &bull; 5 Automated PostgreSQL Views</div>
        <div class="diagram-desc">Below is the complete normalized relational schema. Standalone presentation assets (<code>BuildCore_ER_Diagram.svg</code> vector and <code>BuildCore_ER_Diagram.png</code> 3200&times;2300 HD PNG) are available in the project root for drag-and-drop slide insertion into Microsoft PowerPoint and deep zooming.</div>
    </div>
    <div class="er-svg-wrapper">
        {svg_content}
    </div>
</div>
"""
    processed_md = re.sub(r'!\[BuildCore Entity-Relationship Diagram\]\(BuildCore_ER_Diagram\.png\)', replace_er_image, md_content)

    # 2. Replace mermaid block with clean, styled schema code card so it renders cleanly without client-side JS failure
    def replace_mermaid(match):
        code = match.group(1).strip()
        return f"""
<div class="mermaid-schema-card">
    <div class="mermaid-schema-header">
        <span class="badge">ERD Formal Specification</span>
        <span>Mermaid / Relational Entities</span>
    </div>
    <pre><code>{code}</code></pre>
</div>
"""
    processed_md = re.sub(r'```mermaid\s+(.*?)\s+```', replace_mermaid, processed_md, flags=re.DOTALL)

    # Convert to HTML with extensions
    html_body = markdown.markdown(
        processed_md,
        extensions=['tables', 'fenced_code', 'toc', 'sane_lists']
    )

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>BuildCore Infrastructure: Architecture & Learning Guide</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        @page {{
            size: A4 portrait;
            margin: 16mm 14mm 16mm 14mm;
            @bottom-right {{
                content: "Page " counter(page);
                font-family: 'Inter', sans-serif;
                font-size: 8pt;
                color: #64748b;
            }}
            @top-right {{
                content: "BuildCore Infrastructure | Architecture & Learning Guide";
                font-family: 'Inter', sans-serif;
                font-size: 8pt;
                color: #94a3b8;
            }}
        }}

        *, *::before, *::after {{
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 9.5pt;
            line-height: 1.55;
            color: #1e293b;
            background-color: #ffffff;
            margin: 0;
            padding: 0;
        }}

        /* Document Header / Cover Banner */
        .doc-header {{
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
            color: #ffffff;
            padding: 24px 28px;
            border-radius: 8px;
            margin-bottom: 24px;
        }}

        .doc-header h1 {{
            color: #ffffff !important;
            margin: 0 0 8px 0;
            font-size: 20pt;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}

        .doc-header p {{
            margin: 0;
            font-size: 10.5pt;
            opacity: 0.9;
        }}

        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Inter', sans-serif;
            color: #0f172a;
            font-weight: 700;
            letter-spacing: -0.015em;
            margin-top: 1.4em;
            margin-bottom: 0.5em;
            break-after: avoid;
            page-break-after: avoid;
        }}

        h1 {{
            font-size: 16pt;
            border-bottom: 2px solid #2563eb;
            padding-bottom: 6px;
            margin-top: 2em;
            color: #1e3a8a;
        }}

        h2 {{
            font-size: 13pt;
            color: #1e40af;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 4px;
            margin-top: 1.6em;
        }}

        h3 {{
            font-size: 11pt;
            color: #1e293b;
        }}

        p, ul, ol {{
            margin-top: 0;
            margin-bottom: 0.8em;
        }}

        ul, ol {{
            padding-left: 20px;
        }}

        li {{
            margin-bottom: 0.3em;
        }}

        /* Code & Pre */
        code {{
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 8.5pt;
            background-color: #f1f5f9;
            color: #0f172a;
            padding: 2px 5px;
            border-radius: 4px;
            border: 1px solid #e2e8f0;
        }}

        pre {{
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 8pt;
            background-color: #0f172a;
            color: #f8fafc;
            padding: 12px 14px;
            border-radius: 6px;
            overflow-x: auto;
            line-height: 1.45;
            margin: 12px 0;
            border: 1px solid #1e293b;
            break-inside: avoid;
            page-break-inside: avoid;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
            border: none;
            font-size: inherit;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.5pt;
            margin: 14px 0;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        th {{
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
            color: #ffffff;
            font-weight: 600;
            text-align: left;
            padding: 7px 10px;
            border: 1px solid #1e40af;
        }}

        td {{
            padding: 6px 10px;
            border: 1px solid #cbd5e1;
            vertical-align: top;
        }}

        tr:nth-child(even) {{
            background-color: #f8fafc;
        }}

        /* Blockquotes / Callouts */
        blockquote {{
            margin: 14px 0;
            padding: 10px 14px;
            background-color: #eff6ff;
            border-left: 4px solid #2563eb;
            color: #1e3a8a;
            border-radius: 0 6px 6px 0;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        blockquote p {{
            margin: 0;
            font-weight: 500;
        }}

        /* Visual ER Diagram Styling */
        .er-diagram-container {{
            margin: 18px 0 24px 0;
            padding: 14px;
            background-color: #f8fafc;
            border: 1.5px solid #cbd5e1;
            border-radius: 8px;
            break-inside: avoid;
            page-break-inside: avoid;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}

        .diagram-info-banner {{
            background: #eff6ff;
            border-left: 4px solid #2563eb;
            padding: 10px 14px;
            margin-bottom: 12px;
            border-radius: 0 4px 4px 0;
            color: #1e3a8a;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}

        .diagram-title {{
            font-size: 11pt;
            font-weight: 700;
            color: #1e3a8a;
            margin-bottom: 2px;
        }}

        .diagram-meta {{
            font-size: 8.5pt;
            font-weight: 600;
            color: #2563eb;
            margin-bottom: 4px;
        }}

        .diagram-desc {{
            font-size: 8pt;
            color: #475569;
            line-height: 1.4;
        }}

        .er-svg-wrapper {{
            width: 100%;
            text-align: center;
        }}

        .er-svg-wrapper svg {{
            width: 100% !important;
            height: auto !important;
            display: block;
            margin: 0 auto;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            background-color: #f8fafc;
        }}

        /* Mermaid Schema Syntax Card */
        .mermaid-schema-card {{
            background-color: #0f172a;
            border-radius: 8px;
            border: 1px solid #1e293b;
            margin: 16px 0;
            overflow: hidden;
            page-break-inside: avoid;
            break-inside: avoid;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}

        .mermaid-schema-header {{
            background-color: #1e293b;
            padding: 8px 14px;
            color: #94a3b8;
            font-size: 8pt;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
        }}

        .mermaid-schema-header .badge {{
            background-color: #2563eb;
            color: #ffffff;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 7.5pt;
            font-weight: 700;
        }}

        .mermaid-schema-card pre {{
            margin: 0;
            padding: 12px 14px;
            background: transparent;
            border: none;
            font-size: 7.5pt;
            line-height: 1.4;
            color: #e2e8f0;
        }}

        hr {{
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 22px 0;
        }}

        strong {{
            font-weight: 700;
            color: #0f172a;
        }}

        a {{
            color: #2563eb;
            text-decoration: none;
        }}

        /* Print Specifics */
        @media print {{
            body {{
                background-color: #ffffff;
                color: #000000;
            }}
            .doc-header {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            th {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            pre {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            blockquote {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            .er-diagram-container {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            .diagram-info-banner {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            .mermaid-schema-card {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            .page-break {{
                page-break-before: always;
            }}
        }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

    print(f"HTML successfully generated at: {html_path}")

    # Convert to PDF via msedge
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    ]
    browser_exe = None
    for p in edge_paths:
        if os.path.exists(p):
            browser_exe = p
            break

    if not browser_exe:
        print("Error: Neither msedge nor chrome found on system.")
        return False

    print(f"Using browser: {browser_exe}")
    cmd = [
        browser_exe,
        "--headless",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_path}",
        html_path
    ]

    print("Running headless PDF generator...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        print(f"SUCCESS: PDF generated successfully ({os.path.getsize(pdf_path)} bytes) at:\n{pdf_path}")
        return True
    else:
        print(f"PDF generation failed: {res.stderr}")
        return False

if __name__ == '__main__':
    convert_markdown_to_pdf()
