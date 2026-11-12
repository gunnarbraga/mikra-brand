#!/usr/bin/env python3
"""Mikra brand package generator.

Rebuilds every logo, symbol, lockup, app icon, colour file, background and
social/office asset from the designer originals in `09 Source/SVG`.

    python -m pip install pillow resvg-py
    python build.py

Only approved logo colours are generated: sea (on white) and white (on any
coloured surface). There is no black, grey or print-blue logo file. To change a hex
value edit PALETTE below and rerun. Nothing in 01-08 is hand-edited.
"""
import io, json, re, struct, shutil, zipfile
from pathlib import Path
import resvg_py
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "09 Source" / "SVG"

# ---------------------------------------------------------------- palette
PALETTE = {
    # name:        (hex,      Icelandic,     group,     pantone,        cmyk,            use)
    "sea":        ("#0037FF", "Mikra-blár",  "blues",   "2728 C",       (100, 70, 0, 0),  "Merkið og hnappar: lógó á hvítu, hnappar, línur, ikon. Ekki yfirborðslitur. Skjágildi."),
    "sea-print":  ("#0047BB", "Prentblár",   "blues",   "2728 C",       (100, 70, 0, 0),  "Prentforskrift fyrir Sea: Pantone 2728 C fyrir bíla, skilti, bás og allt prentað í lit. Ekki sérstakt lógó, sama skrá. Yfirborð aðeins þar sem það er tilgreint sérstaklega."),
    "deep-sea":   ("#0A1F5C", "Dökkblár",    "blues",   "staðfesta",    None,             "Yfirborðsliturinn: titilglærur, hero, gaflar, borðar, kaflaskil, skjalahausar. Á Deep Sea er allt annað hvítt."),
    "kelp":       ("#5FA84E", "Grænn",       "signal",  "staðfesta",    None,             "Í lagi, sjálfbærni, matvælaöryggi, gröf. Ber hvítan texta."),
    "salmon-deep":("#D4551A", "Rauðbrúnn",   "signal",  "staðfesta",    None,             "Athygli, nýtt, viðvörun, einn áherslupunktur. Ber hvítan texta."),
    "ice":        ("#F5F8F8", "Ljósgrár",    "neutral", "",             None,             "Aðalbakgrunnur."),
    "mist":       ("#C7DDDB", "Mistur",      "neutral", "",             None,             "Mjúkir fletir, skil."),
    "sky":        ("#B0C7E1", "Ljósblár",    "neutral", "",             None,             "Ljósir bakgrunnar, töflur, tög, aukatexti á dökku."),
    "rock":       ("#8C8C9D", "Grár",        "neutral", "",             None,             "Aukatexti, ikon, vöruheiti, prófunarumhverfi."),
    "rock-dark":  ("#1F2430", "Dökkgrár",    "neutral", "",             None,             "Meginmálstexti í stað hreins svarts. Dökk app-flís."),
    "lava":       ("#000000", "Svart",       "neutral", "Black C",      (0, 0, 0, 100),   "Texti í prenti þar sem Rock Dark dugar ekki. Aldrei á lógóið."),
    "white":      ("#FFFFFF", "Hvítur",      "neutral", "",             (0, 0, 0, 0),     "Lógó á lituðum grunni. Bakgrunnur."),
}
TINTS = (80, 60, 40, 20)   # percent of colour mixed with white

def hex2rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def rgb2hex(r): return "#%02X%02X%02X" % tuple(int(round(v)) for v in r)
def tint(h, pct):
    r = hex2rgb(h); return rgb2hex(tuple(255 - (255 - c) * pct / 100 for c in r))
def cmyk(h):
    r, g, b = (c / 255 for c in hex2rgb(h)); k = 1 - max(r, g, b)
    if k >= 0.999: return (0, 0, 0, 100)
    return tuple(int(round(v * 100)) for v in ((1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k), k))
def HX(name): return PALETTE[name][0]

# ---------------------------------------------------------------- sources
def read(name): return (SRC / name).read_text(encoding="utf-8")
def paths_of(svg): return re.findall(r"<path[^>]*/>", svg)
def setfill(fragment, hexv): return re.sub(r'fill="#[0-9a-fA-F]{3,6}"', f'fill="{hexv}"', fragment)

LOGO = read("mikra_logo_blatt.svg")                 # viewBox 0 0 1260.307 307.806
_lp = paths_of(LOGO)
WORD = "".join(_lp[0:5]); SYM = "".join(_lp[5:8])
# measured bounding boxes in the logo coordinate system
WORD_BOX = (389, 14, 1237, 282); SYM_BOX = (23, 24, 274, 286)
WORD_H = 282 - 34                                   # cap height of the wordmark (M), 248
CLEAR = WORD_H / 2                                  # clear space on every side
LOCKUPS = {"mes": "mikra_logo_mes.svg", "cordex": "mikra_logo_cordex.svg",
           "robotics": "mikra_logo_robotics.svg", "vision": "mikra_logo_vision.svg"}

def svg_doc(vb, body, w=None, h=None):
    x, y, W, H = vb
    size = f' width="{w}" height="{h}"' if w else ""
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{x:.3f} {y:.3f} {W:.3f} {H:.3f}"{size}>\n{body}\n</svg>\n')

def logo_svg(colour):
    """Primary logo, colour from palette, clear space baked into the file."""
    x0, y0, x1, y1 = 23, 14, 1237, 286
    vb = (x0 - CLEAR, y0 - CLEAR, (x1 - x0) + 2 * CLEAR, (y1 - y0) + 2 * CLEAR)
    return svg_doc(vb, setfill(SYM + WORD, HX(colour)))

def symbol_svg(colour, pad=0):
    x0, y0, x1, y1 = SYM_BOX
    vb = (x0 - pad, y0 - pad, (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad)
    return svg_doc(vb, setfill(SYM, HX(colour)))

def stacked_svg(colour):
    """Symbol centred above wordmark. Wordmark width = 1.5 x symbol width, gap = 0.157 x symbol height."""
    sw = SYM_BOX[2] - SYM_BOX[0]; sh = SYM_BOX[3] - SYM_BOX[1]
    ww = WORD_BOX[2] - WORD_BOX[0]; wh = WORD_BOX[3] - WORD_BOX[1]
    scale = 1.5 * sw / ww
    gap = 0.157 * sh
    total_w = 1.5 * sw; total_h = sh + gap + wh * scale
    sym_x = (total_w - sw) / 2 - SYM_BOX[0]; sym_y = -SYM_BOX[1]
    word_x = -WORD_BOX[0] * scale; word_y = sh + gap - WORD_BOX[1] * scale
    body = (f'<g transform="translate({sym_x:.3f},{sym_y:.3f})">{setfill(SYM, HX(colour))}</g>'
            f'<g transform="translate({word_x:.3f},{word_y:.3f}) scale({scale:.5f})">{setfill(WORD, HX(colour))}</g>')
    pad = wh * scale / 2
    return svg_doc((-pad, -pad, total_w + 2 * pad, total_h + 2 * pad), body)

def circle_svg(bg, fg):
    """Symbol at 50 % of the circle diameter."""
    D = 1000; s = 0.5 * D / max(SYM_BOX[2] - SYM_BOX[0], SYM_BOX[3] - SYM_BOX[1])
    sw = (SYM_BOX[2] - SYM_BOX[0]) * s; sh = (SYM_BOX[3] - SYM_BOX[1]) * s
    tx = (D - sw) / 2 - SYM_BOX[0] * s; ty = (D - sh) / 2 - SYM_BOX[1] * s
    body = (f'<circle cx="{D/2}" cy="{D/2}" r="{D/2}" fill="{HX(bg)}"/>'
            f'<g transform="translate({tx:.3f},{ty:.3f}) scale({s:.5f})">{setfill(SYM, HX(fg))}</g>')
    return svg_doc((0, 0, D, D), body)

def lockup_svg(product, logo_colour, word_colour):
    s = read(LOCKUPS[product])
    groups = re.findall(r"<g>.*?</g>(?=\s*(?:<g>|</g>|</svg>))", s, re.S)
    # structure: <g><g>wordmark</g><g>symbol</g></g><g>product</g>
    outer = re.search(r"<g>\s*<g>.*?</g>\s*<g>.*?</g>\s*</g>", s, re.S).group(0)
    prod = s[s.index(outer) + len(outer):]; prod = re.search(r"<g>.*?</g>", prod, re.S).group(0)
    vb = re.search(r'viewBox="([^"]+)"', s).group(1).split()
    vb = [float(v) for v in vb]
    pad = CLEAR * 0.5
    body = setfill(outer, HX(logo_colour)) + setfill(prod, HX(word_colour))
    return svg_doc((vb[0] - pad, vb[1] - pad, vb[2] + 2 * pad, vb[3] + 2 * pad), body)

def tile_svg(bg, fg, style, radius=True, size=512):
    """App icon: rounded square with the white symbol or stacked logo."""
    inner = symbol_svg(fg) if style == "symbol" else stacked_svg(fg)
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', inner).group(1).split()]
    body_inner = re.search(r"<svg[^>]*>(.*)</svg>", inner, re.S).group(1)
    frac = 0.56 if style == "symbol" else 0.72
    s = frac * size / max(vb[2], vb[3])
    tx = (size - vb[2] * s) / 2 - vb[0] * s; ty = (size - vb[3] * s) / 2 - vb[1] * s
    r = size * 0.22 if radius else 0
    body = (f'<rect width="{size}" height="{size}" rx="{r}" ry="{r}" fill="{HX(bg)}"/>'
            f'<g transform="translate({tx:.3f},{ty:.3f}) scale({s:.5f})">{body_inner}</g>')
    return svg_doc((0, 0, size, size), body)


# ---------------------------------------------------------------- periodic wave band (measured from the symbol paths)
WAVE_STRAIGHT = 161.777        # x-run of the straight between two S-curves in the continued wave
WAVE_RISE = 43.66              # the straight rises this much over WAVE_STRAIGHT (same slope as the symbol, 0.27)
WAVE_PERIOD = WAVE_STRAIGHT + 63.79

def _parse_wave(d):
    """Absolute points of one symbol wave. The designer's path is
    M cap-top-right, v, c(corner), l(bottom straight), c(S), l(bottom straight), c(corner), v, l(top straight), c(S), l(top straight) Z.
    Returns the point list P0..P10 and the two S-curves (relative cubics) as drawn."""
    toks = re.findall(r"[MvclZ]|-?\d*\.?\d+", d)
    pts = []; curves = {}; x = y = 0.0; i = 0; k = 0
    while i < len(toks):
        t = toks[i]; i += 1
        if t == "M": x, y = float(toks[i]), float(toks[i+1]); i += 2; pts.append((x, y)); continue
        if t == "v": y += float(toks[i]); i += 1
        elif t == "l": x += float(toks[i]); y += float(toks[i+1]); i += 2
        elif t == "c":
            c = tuple(float(v) for v in toks[i:i+6]); i += 6; curves[len(pts)] = c; x += c[4]; y += c[5]   # keyed by end-point index
        elif t == "Z": break
        pts.append((x, y)); k += 1
    return pts, curves

def wave_continued_path(d, periods):
    """One closed path: the symbol wave exactly as drawn (left cap and all), its right cap replaced by the
    wave running on to the right for `periods` more periods. Top and bottom edges are exact translates,
    so the join is invisible."""
    P, C = _parse_wave(d)
    # P3 = bottom S right end, P4 = bottom S left end, P8 = top S start, P9 = top S end
    sb = C[4]; st = C[9]; corner = C[6]                       # bottom S (drawn leftwards), top S (drawn rightwards)
    off = (P[3][0] - P[9][0], P[3][1] - P[9][1])   # bottom edge = top edge + off
    cmds = [f"M{P[3][0]:.3f},{P[3][1]:.3f}",
            f"c{sb[0]},{sb[1]} {sb[2]},{sb[3]} {sb[4]},{sb[5]}",      # bottom S leftwards
            f"L{P[5][0]:.3f},{P[5][1]:.3f}",
            f"c{corner[0]},{corner[1]} {corner[2]},{corner[3]} {corner[4]},{corner[5]}",  # left bottom corner -> P6
            f"L{P[7][0]:.3f},{P[7][1]:.3f}", f"L{P[8][0]:.3f},{P[8][1]:.3f}",
            f"c{st[0]},{st[1]} {st[2]},{st[3]} {st[4]},{st[5]}"]      # top S rightwards -> P9
    x, y = P[9]; top = []
    for _ in range(periods):
        x += WAVE_STRAIGHT; y -= WAVE_RISE; top.append(f"L{x:.3f},{y:.3f}")
        top.append(f"c{st[0]},{st[1]} {st[2]},{st[3]} {st[4]},{st[5]}"); x += st[4]; y += st[5]
    x += WAVE_STRAIGHT; y -= WAVE_RISE; top.append(f"L{x:.3f},{y:.3f}")      # run off the right edge
    bottom = [f"L{x+off[0]:.3f},{y+off[1]:.3f}"]
    x += off[0]; y += off[1]
    for _ in range(periods):
        x -= WAVE_STRAIGHT; y += WAVE_RISE; bottom.append(f"L{x:.3f},{y:.3f}")
        bottom.append(f"c{st[2]-st[4]:.3f},{st[3]-st[5]:.3f} {st[0]-st[4]:.3f},{st[1]-st[5]:.3f} {-st[4]:.3f},{-st[5]:.3f}")
        x -= st[4]; y -= st[5]
    bottom.append(f"L{P[3][0]:.3f},{P[3][1]:.3f}")
    return " ".join(cmds + top + bottom) + " Z"

def waves_band_svg(colour, W, H, scale, margin=24.0):
    """The three symbol waves, exactly as drawn on the left, continued across a W x H surface.
    `scale` is relative to the symbol; `margin` (symbol units) is the gap before the left caps."""
    periods = int((W / scale) / WAVE_PERIOD) + 2
    parts = [f'<path d="{wave_continued_path(d, periods)}" fill="{HX(colour)}"/>' for d in re.findall(r'd="([^"]+)"', SYM)]
    top = SYM_BOX[1]; bottom = SYM_BOX[3]
    # the wave climbs a little per period (straight rises more than the S drops); centre the whole run, not just the symbol
    climb = ((W / scale - SYM_BOX[2]) / WAVE_PERIOD) * (WAVE_RISE - 40.171)
    tx = margin - SYM_BOX[0]; ty = (H / scale - (bottom - top)) / 2 - top + climb / 2
    body = f'<g transform="scale({scale}) translate({tx:.3f},{ty:.3f})">{"".join(parts)}</g>'
    return svg_doc((0, 0, W, H), body)

# ---------------------------------------------------------------- raster
def png_bytes(svg, width=None, height=None, background=None):
    return resvg_py.svg_to_bytes(svg_string=svg, width=width, height=height, background=background)

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data) if isinstance(data, bytes) else path.write_text(data, encoding="utf-8")

def out_svg_png(folder, stem, svg, widths):
    write(folder / f"{stem}.svg", svg)
    for w in widths:
        write(folder / f"{stem}-{w}.png", png_bytes(svg, width=w))

def clean(folder):
    if folder.exists(): shutil.rmtree(folder)
    folder.mkdir(parents=True)

# ---------------------------------------------------------------- 01-04
LOGO_COLOURS = ["sea", "white"]   # sea-print is a print spec (Pantone 2728 C) for the Sea file, not a logo colour

def build_logos():
    f = ROOT / "01 Logo"; clean(f)
    for c in LOGO_COLOURS: out_svg_png(f, f"mikra-logo-{c}", logo_svg(c), (2000, 600))
    f = ROOT / "02 Stacked"; clean(f)
    for c in LOGO_COLOURS: out_svg_png(f, f"mikra-stacked-{c}", stacked_svg(c), (1200, 400))
    f = ROOT / "03 Symbol"; clean(f)
    for c in LOGO_COLOURS: out_svg_png(f, f"mikra-symbol-{c}", symbol_svg(c), (1000, 256))
    for bg, fg in [("sea", "white"), ("white", "sea"), ("deep-sea", "white"), ("rock-dark", "ice"), ("rock", "white")]:
        out_svg_png(f / "Circle", f"mikra-symbol-circle-{bg}-{fg}", circle_svg(bg, fg), (1000, 256))
    # watermark overlays: transparent symbol at the brand opacities, to lay over any surface
    wm = f / "Watermark"; wm.mkdir()
    for colour, op, nm in [("white", 0.08, "white-8"), ("sky", 0.35, "sky-35"), ("sea", 0.10, "sea-10")]:
        svg = symbol_svg(colour); body = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
        svg = svg.replace(body, f'<g opacity="{op}">{body}</g>')
        write(wm / f"mikra-watermark-{nm}.svg", svg)
        write(wm / f"mikra-watermark-{nm}-3840.png", png_bytes(svg, width=3840))
    # ready-made wave graphics: the three waves of the symbol continued as a periodic band across a screen,
    # same curve, same thickness, same stagger as the symbol. Transparent background.
    wv = f / "Waves"; wv.mkdir()
    for colour in LOGO_COLOURS:   # same rule as the logo: white on colour, Sea on white, nothing else
        for W, H, sc, tag in ((1920, 500, 1.5, "1920x500"), (1920, 820, 2.5, "1920x820"), (3840, 1000, 3.0, "3840x1000")):
            svg = waves_band_svg(colour, W, H, sc)
            write(wv / f"mikra-waves-{colour}-{tag}.svg", svg)
            write(wv / f"mikra-waves-{colour}-{tag}.png", png_bytes(svg, width=W))
    f = ROOT / "04 Product lockups"; clean(f)
    for p in LOCKUPS:
        for lc, wc, tag in [("sea", "rock", "sea"), ("white", "sky", "white")]:
            out_svg_png(f, f"mikra-{p}-{tag}", lockup_svg(p, lc, wc), (2000, 600))

# ---------------------------------------------------------------- 05 app icons
ICON_SETS = {"mikra-general": ("sea", "white"), "mikra-dark": ("rock-dark", "ice"), "mikra-gray": ("rock", "white")}

def build_icons():
    root = ROOT / "05 App icons"; clean(root)
    for name, (bg, fg) in ICON_SETS.items():
        for style in ("symbol", "stacked"):
            d = root / name / style; d.mkdir(parents=True)
            svg = tile_svg(bg, fg, style)
            write(d / "tile.svg", svg)
            imgs = {}
            for s in (16, 32, 48, 64, 96, 128, 192, 215, 256, 384, 512, 36, 72, 144):
                imgs[s] = Image.open(io.BytesIO(png_bytes(svg, width=s, height=s))).convert("RGBA")
            for s in (16, 32, 96, 128): imgs[s].save(d / f"favicon-{s}x{s}.png", optimize=True)
            for s in (128, 192, 256, 384, 512): imgs[s].save(d / f"icon-{s}x{s}.png", optimize=True)
            imgs[256].save(d / "app-icon.png", optimize=True)
            imgs[215].save(d / "myapps-215x215.png", optimize=True)
            imgs[16].save(d / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
                          append_images=[imgs[32], imgs[48], imgs[64]])
            m = d / "Manifest"; m.mkdir()
            for s in (36, 48, 72, 96, 144, 192): imgs[s].save(m / f"launcher-icon-{s}.png", optimize=True)
        # square (no radius) for hosts that round corners themselves
        for style in ("symbol", "stacked"):
            sq = tile_svg(bg, fg, style, radius=False)
            write(root / name / f"myapps-215x215-square-{style}.png", png_bytes(sq, width=215, height=215))
            write(root / name / f"tile-square-{style}.svg", sq)

# ---------------------------------------------------------------- 06 colours
def ase_bytes(colours):
    """Adobe Swatch Exchange, RGB entries."""
    out = io.BytesIO(); out.write(b"ASEF"); out.write(struct.pack(">HH", 1, 0)); out.write(struct.pack(">I", len(colours)))
    for name, h in colours:
        nm = (name + "\0").encode("utf-16-be")
        block = struct.pack(">H", len(name) + 1) + nm + b"RGB " + struct.pack(">fff", *[c / 255 for c in hex2rgb(h)]) + struct.pack(">H", 2)
        out.write(struct.pack(">HI", 1, len(block))); out.write(block)
    return out.getvalue()

def build_colours():
    f = ROOT / "06 Colours"; clean(f)
    rows = []; css = [":root {"]; scss = []; gpl = ["GIMP Palette", "Name: Mikra 2026", "Columns: 5", "#"]; ase = []
    for name, (h, isl, group, pms, cm, use) in PALETTE.items():
        r = hex2rgb(h); c = cm or cmyk(h)
        entry = {"name": name, "icelandic": isl, "group": group, "hex": h, "rgb": list(r),
                 "cmyk": list(c), "cmyk_source": "spec" if cm else "reiknað, staðfesta", "pantone": pms, "use": use,
                 "tints": {str(p): tint(h, p) for p in TINTS} if name != "white" else {}}
        rows.append(entry)
        css.append(f"  --mikra-{name}: {h};"); scss.append(f"$mikra-{name}: {h};")
        gpl.append(f"{r[0]:3d} {r[1]:3d} {r[2]:3d}\tmikra-{name}"); ase.append((f"Mikra {name}", h))
        for p, th in entry["tints"].items():
            css.append(f"  --mikra-{name}-{p}: {th};"); scss.append(f"$mikra-{name}-{p}: {th};")
            gpl.append("%3d %3d %3d\tmikra-%s-%s" % (*hex2rgb(th), name, p)); ase.append((f"Mikra {name} {p}%", th))
        # swatch PNG: solid block over a tint strip (Hoseth style)
        W, H = 600, 460; im = Image.new("RGB", (W, H), "white"); dr = ImageDraw.Draw(im)
        dr.rectangle((0, 0, W, 340), fill=h)
        if entry["tints"]:
            for i, p in enumerate(TINTS): dr.rectangle((i * W / 4, 340, (i + 1) * W / 4, H), fill=tint(h, p))
        if name == "white": dr.rectangle((0, 0, W - 1, H - 1), outline="#E3E7EC")
        im.save(f / f"{name}.png", optimize=True)
    css.append("}")
    write(f / "palette.css", "\n".join(css) + "\n"); write(f / "palette.scss", "\n".join(scss) + "\n")
    write(f / "palette.gpl", "\n".join(gpl) + "\n"); write(f / "palette.json", json.dumps(rows, ensure_ascii=False, indent=2))
    write(f / "palette.ase", ase_bytes(ase))
    return rows

# ---------------------------------------------------------------- 07 backgrounds
def watermark_body(W, H, colour, opacity):
    """Symbol at 135 % of surface height, bleeding off the right edge."""
    sw = SYM_BOX[2] - SYM_BOX[0]; sh = SYM_BOX[3] - SYM_BOX[1]
    s = 1.35 * H / sh; tx = W - 0.72 * sw * s - SYM_BOX[0] * s; ty = (H - sh * s) / 2 - SYM_BOX[1] * s
    return f'<g opacity="{opacity}" transform="translate({tx:.2f},{ty:.2f}) scale({s:.5f})">{setfill(SYM, HX(colour))}</g>'

def surface_svg(kind, W=1920, H=1080):
    if kind == "gradient-deep-sea-to-sea":
        body = (f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{HX("deep-sea")}"/>'
                f'<stop offset="1" stop-color="{HX("sea")}"/></linearGradient></defs><rect width="{W}" height="{H}" fill="url(#g)"/>')
    elif kind.endswith("-watermark"):
        base = kind[:-len("-watermark")]
        wm = ("sky", 0.35) if base == "ice" else ("white", 0.08)
        body = f'<rect width="{W}" height="{H}" fill="{HX(base)}"/>' + watermark_body(W, H, *wm)
    else:
        body = f'<rect width="{W}" height="{H}" fill="{HX(kind[len("solid-"):])}"/>'
    return svg_doc((0, 0, W, H), body)

SURFACES = ["deep-sea-watermark", "ice-watermark", "rock-dark-watermark",   # no Sea surface: Sea is logo and buttons only
            "solid-deep-sea", "solid-ice", "solid-rock-dark", "solid-sea-print"]

def build_backgrounds():
    f = ROOT / "07 Backgrounds"; clean(f)
    for k in SURFACES:
        svg = surface_svg(k); stem = f"{k}-1920x1080"
        if not k.startswith("solid-"): write(f / f"{stem}.svg", svg)
        write(f / f"{stem}.png", png_bytes(svg, width=1920))
    # 4K versions of the four surfaces
    for k in SURFACES[:4]: write(f / f"{k}-3840x2160.png", png_bytes(surface_svg(k), width=3840))

# ---------------------------------------------------------------- 08 social and office
def place(inner_svg, W, H, box, align="center"):
    """Place an SVG document inside a (x, y, w, h) box, preserving aspect."""
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', inner_svg).group(1).split()]
    body = re.search(r"<svg[^>]*>(.*)</svg>", inner_svg, re.S).group(1)
    bx, by, bw, bh = box; s = min(bw / vb[2], bh / vb[3])
    w, h = vb[2] * s, vb[3] * s
    x = bx + (bw - w) / 2 if align == "center" else (bx if align == "left" else bx + bw - w)
    y = by + (bh - h) / 2
    return f'<g transform="translate({x - vb[0]*s:.3f},{y - vb[1]*s:.3f}) scale({s:.5f})">{body}</g>'

def build_social():
    f = ROOT / "08 Social and office"; clean(f)
    for bg, fg in [("sea", "white"), ("deep-sea", "white"), ("rock-dark", "ice")]:
        write(f / f"avatar-400-{bg}.png", png_bytes(circle_svg(bg, fg), width=400))
        write(f / f"avatar-400-{bg}-square.png", png_bytes(tile_svg(bg, fg, "symbol", radius=False, size=400), width=400))
    # LinkedIn banner 1584x396: deep sea watermark, white logo right, left third clear for the avatar
    W, H = 1584, 396
    body = f'<rect width="{W}" height="{H}" fill="{HX("deep-sea")}"/>' + watermark_body(W, H, "white", 0.08) + \
           place(logo_svg("white"), W, H, (W * 0.55, H * 0.22, W * 0.40, H * 0.56), "right")
    svg = svg_doc((0, 0, W, H), body); write(f / "linkedin-banner-1584x396.svg", svg); write(f / "linkedin-banner-1584x396.png", png_bytes(svg, width=W))
    # Open Graph 1200x630
    W, H = 1200, 630
    body = f'<rect width="{W}" height="{H}" fill="{HX("deep-sea")}"/>' + watermark_body(W, H, "white", 0.08) + \
           place(logo_svg("white"), W, H, (W * 0.12, H * 0.28, W * 0.5, H * 0.44), "left")
    svg = svg_doc((0, 0, W, H), body); write(f / "og-image-1200x630.svg", svg); write(f / "og-image-1200x630.png", png_bytes(svg, width=W))
    # email signature: sea logo with padding, 320 and 640
    for w, nm in ((320, "email-signature-logo-320.png"), (640, "email-signature-logo-640@2x.png")):
        write(f / nm, png_bytes(logo_svg("sea"), width=w))
    write(f / "email-signature-symbol-64.png", png_bytes(symbol_svg("sea", pad=12), width=64))
    # Word header logos 1200 px
    for c, nm in (("sea", "sea"), ("white", "white")):
        write(f / f"word-header-logo-{nm}-1200.png", png_bytes(logo_svg(c), width=1200))
    # CodeTwo email signature template: static source, copied as is
    sig = ROOT / "09 Source" / "email-signature"
    if sig.exists():
        shutil.copytree(sig, f / "email-signature", ignore=shutil.ignore_patterns("_preview.html"))
    # PowerPoint backgrounds
    write(f / "pptx-title-dark-background-1920x1080.png", png_bytes(surface_svg("deep-sea-watermark"), width=1920))
    write(f / "pptx-title-light-background-1920x1080.png", png_bytes(surface_svg("ice-watermark"), width=1920))
    write(f / "pptx-section-background-1920x1080.png", png_bytes(surface_svg("solid-deep-sea"), width=1920))
    write(f / "pptx-content-background-1920x1080.png", png_bytes(surface_svg("solid-ice"), width=1920))
    office = ROOT / "09 Source" / "office"
    if office.exists():
        for p in office.iterdir(): shutil.copy(p, f / p.name)

# ---------------------------------------------------------------- zips
def build_zips():
    z = ROOT / "Downloads"; clean(z)
    def zipdir(name, folders):
        with zipfile.ZipFile(z / name, "w", zipfile.ZIP_DEFLATED) as zf:
            for fo in folders:
                for p in sorted((ROOT / fo).rglob("*")):
                    if p.is_file() and p.name != "Thumbs.db": zf.write(p, p.relative_to(ROOT))
    zipdir("mikra-merki.zip", ["01 Logo", "02 Stacked", "03 Symbol"])
    zipdir("mikra-vorulinur.zip", ["04 Product lockups"])
    zipdir("mikra-app-ikon.zip", ["05 App icons"])
    zipdir("mikra-litir.zip", ["06 Colours"])
    zipdir("mikra-bakgrunnar.zip", ["07 Backgrounds"])
    zipdir("mikra-social-office.zip", ["08 Social and office"])
    zipdir("mikra-frumskrar.zip", ["09 Source"])
    zipdir("mikra-brand-allt.zip", ["01 Logo", "02 Stacked", "03 Symbol", "04 Product lockups", "05 App icons",
                                   "06 Colours", "07 Backgrounds", "08 Social and office", "09 Source"])

if __name__ == "__main__":
    import datetime
    build_logos(); print("01-04 ok")
    build_icons(); print("05 ok")
    rows = build_colours(); print("06 ok")
    build_backgrounds(); print("07 ok")
    build_social(); print("08 ok")
    build_zips(); print("zips ok")
    from brandsite import build_site
    src = (ROOT / "09 Source" / "site" / "guide_src.html").read_text(encoding="utf-8")
    depth = len(re.findall(r"<div\b", src)) - len(re.findall(r"</div>", src))
    assert depth == 0, f"guide_src.html: <div> nesting off by {depth}, fix the source before building"
    vs = (ROOT / "09 Source" / "site" / "vinnuskjal_src.html").read_text(encoding="utf-8")
    vd = len(re.findall(r"<div\b", vs)) - len(re.findall(r"</div>", vs))
    assert vd == 0, f"vinnuskjal_src.html: <div> nesting off by {vd}"
    build_site(rows, datetime.date.today().isoformat()); print("index.html ok")
