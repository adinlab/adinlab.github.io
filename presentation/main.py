import math
import yaml

# ── Configuration ────────────────────────────────────────────────────────────
YAML_FILE   = "team.yaml"  # todo: update this path if your YAML is located elsewhere
OUTPUT_FILE = "team_frame.tex"
COLS          = None       # None = auto-balance based on member count (recommended)
                           # or set an integer e.g. 4 to force a fixed column count
MAX_ROWS      = 2          # maximum number of rows in the team grid
PHOTO_SIZE    = "1.1cm"   # radius of the circular clip
IMAGE_WIDTH   = "2.2cm"   # width fed to \includegraphics (≈ 2× radius)
COL_SEP       = "0.6cm"   # extra horizontal space between columns
SHOW_POSITION = True       # set False to hide the position/role label

QR_CODES = [
    # Each entry: label (str), url (str), image (str | None)
    # If image is None a TikZ placeholder box is drawn instead.
    {"label": "Adin Lab",   "url": "https://adinlab.github.io/",          "image": 'assets/img/adinlab.png'},
    {"label": "ObjectRL",   "url": "https://github.com/adinlab/objectrl", "image": 'assets/img/objectrl.png'},
]
# ─────────────────────────────────────────────────────────────────────────────


def get_position(member: dict, category: str) -> str:
    """Extract a short position label from the member dict."""
    if category == "faculty":
        return "Lab Head" if member.get("head") else "Assistant Professor"
    if category == "researchers":
        areas = member.get("research_areas", "")
        if "Postdoc" in areas:
            return "Postdoc"
        if "PhD" in areas:
            return "PhD"
        return "Researcher"
    return ""


def circular_photo(image_path: str) -> str:
    """Return TikZ snippet for a circular-clipped photo."""
    return (
        r"\begin{tikzpicture}" + "\n"
        r"  \clip (0,0) circle (" + PHOTO_SIZE + r");" + "\n"
        r"  \node at (0,0) {\includegraphics"
        r"[width=" + IMAGE_WIDTH + r",height=" + IMAGE_WIDTH + r"]"
        r"{" + image_path + r"}};" + "\n"
        r"\end{tikzpicture}"
    )


def member_cell(member: dict, category: str) -> str:
    """Return a minipage cell with photo + name + position."""
    image    = member.get("image", "placeholder")
    name     = member["name"]
    position = get_position(member, category)
    photo    = circular_photo(image)

    position_line = (
        r"{\tiny\itshape " + position + r"}" + "\n"
        if SHOW_POSITION else ""
    )

    return (
        r"\begin{minipage}[t]{2.2cm}\centering" + "\n"
        + photo + "\\\\[-6pt]\n"
        r"{\tiny\bfseries " + name + r"}\\[-5pt]" + "\n"
        + position_line
        + r"\end{minipage}"
    )


def auto_cols(n: int) -> int:
    """Pick the most balanced column count for n members.

    Strategy: find the col count c in [2..max_cols] that minimises the
    remainder (last-row stragglers).  Among ties prefer a layout closer
    to square (fewer rows).  Single-member edge case returns 1.
    """
    if n <= 1:
        return 1
    max_cols = min(n, 5)          # never wider than 5 columns
    best_c, best_remainder = 2, n
    for c in range(2, max_cols + 1):
        remainder = n % c          # 0 = perfectly even
        if remainder < best_remainder or (
            remainder == best_remainder and (n // c) < (n // best_c)
        ):
            best_c, best_remainder = c, remainder
    return best_c


def build_grid(members: list[tuple[dict, str]]) -> str:
    """Arrange member cells into a LaTeX tabular grid, centering any incomplete last row."""
    n = len(members)
    cols = COLS if COLS is not None else max(auto_cols(n), math.ceil(n / MAX_ROWS))

    # Split into full rows and a (possibly partial) last chunk
    chunks = [members[i:i+cols] for i in range(0, len(members), cols)]

    rows = []
    for chunk in chunks:
        cells = [member_cell(m, cat) for m, cat in chunk]

        if len(cells) == cols:
            # Full row — normal cells
            rows.append(" & ".join(cells) + r" \\[6pt]")
        else:
            # Incomplete last row — center it with \multicolumn
            inner = r"\hfill ".join(cells) + r"\hfill"
            rows.append(
                r"\multicolumn{" + str(cols) + r"}{c}{"
                + inner + r"} \\[6pt]"
            )

    col_spec = ("@{\\hspace{" + COL_SEP + "}}c") * cols + "@{\\hspace{" + COL_SEP + "}}"
    lines = [
        r"\begin{tabular}{" + col_spec + "}",
        *rows,
        r"\end{tabular}",
    ]
    return "\n".join(lines)


def qr_cell(qr: dict) -> str:
    """Return a minipage for a QR entry (image or TikZ placeholder)."""
    label = qr["label"]
    url   = qr["url"]
    image = qr.get("image")

    if image:
        graphic = r"\includegraphics[width=1.8cm,height=1.8cm]{" + image + r"}"
    else:
        graphic = (
            r"\begin{tikzpicture}" + "\n"
            r"  \draw[rounded corners=3pt, gray] (0,0) rectangle (1.8cm,1.8cm);" + "\n"
            r"  \node[gray, font=\tiny, align=center] at (0.9cm,0.9cm) {QR Code\\" + "\n"
            r"  \url{" + url[:30] + r"...}};" + "\n"
            r"\end{tikzpicture}"
        )

    return (
        r"\begin{minipage}{2.2cm}\centering" + "\n"
        r"\href{" + url + r"}{\mbox{" + graphic + r"}}\\[-7pt]" + "\n"
        r"\href{" + url + r"}{{\tiny " + label + r"}}" + "\n"
        r"\end{minipage}"
    )


def build_frame(members: list[tuple[dict, str]]) -> str:
    grid = build_grid(members)
    qr_cells = [qr_cell(qr) for qr in QR_CODES]
    col_spec  = "c" * len(qr_cells)
    qr_row    = " & ".join(qr_cells)

    frame = (
        r"% ── Required packages (add to your preamble) ──────────────────────" + "\n"
        r"% \usepackage{tikz}" + "\n"
        r"% \usepackage{graphicx}" + "\n"
        r"% \usepackage{url}" + "\n"
        r"% \usepackage{booktabs}" + "\n"
        r"% \usepackage{hyperref}" + "\n"
        r"% ────────────────────────────────────────────────────────────────────" + "\n\n"
        r"\begin{frame}{The ADIN Lab says thank you!}" + "\n"
        r"  \centering" + "\n\n"
        r"  % ── Team grid ──────────────────────────────────────────────────" + "\n"
        + "  " + grid.replace("\n", "\n  ") + "\n\n"
        r"  \vfill" + "\n\n"
        r"  % ── QR Codes ───────────────────────────────────────────────────" + "\n"
        r"  \begin{tabular}{" + col_spec + r"}" + "\n"
        r"    " + qr_row + "\n"
        r"  \end{tabular}" + "\n\n"
        r"\end{frame}" + "\n"
    )
    return frame


def main():
    with open(YAML_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Collect active members in display order: faculty → researchers only
    members: list[tuple[dict, str]] = []
    for category in ("faculty", "researchers"):
        for member in data.get(category, []):
            members.append((member, category))

    frame_tex = build_frame(members)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(frame_tex)

    cols = COLS if COLS is not None else max(auto_cols(len(members)), math.ceil(len(members) / MAX_ROWS))
    print(f"✓  Generated '{OUTPUT_FILE}' with {len(members)} members.")
    print(f"   Layout: {cols} columns × {-(-len(members) // cols)} rows  {'(auto-balanced)' if COLS is None else '(manual)'}")


if __name__ == "__main__":
    main()