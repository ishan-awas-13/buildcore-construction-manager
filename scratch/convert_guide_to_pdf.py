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

    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found.")
        return False

    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Pre-process Mermaid blocks so Mermaid.js can render them
    # Replace ```mermaid ... ``` with <div class="mermaid"> ... </div>
    def replace_mermaid(match):
        code = match.group(1).strip()
        return f'<div class="mermaid">\n{code}\n</div>'

    processed_md = re.sub(r'```mermaid\s+(.*?)\s+```', replace_mermaid, md_content, flags=re.DOTALL)

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
    <!-- Mermaid.js -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            themeVariables: {{
                primaryColor: '#e0e7ff',
                primaryBorderColor: '#3b82f6',
                primaryTextColor: '#1e3a8a',
                lineColor: '#2563eb'
            }}
        }});
    </script>
    <style>
        @page {{
            size: A4;
            margin: 18mm 16mm 18mm 16mm;
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

        /* Mermaid Diagrams Container */
        .mermaid {{
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 12px;
            margin: 14px 0;
            text-align: center;
            break-inside: avoid;
            page-break-inside: avoid;
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
