# Mikra brandpakki 2026

Opnaðu `index.html` í vafra. Það er eina skjalið: reglurnar og niðurhal á hverri skrá, kafli fyrir kafla.
`Mikra_Brand_Guide_standalone.html` er sama síða með innbyggðum myndum, til að senda út fyrir hús (engir niðurhalshnappar).
`Vinnuskjal.html` er innanhúss: valkostir til ákvörðunar, tillögur birgja, vefforskrift og opin atriði. Guide-inn er reglurnar og eitt dæmi um hvert; það sem er ekki ákveðið fer í vinnuskjalið.

| Mappa | Innihald |
|---|---|
| `01 Logo` | Aðalmerki í sea og white · SVG + PNG 2000/600. Friðhelgað svæði innbyggt. Engar aðrar litútgáfur. |
| `02 Stacked` | Tákn yfir orðmerki, sea og white · SVG + PNG 1200/400. |
| `03 Symbol` | Bylgjutáknið, sea og white · SVG + PNG 1000/256, auk `Circle/`, `Watermark/` (gegnsætt vatnsmerki) og `Waves/` (bylgjurnar þrjár haldið áfram yfir skjábreidd, hvítt og Sea, sama regla og lógóið). |
| `04 Product lockups` | Mikra MES, CorDex, Robotics, Vision í sea og white. |
| `05 App icons` | mikra-general (blár), mikra-dark (dökkgrár, OMS), mikra-gray (grár, sandbox) · symbol/ og stacked/ með favicon.ico, PNG 16–512, My Apps 215, TwinCAT launcher. |
| `06 Colours` | palette.css / .scss / .json / .ase / .gpl og litaspjald per lit með 80/60/40/20 % tintum. |
| `07 Backgrounds` | Þrjú vatnsmerki (Deep Sea, Ice, Rock Dark) og heillitir · SVG + PNG 1920×1080 og 3840×2160. Enginn gradient. |
| `08 Social and office` | Avatar, LinkedIn-borði, link preview, CodeTwo-undirskrift, Word-haus, PowerPoint-sniðmát (.potx) og bakgrunnar. |
| `09 Source` | Frumskrár hönnuðar (SVG, PDF, DXF, AI), texti síðunnar (`site/guide_src.html`), undirskrift, Office-sniðmát. |
| `10 Daemi` | Ljósmyndir og tillögur sem síðan sýnir sem dæmi. Ekki merkjaskrár. |
| `Downloads` | Zip-pakkar sem hnapparnir á index.html vísa í. |

## Endurbyggja

    python -m pip install pillow resvg-py
    python build.py

Allt í 01–08, Downloads og index.html er búið til úr `09 Source` og `PALETTE` í `build.py`.
Nýr litur, ný stærð eða nýtt kerfi: breyta í `build.py`. Texti og reglur: `09 Source/site/guide_src.html`. Niðurhalsblokkir: `brandsite.py`. Keyra aftur. Aldrei handvirkt.

## Reglur í einni línu

Litaður grunnur → hvítt merki. Hvítur grunnur → Sea #0037FF. Ekkert annað. Prent → Pantone 2728 C. Gröftur → DXF.
Plus Jakarta Sans í öllu, Ubuntu aðeins í merkinu. Sea er merkið og hnappar, ekki yfirborð. Deep Sea er blái flöturinn, á honum er allt hvítt.

## Git og brand.mikra.is

Uppsprettan er git. Í repo-inu er bæði uppsprettan (`build.py`, `brandsite.py`, `09 Source`, `10 Daemi`) og það sem byggist úr henni (01–08, Downloads, `index.html`, `brand.md`), svo klón er heill pakki án þess að keyra neitt.
Reglan: aldrei breyta byggðu skránum beint. Breyta í `09 Source` eða `build.py`, keyra `python build.py`, committa hvort tveggja. `public/` og `Vinnuskjal.html` (innanhúss) eru ekki í git.

`build.py` skrifar þrjár birtingar úr sömu uppsprettu:

| Birting | Fyrir hverja | Innihald |
|---|---|---|
| `index.html` | innanhúss | allt: reglur, niðurhal, tillögur birgja, Office-sniðmát, opin atriði |
| `public/` | brand.mikra.is, allir | reglur og skrár, ekkert innanhúss. GitHub Actions byggir og birtir við hvert push á `main` |
| `brand.md` + `llms.txt` | gervigreind og forritarar | reglurnar sem texti, litir sem tafla. Vísa í `https://brand.mikra.is/brand.md` í kerfisfyrirmælum |

Uppsetning einu sinni: repo á GitHub → Settings → Pages → Source: GitHub Actions. IT setur CNAME `brand.mikra.is` á `<org>.github.io` (CNAME-skráin í public/ er þegar til).
Sameignarmappan er eftir það aðeins afrit til niðurhals, ekki vinnusvæði.
