"""Builds index.html, the one Mikra brand guide: rules and downloads in the same page, section by section.
Source text lives in 09 Source/site/guide_src.html (tokens like {{blatt}} are resolved to package files).
Also writes Mikra_Brand_Guide_standalone.html, the same page with every image embedded, for sharing
with people who do not have the folder (no download buttons there).

Called by build.py after the assets exist."""
import base64, html, json, mimetypes, re, shutil, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "09 Source" / "site" / "guide_src.html"

def esc(s): return html.escape(str(s), quote=True)
def img(path, cls="", style=""):
    return f'<img src="{esc(path)}" alt="" class="{cls}" style="{style}" loading="lazy">'

# ---------------------------------------------------------------- token map (guide tokens -> package files)
TOKENS = {
    "blatt": img("01 Logo/mikra-logo-sea.svg", "lg"), "hvitt": img("01 Logo/mikra-logo-white.svg", "lg"),
    "svart": img("10 Daemi/ekki-notad/logo-svart.png", "lg"),
    "logo_rd": img("10 Daemi/ekki-notad/logo-dokkgratt.png", "lg"), "logo_sky": img("10 Daemi/ekki-notad/logo-ljosblatt.png", "lg"),
    "logo_rock": img("10 Daemi/ekki-notad/logo-gratt.png", "lg"), "logo_deep": img("10 Daemi/ekki-notad/logo-dokkblatt.png", "lg"),
    "takn": img("03 Symbol/mikra-symbol-sea.svg", "tk"), "takn_h": img("03 Symbol/mikra-symbol-white.svg", "tk"),
    "hringur": img("03 Symbol/Circle/mikra-symbol-circle-sea-white.svg", "tk"),
    "stacked": "02 Stacked/mikra-stacked-sea.svg",
    "cordex": img("04 Product lockups/mikra-cordex-sea.svg", "sub"), "mes": img("04 Product lockups/mikra-mes-sea.svg", "sub"),
    "robotics": img("04 Product lockups/mikra-robotics-sea.svg", "sub"), "vision": img("04 Product lockups/mikra-vision-sea.svg", "sub"),
    "mk_w": img("01 Logo/mikra-logo-white.svg", "mk"), "mk_b": img("01 Logo/mikra-logo-sea.svg", "mk"),
    "tk_w": img("03 Symbol/mikra-symbol-white.svg", "mk"), "tk_b": img("03 Symbol/mikra-symbol-sea.svg", "mk"),
    "card1": "10 Daemi/nafnspjald-fram.jpg", "card2": "10 Daemi/nafnspjald-bak.jpg", "car_side": "10 Daemi/bill-hlid.jpg",
    "car_fr": "10 Daemi/bill-fram-aftan.jpg", "car_render": "10 Daemi/bill-render.jpg", "tee": "10 Daemi/bolur.jpg",
    "caps": "10 Daemi/hufur.jpg", "sig": "08 Social and office/email-signature/signature-preview.png",
    "bld1": "10 Daemi/skilti-bygging.jpg", "bld2": "10 Daemi/skilti-inngangur.jpg", "booth": "10 Daemi/bas.jpg",
    "e8": "10 Daemi/ennemm-vefur.jpg", "e9": "10 Daemi/ennemm-farsimi.jpg", "e10": "10 Daemi/ennemm-fani-fatnadur.jpg",
    "e11": "10 Daemi/ennemm-bill.jpg", "e12": "10 Daemi/ennemm-storflotur.jpg", "e13": "10 Daemi/ennemm-glaerur.jpg",
    "bg_deep": "07 Backgrounds/deep-sea-watermark-1920x1080.png",
    "bg_ice": "07 Backgrounds/ice-watermark-1920x1080.png", "bg_rock": "07 Backgrounds/rock-dark-watermark-1920x1080.png",
    "ic_gen_sy": "05 App icons/mikra-general/symbol/icon-256x256.png", "ic_gen_st": "05 App icons/mikra-general/stacked/icon-256x256.png",
    "ic_dark_sy": "05 App icons/mikra-dark/symbol/icon-256x256.png", "ic_dark_st": "05 App icons/mikra-dark/stacked/icon-256x256.png",
    "ic_gray_sy": "05 App icons/mikra-gray/symbol/icon-256x256.png", "ic_gray_st": "05 App icons/mikra-gray/stacked/icon-256x256.png",
    "li_banner": "08 Social and office/linkedin-banner-1584x396.png", "og": "08 Social and office/og-image-1200x630.png",
    "avatar": "08 Social and office/avatar-400-sea.png", "fanar": "10 Daemi/bygging-fanar.jpg",
}

# ---------------------------------------------------------------- download blocks
def dl(label, path): return f'<a class="dl" href="{esc(path)}" download>{esc(label)}</a>'
def btns(*pairs): return '<div class="btns">' + "".join(dl(l, p) for l, p in pairs) + "</div>"
def card(title, note, preview, files, dark=False, wide=False):
    return (f'<figure class="asset{" dark" if dark else ""}{" wide" if wide else ""}"><div class="prev"><img src="{esc(preview)}" alt="{esc(title)}" loading="lazy"></div>'
            f'<figcaption><b>{esc(title)}</b><span>{esc(note)}</span>{btns(*files)}</figcaption></figure>')

def colour_card(c):
    tints = "".join(f'<i style="background:{v}" title="{p} % · {v}"></i>' for p, v in c["tints"].items())
    light = c["name"] in ("ice", "white", "mist", "sky")
    cm = "/".join(str(v) for v in c["cmyk"]) + ("" if c["cmyk_source"] == "spec" else " *")
    nice = c["name"].replace("-", " ").title()
    return (f'<div class="colour"><div class="swatch" style="background:{c["hex"]};color:{"#1F2430" if light else "#fff"}"><span>{esc(nice)}</span><em>{esc(c["icelandic"])}</em></div>'
            f'<div class="tints">{tints}</div><dl><dt>HEX</dt><dd><button class="copy" data-copy="{c["hex"]}">{c["hex"]}</button></dd>'
            f'<dt>RGB</dt><dd>{" · ".join(str(v) for v in c["rgb"])}</dd><dt>CMYK</dt><dd>{cm}</dd><dt>Pantone</dt><dd>{esc(c["pantone"] or "—")}</dd></dl><p>{esc(c["use"])}</p></div>')

EXTRA_CSS = """
.btns{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.dl{display:inline-block;font-size:11.5px;font-weight:600;color:var(--sea);border:1.5px solid var(--sea);border-radius:999px;padding:4px 11px;text-decoration:none;background:#fff}
.dl:hover{background:var(--sea);color:#fff}
.dlrow{margin:14px 0 4px}
.assets{display:grid;grid-template-columns:repeat(auto-fill,minmax(222px,1fr));gap:14px;margin-top:12px}
.asset{margin:0;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#fff;display:flex;flex-direction:column;min-width:0}
.asset.wide{grid-column:span 2}
.asset .prev{background:#fff;display:flex;align-items:center;justify-content:center;padding:22px;min-height:140px}
.asset.dark .prev{background:var(--deep)}
.asset .prev img{max-width:100%;max-height:130px;height:auto}
.asset.wide .prev{padding:0;min-height:0}.asset.wide .prev img{max-height:none;width:100%;display:block}
figcaption{padding:10px 12px 12px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}
figcaption b{display:block;color:var(--fg);font-size:13px;font-weight:600}figcaption span{display:block;margin:2px 0 6px}
.colours{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.colour{border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#fff;font-size:12.5px}
.colour .swatch{height:130px;padding:14px;display:flex;flex-direction:column;justify-content:flex-end}
.colour .swatch span{font-weight:600;font-size:16px}.colour .swatch em{font-style:normal;opacity:.75;font-size:11px}
.colour .tints{display:flex;height:30px}.colour .tints i{flex:1}
.colour dl{display:grid;grid-template-columns:62px 1fr;gap:3px 8px;margin:12px 14px 6px;font-variant-numeric:tabular-nums}
.colour dt{color:var(--rock);font-size:11px;text-transform:uppercase;letter-spacing:.06em}.colour dd{margin:0;color:var(--fg)}
.colour p{margin:4px 14px 14px;color:var(--muted);font-size:12px}
.copy{font:inherit;font-weight:600;color:var(--sea);background:none;border:0;padding:0;cursor:pointer}.copy:after{content:" ⧉";font-weight:400;color:var(--rock)}
.copy.done:after{content:" afritað";color:var(--kelp)}
nav .all{display:block;margin-top:22px;background:var(--sea);color:#fff;text-decoration:none;font-weight:600;font-size:13px;padding:10px 14px;border-radius:999px;text-align:center}
.hero-cta{display:inline-block;background:#fff;color:var(--deep);font-weight:600;padding:12px 20px;border-radius:999px;text-decoration:none;margin:22px 10px 0 0;font-size:14px}
.hero-cta.g{background:transparent;color:#fff;border:1.5px solid #fff}
.ref{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}.ref figure{margin:0;min-width:0}.ref img{width:100%;height:auto;border-radius:6px;border:1px solid var(--line);display:block}.ref figcaption{font-size:12px;color:var(--muted);margin-top:6px;padding:0;border:0}
"""

def build_site(palette_rows, stamp):
    t = SRC.read_text(encoding="utf-8")
    t = re.sub(r"\{\{(\w+)\}\}", lambda m: TOKENS[m.group(1)] if TOKENS[m.group(1)].startswith("<") else TOKENS[m.group(1)], t)

    # ---- head: full document, favicon, extra css
    t = t.replace('<title>Mikra Brand Guide</title>\n<meta name="claude:viewport-fit-sides" content="cover">',
                  '<!doctype html>\n<html lang="is"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>Mikra · Vörumerki</title>\n<link rel="icon" href="05 App icons/mikra-general/symbol/favicon.ico">', 1)
    t = t.replace("</style>", EXTRA_CSS + "</style></head><body>", 1)
    t = t.replace("Útgáfa 1.0 · drög til samþykktar · 06.11.2026", f"Útgáfa 1.0 · byggt {stamp}")

    # ---- nav: download CTA
    t = t.replace('  <span class="ver">', '  <a class="all" href="Downloads/mikra-brand-allt.zip" download>Sækja allan pakkann</a>\n  <span class="ver">', 1)

    # ---- hero: downloads + wording
    t = t.replace('<h1>Mikra Brand Guide</h1>', '<h1>Vörumerki Mikra</h1>')
    t = t.replace('Skrárnar sjálfar eru í brandpakkanum, sjá kafla 09 og vefsíðuna <code>index.html</code> með niðurhali.',
                  'Reglurnar og skrárnar eru hér á sömu síðu: hver kafli endar á niðurhali. Sæktu allt héðan, ekki úr tölvupósti eða gömlum skjölum.')
    t = t.replace('    <div style="margin-top:34px;width:min(100%,520px)"><img src="01 Logo/mikra-logo-white.svg" alt="" class="lg" style="" loading="lazy"></div>',
                  '    <div style="margin-top:34px;width:min(100%,520px)"><img src="01 Logo/mikra-logo-white.svg" alt="Mikra" style="width:100%;height:auto"></div>'
                  '<div><a class="hero-cta" href="Downloads/mikra-merki.zip" download>Sækja merkin (zip)</a><a class="hero-cta g" href="#logo">Reglurnar</a></div>')

    # ---- logo section: downloads after main tiles, stacked, lockups; symbol/circle/watermark/waves subsection
    t = t.replace('  <div class="note" style="margin-top:14px"><b>Reglan í einni línu:</b>',
                  '  <div class="dlrow">' + btns(("Merki Sea · SVG", "01 Logo/mikra-logo-sea.svg"), ("PNG 2000", "01 Logo/mikra-logo-sea-2000.png"), ("PNG 600", "01 Logo/mikra-logo-sea-600.png"),
                                                 ("Merki hvítt · SVG", "01 Logo/mikra-logo-white.svg"), ("PNG 2000", "01 Logo/mikra-logo-white-2000.png"), ("PNG 600", "01 Logo/mikra-logo-white-600.png")) + '</div>\n  <div class="note" style="margin-top:14px"><b>Reglan í einni línu:</b>', 1)
    waves = ""
    for tag, lab, note in [("1920x500", "Skjábreidd 1920×500", "Bylgjurnar þrjár haldið áfram yfir heilan skjá, sama kúrfa og í merkinu. Fótur, haus, borði, bíll."),
                           ("1920x820", "Skjábreidd 1920×820, stærri", "Stærri bylgja: hero, básveggur, stórir fletir."),
                           ("3840x1000", "4K 3840×1000", "Stórprent og 4K-skjáir.")]:
        for colour, lab2, dark in (("white", "hvítt", True), ("sea", "Sea", False)):
            waves += card(f"{lab} · {lab2}", note, f"03 Symbol/Waves/mikra-waves-{colour}-{tag}.png",
                          [("SVG", f"03 Symbol/Waves/mikra-waves-{colour}-{tag}.svg"), ("PNG", f"03 Symbol/Waves/mikra-waves-{colour}-{tag}.png")], dark=dark, wide=True)
    symbols = "".join(card(f"Tákn · {'Sea' if c=='sea' else 'hvítt'}", "Ikon, fatnaður, þar sem nafnið er þegar þekkt.", f"03 Symbol/mikra-symbol-{c}-256.png",
                           [("SVG", f"03 Symbol/mikra-symbol-{c}.svg"), ("PNG 1000", f"03 Symbol/mikra-symbol-{c}-1000.png"), ("PNG 256", f"03 Symbol/mikra-symbol-{c}-256.png")], dark=(c == "white")) for c in ("sea", "white"))
    circles = "".join(card(f"Hringur · {lab}", note, f"03 Symbol/Circle/mikra-symbol-circle-{k}-256.png",
                           [("SVG", f"03 Symbol/Circle/mikra-symbol-circle-{k}.svg"), ("PNG 1000", f"03 Symbol/Circle/mikra-symbol-circle-{k}-1000.png")], dark=k.startswith("white"))
                      for k, lab, note in [("sea-white", "Sea / hvítt", "Sjálfgefinn avatar."), ("white-sea", "hvítt / Sea", "Á lituðum grunni."), ("deep-sea-white", "Deep Sea / hvítt", "Rólegri avatar."),
                                           ("rock-dark-ice", "Rock Dark / Ice", "OMS app-ikon."), ("rock-white", "Rock / hvítt", "Sandbox, prófun.")])
    wms = "".join(card(f"Vatnsmerki · {lab}", note, f"03 Symbol/Watermark/mikra-watermark-{k}-3840.png",
                       [("SVG", f"03 Symbol/Watermark/mikra-watermark-{k}.svg"), ("PNG 3840", f"03 Symbol/Watermark/mikra-watermark-{k}-3840.png")], dark=d)
                  for k, lab, note, d in [("white-8", "hvítt 8 %", "Á Deep Sea, Sea, Rock Dark og dökkum myndum.", True), ("sky-35", "Sky 35 %", "Á Ice og hvítu.", False), ("sea-10", "Sea 10 %", "Á hvítu, blær af bláu.", False)])
    stacked = "".join(card(f"Stacked · {'Sea' if c=='sea' else 'hvítt'}", "App-flísar, avatar, básgaflar, stimplar.", f"02 Stacked/mikra-stacked-{c}-400.png",
                           [("SVG", f"02 Stacked/mikra-stacked-{c}.svg"), ("PNG 1200", f"02 Stacked/mikra-stacked-{c}-1200.png"), ("PNG 400", f"02 Stacked/mikra-stacked-{c}-400.png")], dark=(c == "white")) for c in ("sea", "white"))
    t = t.replace('  <h3>Vörulínur</h3>',
                  '  <h4 style="margin-top:18px">Sækja tákn, stacked, hringi og vatnsmerki</h4><div class="assets">' + symbols + stacked + circles + wms + '</div>'
                  '\n  <h3>Bylgjurnar sem grafískt element, tilbúnar</h3>'
                  '\n  <p>Bylgjurnar þrjár úr merkinu haldið áfram yfir heilan skjá eða flöt: sama kúrfa, sama þykkt, sama stöðun og í merkinu, aðeins endurtekin. Gegnsær grunnur, í hvítu og Sea, sama regla og lógóið: hvítt á lituðum grunni, Sea á hvítum, engin þriðja útgáfa. Í prenti er Sea-skráin notuð og prentara sagt Pantone 2728 C. Fyrir fót, haus, borða, bíl, bás og markaðsefni. SVG má teygja í hvaða breidd sem er. Aldrei bak við lógóið og aldrei bak við meginmálstexta.</p>'
                  '\n  <div class="assets">' + waves + '</div>'
                  '\n  <h3>Vörulínur</h3>', 1)
    lock = "".join(card(lab, "Sea á hvítu · hvítt á lituðu", f"04 Product lockups/mikra-{p}-sea-600.png",
                        [("SVG Sea", f"04 Product lockups/mikra-{p}-sea.svg"), ("SVG hvítt", f"04 Product lockups/mikra-{p}-white.svg"), ("PNG 2000", f"04 Product lockups/mikra-{p}-sea-2000.png")])
                   for p, lab in (("mes", "Mikra MES"), ("cordex", "Mikra CorDex"), ("robotics", "Mikra Robotics"), ("vision", "Mikra Vision")))
    t = t.replace('  <div class="cols" style="margin-top:30px">\n    <div>\n      <h4>Friðhelgað svæði og lágmarksstærð</h4>',
                  '  <div class="assets">' + lock + '</div>\n  <div class="cols" style="margin-top:30px">\n    <div>\n      <h4>Friðhelgað svæði og lágmarksstærð</h4>', 1)

    # ---- letur: font link
    t = t.replace('<p>Vefur: <code>fonts.googleapis.com/css2?family=Plus+Jakarta+Sans</code><br>',
                  '<div class="btns" style="margin-bottom:10px"><a class="dl" href="https://fonts.google.com/specimen/Plus+Jakarta+Sans" target="_blank" rel="noopener">Sækja Plus Jakarta Sans (Google Fonts)</a></div><p>Vefur: <code>fonts.googleapis.com/css2?family=Plus+Jakarta+Sans</code><br>', 1)

    # ---- litir: swap swatch grids for colour cards with tints
    groups = {"blues": "Bláa fjölskyldan", "signal": "Merkingarlitir", "neutral": "Hlutlausir"}
    cards = "".join(f'<h3>{gl}</h3><div class="colours">' + "".join(colour_card(c) for c in palette_rows if c["group"] == g and c["name"] != "white") + "</div>" for g, gl in groups.items())
    a = t.index("<h3>Bláa fjölskyldan</h3>"); b = t.index("<h3>Hlutföll</h3>")
    t = t[:a] + cards + '<p style="font-size:12px;color:var(--rock);margin-top:10px">* CMYK reiknað úr RGB, ekki prófað í prenti. Pantone fyrir Deep Sea, Kelp og Salmon Deep óstaðfest. Prentari fær alltaf Pantone 2728 C fyrir bláa, aldrei hex. Smelltu á hex-gildið til að afrita.</p>' + \
        '<div class="dlrow">' + btns(("palette.css", "06 Colours/palette.css"), ("palette.scss", "06 Colours/palette.scss"), ("palette.json", "06 Colours/palette.json"), ("palette.ase (Adobe)", "06 Colours/palette.ase"), ("palette.gpl (Inkscape, GIMP)", "06 Colours/palette.gpl"), ("Litaspjöld með tintum (zip)", "Downloads/mikra-litir.zip")) + "</div>\n  " + t[b:]

    # ---- bakgrunnar: replace figures with cards
    a = t.index('<section id="bakgrunnar">'); b = t.index('<section id="appikon">')
    sec = t[a:b]
    bg = "".join(card(lab, note, f"07 Backgrounds/{k}-1920x1080.png", [("SVG", f"07 Backgrounds/{k}-1920x1080.svg"), ("PNG 1920", f"07 Backgrounds/{k}-1920x1080.png"), ("PNG 3840", f"07 Backgrounds/{k}-3840x2160.png")], wide=True)
                 for k, lab, note in [("deep-sea-watermark", "Deep Sea með vatnsmerki", "Titilglæra (dökk), kaflaskil, hero, lokamynd."),
                                      ("ice-watermark", "Ice með vatnsmerki", "Titilglæra (ljós), skjalaforsíður, hliðarveggir."), ("rock-dark-watermark", "Rock Dark með vatnsmerki", "Splash-skjáir, HMI-biðskjár.")])
    sec = re.sub(r'<div class="ref"[^>]*>.*?</div>\n', '<div class="assets">' + bg + '</div>\n<div class="dlrow">' + btns(("Allir bakgrunnar, þ.m.t. heillitir (zip)", "Downloads/mikra-bakgrunnar.zip")) + '</div>\n', sec, count=1, flags=re.S)
    t = t[:a] + sec + t[b:]

    # ---- appikon: downloads
    icons = "".join('<div class="btns" style="margin-top:4px">' + "".join(dl(l, p) for l, p in [(f"{s} favicon.ico", f"05 App icons/{s}/symbol/favicon.ico"), ("tákn 512", f"05 App icons/{s}/symbol/icon-512x512.png"), ("My Apps 215", f"05 App icons/{s}/stacked/myapps-215x215.png"), ("tile.svg", f"05 App icons/{s}/stacked/tile.svg")]) + "</div>"
                    for s in ("mikra-general", "mikra-dark", "mikra-gray"))
    t = t.replace('  <div class="cols" style="margin-top:20px">\n    <div><h4>Úthlutun kerfa</h4>', '  <div class="dlrow">' + icons + btns(("Öll app-ikon (zip)", "Downloads/mikra-app-ikon.zip")) + '</div>\n  <div class="cols" style="margin-top:20px">\n    <div><h4>Úthlutun kerfa</h4>', 1)

    # ---- notkun: ready files block -> cards with downloads; signature card
    a = t.index('<h3 style="margin-top:44px">Tilbúnar skrár: samfélagsmiðlar og skrifstofa</h3>'); b = t.index('</div></section>', a)
    social = (card("LinkedIn-borði 1584×396", "Lógó hægra megin, vinstri þriðjungur auður fyrir prófílmynd.", "08 Social and office/linkedin-banner-1584x396.png", [("PNG", "08 Social and office/linkedin-banner-1584x396.png"), ("SVG", "08 Social and office/linkedin-banner-1584x396.svg")], wide=True)
              + card("Link preview 1200×630", "Open Graph fyrir mikra.is, Teams og LinkedIn-tenglakort.", "08 Social and office/og-image-1200x630.png", [("PNG", "08 Social and office/og-image-1200x630.png"), ("SVG", "08 Social and office/og-image-1200x630.svg")], wide=True)
              + card("Avatar 400×400", "LinkedIn, Facebook, Teams, GitHub.", "08 Social and office/avatar-400-sea.png", [("Sea", "08 Social and office/avatar-400-sea.png"), ("Deep Sea", "08 Social and office/avatar-400-deep-sea.png"), ("Ferningur", "08 Social and office/avatar-400-sea-square.png")])
              + card("Tölvupóstundirskrift, CodeTwo", "HTML-sniðmát með {Display name} {Title} {Mobile} {E-mail} og myndirnar sem það notar.", "08 Social and office/email-signature/signature-preview.png", [("HTML", "08 Social and office/email-signature/codetwo-signature.html"), ("Lógó 440×108", "08 Social and office/email-signature/mikra-logo-email-440x108.png")], wide=True)
              + card("Word-haus 1200 px", "Sett 35–45 mm breitt í haus. Sea á hvítum haus, hvítt á Deep Sea-haus.", "08 Social and office/word-header-logo-sea-1200.png", [("Sea", "08 Social and office/word-header-logo-sea-1200.png"), ("Hvítt", "08 Social and office/word-header-logo-white-1200.png")])
              + card("PowerPoint-sniðmát", "Þrjár titilglærur (C, I, D), kaflaskil, efnisglærur. Líka undir Nýtt → Mikra í PowerPoint.", "08 Social and office/pptx-template-preview.png", [("Mikra_snidmat.potx", "08 Social and office/Mikra_snidmat.potx"), ("Uppsetning fyrir IT", "08 Social and office/PowerPoint-uppsetning.md")], wide=True))
    t = t[:a] + '<h3 style="margin-top:44px">Tilbúnar skrár: samfélagsmiðlar og skrifstofa</h3>\n  <p>Tilbúið til að hlaða upp eða líma inn. Ekki búa til eigin útgáfur.</p>\n  <div class="assets">' + social + '</div>\n<div class="dlrow">' + btns(("Allt í 08 (zip)", "Downloads/mikra-social-office.zip")) + '</div>\n' + t[b:]

    # ---- skrár: zips
    t = t.replace('  <div class="cols" style="margin-top:20px">\n    <div><h4>Reglur um pakkann</h4>',
                  '  <div class="dlrow">' + btns(("Allt (zip)", "Downloads/mikra-brand-allt.zip"), ("Merki, stacked, tákn", "Downloads/mikra-merki.zip"), ("Vörulínur", "Downloads/mikra-vorulinur.zip"), ("App-ikon", "Downloads/mikra-app-ikon.zip"), ("Litir", "Downloads/mikra-litir.zip"), ("Bakgrunnar", "Downloads/mikra-bakgrunnar.zip"), ("Social og skrifstofa", "Downloads/mikra-social-office.zip"), ("Frumskrár SVG/PDF/DXF/AI", "Downloads/mikra-frumskrar.zip")) + '</div>\n  <div class="cols" style="margin-top:20px">\n    <div><h4>Reglur um pakkann</h4>', 1)
    t = t.replace('<tr><td>index.html</td><td>Brand-portal með niðurhali</td><td>Forskoðun og niðurhalshnappar á hverri skrá, zip per kafla.</td></tr>',
                  '<tr><td>index.html</td><td>Þessi síða: reglur og niðurhal</td><td>Eina skjalið. Mikra_Brand_Guide_standalone.html er sama síða með innbyggðum myndum, til að senda út fyrir hús.</td></tr>\n    <tr><td>10 Daemi</td><td>Ljósmyndir og tillögur sem þessi síða sýnir</td><td>Dæmi, ekki merkjaskrár.</td></tr>')

    # ---- close document + copy script
    t = t.replace('</main>\n</div>', '</main>\n</div>\n<script>document.querySelectorAll(".copy").forEach(b=>b.addEventListener("click",async()=>{try{await navigator.clipboard.writeText(b.dataset.copy);b.classList.add("done");setTimeout(()=>b.classList.remove("done"),1500)}catch(e){}}));</script>\n</body></html>')
    (ROOT / "index.html").write_text(t, encoding="utf-8")

    # ---- standalone: embed every local image, drop download buttons
    def embed(m):
        p = ROOT / html.unescape(m.group(2))
        if not p.exists() or p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".svg"): return m.group(0)
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return f'{m.group(1)}="data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"'
    s = re.sub(r'(src)="([^"]+)"', embed, t)
    s = re.sub(r'<a class="dl"[^>]*download>[^<]*</a>', '', s)
    s = re.sub(r'<a class="all"[^>]*>[^<]*</a>', '', s)
    s = re.sub(r'<a class="hero-cta"[^>]*download>[^<]*</a>', '', s)
    s = s.replace('<link rel="icon" href="05 App icons/mikra-general/symbol/favicon.ico">', '')
    s = s.replace('Reglurnar og skrárnar eru hér á sömu síðu: hver kafli endar á niðurhali. Sæktu allt héðan, ekki úr tölvupósti eða gömlum skjölum.',
                  'Þetta er lesútgáfa. Skrárnar sjálfar eru í pakkanum <code>Marketing/Mikra/Branding/Mikra_Brand_2026</code>, opnið <code>index.html</code> þar til að sækja þær.')
    (ROOT / "Mikra_Brand_Guide_standalone.html").write_text(s, encoding="utf-8")

    build_text(palette_rows, stamp)
    build_public(t, palette_rows, stamp)
    build_vinnuskjal(stamp)


# ---------------------------------------------------------------- internal working document
def build_vinnuskjal(stamp):
    """Vinnuskjal.html: options awaiting decision, supplier proposals, web spec, open items. Internal only."""
    v = (ROOT / "09 Source" / "site" / "vinnuskjal_src.html").read_text(encoding="utf-8")
    v = re.sub(r"\{\{(\w+)\}\}", lambda m: TOKENS[m.group(1)], v)
    v = v.replace('<title>Mikra · Vinnuskjal</title>\n<meta name="claude:viewport-fit-sides" content="cover">',
                  '<!doctype html>\n<html lang="is"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>Mikra · Vinnuskjal</title>', 1)
    v = v.replace("</style>", EXTRA_CSS + "\nbody>main{display:block;width:min(1100px,100% - 48px);margin:0 auto;padding:40px 0}body>main .inner{max-width:none}body>main #vinnuskjal>.inner>.cols{display:block}body>main h2{font-size:34px}\n</style></head><body>", 1)
    v = v.replace("<h2>Vinnuskjal vörumerkis</h2>", f"<h2>Vinnuskjal vörumerkis</h2><p style=\"color:var(--rock);font-size:12px\">Innanhúss · byggt {stamp} · <a href=\"index.html\">til baka í guide</a></p>")
    (ROOT / "Vinnuskjal.html").write_text(v + "\n</body></html>", encoding="utf-8")



# ---------------------------------------------------------------- public site (brand.mikra.is)
# Same page, minus everything that is internal: supplier proposals, undecided options, office/e-mail
# templates and the open-items list. Written to public/ with only the files it links to, so the
# folder can be published as is (GitHub Pages, Cloudflare Pages).
PUBLIC_DROP_SAMPLES = ["Sýningarbás", "Þjónustubíll"]   # supplier renders stay internal
PUBLIC_DIRS = ["01 Logo", "02 Stacked", "03 Symbol", "04 Product lockups", "05 App icons", "06 Colours", "07 Backgrounds"]
PUBLIC_SOCIAL = ["linkedin-banner-1584x396.png", "linkedin-banner-1584x396.svg", "og-image-1200x630.png", "og-image-1200x630.svg",
                 "avatar-400-sea.png", "avatar-400-deep-sea.png", "avatar-400-sea-square.png"]

def _drop_sample(t, label):
    a = t.find(f'<div class="sample"><div class="lab"><b>{label}</b>')
    if a < 0: return t
    nxt = t.find('\n    <div class="sample">', a + 10); end = t.find('\n  </div>', a)
    b = min(x for x in (nxt, end) if x > 0)
    return t[:a] + t[b:].lstrip("\n")

def _drop_block(t, start, end_marker):
    a = t.find(start)
    if a < 0: return t
    b = t.find(end_marker, a + len(start))
    if b < 0: raise ValueError(f"public build: end marker not found after {start[:40]!r}")
    return t[:a] + t[b:]

def build_public(t, palette_rows, stamp):
    pub = ROOT / "public"
    if pub.exists(): shutil.rmtree(pub)
    pub.mkdir()
    p = t
    for lab in PUBLIC_DROP_SAMPLES: p = _drop_sample(p, lab)
    p = _drop_block(p, '<h3 style="margin-top:44px">Tilbúnar skrár: samfélagsmiðlar og skrifstofa</h3>', '</div></section>')   # office/e-mail files are internal
    # skrár: public download list only, no package table, no open items
    a = p.index('<section id="skrar"'); b = p.index('</main>')
    p = p[:a] + ('<section id="skrar" style="border-bottom:0"><div class="inner">\n  <div class="eyebrow">09</div><h2>Sækja</h2>\n'
                 '  <p class="lead">Allar skrár á þessari síðu í zip-pökkum. Þetta er opinbera útgáfan af vörumerki Mikra, uppfærð úr einni uppsprettu.</p>\n'
                 '  <div class="dlrow">' + btns(("Allt (zip)", "Downloads/mikra-brand-allt.zip"), ("Merki, stacked, tákn", "Downloads/mikra-merki.zip"), ("Vörulínur", "Downloads/mikra-vorulinur.zip"),
                                                ("App-ikon", "Downloads/mikra-app-ikon.zip"), ("Litir", "Downloads/mikra-litir.zip"), ("Bakgrunnar", "Downloads/mikra-bakgrunnar.zip")) + '</div>\n'
                 '  <p style="font-size:12px;color:var(--rock);margin-top:18px">Vélalesanleg útgáfa fyrir gervigreind og forritara: <a href="brand.md">brand.md</a> · <a href="llms.txt">llms.txt</a> · <a href="06 Colours/palette.json">palette.json</a> · <a href="06 Colours/palette.css">palette.css</a></p>\n'
                 '</div></section>\n') + p[b:]
    p = p.replace('Reglurnar og skrárnar eru hér á sömu síðu: hver kafli endar á niðurhali. Sæktu allt héðan, ekki úr tölvupósti eða gömlum skjölum.',
                  'Reglurnar og skrárnar eru hér á sömu síðu: hver kafli endar á niðurhali. Þetta er eina gilda útgáfan, sæktu allt héðan.')
    p = p.replace('<a href="#skrar">Skrár og pakkinn</a>', '<a href="#skrar">Sækja</a>')
    p = p.replace('<link rel="icon" href="05 App icons/mikra-general/symbol/favicon.ico">',
                  '<link rel="icon" href="05 App icons/mikra-general/symbol/favicon.ico"><meta name="description" content="Vörumerki Mikra: lógó, litir, letur og reglur. Opinber útgáfa.">')
    (pub / "index.html").write_text(p, encoding="utf-8")
    # files the page links to
    for d in PUBLIC_DIRS: shutil.copytree(ROOT / d, pub / d)
    (pub / "08 Social and office").mkdir()
    for f in PUBLIC_SOCIAL: shutil.copy(ROOT / "08 Social and office" / f, pub / "08 Social and office" / f)
    used = set(re.findall(r'(?:src|href)="(10 Daemi/[^"]+)"', p))
    if used:
        for u in used:
            rel = Path(html.unescape(u)); src = ROOT / rel
            if src.exists(): (pub / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src, pub / rel)
    # zips, public content only
    dl_dir = pub / "Downloads"; dl_dir.mkdir()
    def zipdirs(name, dirs):
        with zipfile.ZipFile(dl_dir / name, "w", zipfile.ZIP_DEFLATED) as z:
            for d in dirs:
                for f in sorted((pub / d).rglob("*")):
                    if f.is_file(): z.write(f, f.relative_to(pub))
    zipdirs("mikra-merki.zip", ["01 Logo", "02 Stacked", "03 Symbol"]); zipdirs("mikra-vorulinur.zip", ["04 Product lockups"])
    zipdirs("mikra-app-ikon.zip", ["05 App icons"]); zipdirs("mikra-litir.zip", ["06 Colours"]); zipdirs("mikra-bakgrunnar.zip", ["07 Backgrounds"])
    zipdirs("mikra-brand-allt.zip", PUBLIC_DIRS + ["08 Social and office"])
    for f in ("brand.md", "llms.txt"):
        if (ROOT / f).exists(): shutil.copy(ROOT / f, pub / f)
    (pub / "CNAME").write_text("brand.mikra.is\n")
    (pub / ".nojekyll").write_text("")


# ---------------------------------------------------------------- text version for people and machines
def _text(fragment):
    """HTML fragment -> plain text lines, headings kept as markdown."""
    f = re.sub(r"<(script|style|svg|table|figure)[^>]*>.*?</\1>", "", fragment, flags=re.S)
    f = re.sub(r"<img[^>]*>", "", f)
    f = re.sub(r'<div class="eyebrow">[^<]*</div>', "", f)
    f = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", f, flags=re.S)
    f = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", f, flags=re.S)
    f = re.sub(r"<h4[^>]*>(.*?)</h4>", r"\n#### \1\n", f, flags=re.S)
    f = re.sub(r'<div class="rule"><span class="(ok|no)">[^<]*</span><div>(.*?)</div></div>', lambda m: "\n- " + ("✓ " if m.group(1) == "ok" else "✕ ") + m.group(2) + "\n", f, flags=re.S)
    f = re.sub(r"<(p|li|dt|dd|div class=\"note\")[^>]*>", "\n", f)
    f = re.sub(r"<[^>]+>", "", f)
    f = html.unescape(f)
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in f.splitlines()]
    out = []
    for l in lines:
        if l or (out and out[-1]): out.append(l)
    return "\n".join(out).strip()

def build_text(palette_rows, stamp):
    src = SRC.read_text(encoding="utf-8")
    src = re.sub(r"\{\{\w+\}\}", "", src)
    body = src[src.index('<section id="profill">'):src.index('<section id="notkun">')]
    sections = re.findall(r'<section id="(\w+)"[^>]*>(.*?)</section>', body, flags=re.S)
    md = [f"# Vörumerki Mikra, reglur\n\nOpinber útgáfa {stamp}. Vefur: https://brand.mikra.is · skrár: sama slóð. Þetta skjal er fyrir fólk og gervigreind sem á að fara eftir reglum Mikra; það er búið til úr sömu uppsprettu og vefsíðan.\n",
          "## Reglurnar í stuttu máli\n",
          "- Lógó: hvítt á lituðum grunni, Sea #0037FF á hvítum eða Ice grunni. Engin þriðja útgáfa (ekki svart, ekki grátt, ekki Deep Sea).",
          "- Sea #0037FF er merkið, hnappar, línur og ikon. Ekki yfirborðslitur.",
          "- Deep Sea #0A1F5C er yfirborðsliturinn: titilglærur, hero, gaflar, borðar, kaflaskil. Á Deep Sea er allt annað hvítt.",
          "- Bylgjurnar (þrjár úr tákninu) fylgja lógóreglunni: hvítar á lituðu, Sea á hvítu.",
          "- Prent: blái liturinn er Pantone 2728 C (Sea Print #0047BB er skjágildi þess). Prentari fær Pantone, ekki hex.",
          "- Letur: Plus Jakarta Sans í öllu efni. Ubuntu aðeins í lógóinu.",
          "- Enginn gradient. Kelp = í lagi, Salmon Deep = athygli; aldrei skreyting.",
          "- Hvítur texti aðeins á Sea, Sea Print, Deep Sea, Rock Dark, Kelp og Salmon Deep.\n",
          "## Litir\n", "| Nafn | HEX | RGB | CMYK | Pantone | Notkun |", "|---|---|---|---|---|---|"]
    for c in palette_rows:
        if c["name"] == "white": continue
        md.append(f"| {c['name'].replace('-', ' ').title()} | {c['hex']} | {' '.join(str(v) for v in c['rgb'])} | {'/'.join(str(v) for v in c['cmyk'])}{'' if c['cmyk_source']=='spec' else ' (reiknað)'} | {c['pantone'] or '–'} | {c['use']} |")
    md.append("\nTintar 80/60/40/20 % af hverjum lit eru í palette.css / palette.json (--mikra-<nafn>-<prósenta>).\n")
    for sid, frag in sections:
        md.append(_text(frag) + "\n")
    md.append("## Skrár\n\nLógó (SVG/PNG), stacked, tákn, bylgjur, vörulínur, app-ikon, litaspjöld og bakgrunnar: https://brand.mikra.is (Downloads/mikra-brand-allt.zip).\n")
    text = "\n".join(md)
    (ROOT / "brand.md").write_text(text, encoding="utf-8")
    (ROOT / "llms.txt").write_text(
        "# Mikra brand\n\n> Opinberar vörumerkjareglur Mikra ehf.: lógó, litir, letur, bylgjur, bakgrunnar. Fylgja þeim í öllu efni fyrir Mikra.\n\n"
        "- [Reglurnar, allt skjalið](https://brand.mikra.is/brand.md): lógóreglan, litir með HEX/RGB/CMYK/Pantone, letur, bakgrunnar.\n"
        "- [palette.json](https://brand.mikra.is/06%20Colours/palette.json): litir og tintar, vélalesanlegt.\n"
        "- [palette.css](https://brand.mikra.is/06%20Colours/palette.css): CSS-breytur --mikra-*.\n"
        "- [Vefsíðan](https://brand.mikra.is/): sama efni með myndum og niðurhali.\n\n"
        "## Kjarnareglur\n\n- Lógó: hvítt á lituðum grunni, Sea #0037FF á hvítum. Ekkert annað.\n- Sea er merki og hnappar, ekki yfirborð. Deep Sea #0A1F5C er yfirborðsliturinn.\n- Plus Jakarta Sans í öllu, Ubuntu aðeins í lógóinu.\n- Enginn gradient. Prentblár Pantone 2728 C.\n", encoding="utf-8")
