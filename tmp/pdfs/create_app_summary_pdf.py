from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

output_path = r"output/pdf/app-summary-one-page.pdf"

c = canvas.Canvas(output_path, pagesize=LETTER)
width, height = LETTER

left = 0.75 * inch
right = width - 0.75 * inch
y = height - 0.7 * inch

# Title
c.setFont("Helvetica-Bold", 18)
c.drawString(left, y, "App Summary (Repo Evidence)")
y -= 0.18 * inch
c.setStrokeColor(colors.HexColor("#BDBDBD"))
c.line(left, y, right, y)
y -= 0.22 * inch

section_gap = 0.18 * inch
line_gap = 0.16 * inch
bullet_indent = 0.2 * inch


def heading(text):
    global y
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#1F2937"))
    c.drawString(left, y, text)
    y -= line_gap


def body_line(text, indent=0):
    global y
    c.setFont("Helvetica", 9.6)
    c.setFillColor(colors.black)
    c.drawString(left + indent, y, text)
    y -= line_gap


heading("What It Is")
body_line("Not found in repo. This repository currently contains only .git metadata and no app files.")
y -= section_gap

heading("Who It's For")
body_line("Primary user/persona: Not found in repo.")
y -= section_gap

heading("What It Does")
features = [
    "No application features are implemented in the current repository state.",
    "Git repository initialized (branch exists, no commits).",
    "No source files found under workspace root.",
    "No package/dependency manifests found.",
    "No configuration files for runtime/services found.",
    "No tests, scripts, or documentation found.",
]
for item in features:
    body_line(f"- {item}", indent=bullet_indent)
y -= section_gap

heading("How It Works (Architecture)")
body_line("Components/services/data flow: Not found in repo.")
body_line("Evidence basis: filesystem scan shows only .git internals; no runnable app artifacts.")
y -= section_gap

heading("How To Run")
steps = [
    "1. Not found in repo: no executable source, entrypoint, or run script detected.",
    "2. Not found in repo: no dependency manifest (e.g., package.json, pyproject.toml).",
    "3. Not found in repo: no setup instructions or README available.",
]
for step in steps:
    body_line(step, indent=bullet_indent)

# Footer
c.setFont("Helvetica-Oblique", 8)
c.setFillColor(colors.HexColor("#4B5563"))
c.drawRightString(right, 0.5 * inch, "Generated from repository evidence only")

c.save()
print(output_path)
