import os
import subprocess
from PIL import Image

workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
svg_file = os.path.join(workspace_root, 'BuildCore_ER_Diagram.svg')
png_file = os.path.join(workspace_root, 'BuildCore_ER_Diagram.png')
html_file = os.path.join(workspace_root, 'scratch', 'svg_viewer_inline.html')

with open(svg_file, 'r', encoding='utf-8') as f:
    svg_content = f.read()

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 0; background: #f8fafc; display: flex; justify-content: center; align-items: center; width: 1600px; height: 1150px; overflow: hidden; }}
  svg {{ width: 1600px; height: 1150px; display: block; }}
</style>
</head>
<body>
{svg_content}
</body>
</html>
"""

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html)

edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
browser = edge_exe if os.path.exists(edge_exe) else chrome_exe

cmd = [
    browser,
    "--headless",
    "--disable-gpu",
    "--window-size=1600,1150",
    f"--screenshot={png_file}",
    html_file
]
print("Running screenshot command...")
res = subprocess.run(cmd, capture_output=True, text=True)
print("Returncode:", res.returncode)
print("PNG file size:", os.path.getsize(png_file))

im = Image.open(png_file)
print("PNG dimensions:", im.size)
colors = im.getcolors(maxcolors=200000)
print("Num distinct colors:", len(colors) if colors else "over 200000")
