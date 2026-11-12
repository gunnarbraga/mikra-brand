# Mikra PowerPoint-sniðmát – uppsetning fyrir alla

Skrá: `Mikra_snidmat.potx` (sama efni og `Mikra_snidmat.pptx`, en sem sniðmát).
Glærusnið: Titill dökk C · Titill dökk vatnsmerki I · Titill ljós D · Kaflaskil · Efni · Efni ljósgrá.
Þemalitir: Sea, Deep Sea, Kelp, Salmon Deep, Sky, Rock. Letur: Plus Jakarta Sans (fellur í Segoe UI þar sem það vantar).

## Leið 1 – fyrir alla í fyrirtækinu (mælt með): Organization Assets Library

Sniðmátið birtist þá undir **Nýtt → Mikra** í PowerPoint hjá öllum, á öllum tölvum, og uppfærist miðlægt.

IT (Magnús) gerir þetta einu sinni:

1. Búa til skjalasafn á SharePoint, t.d. `https://<tenant>.sharepoint.com/sites/Brand/OfficeTemplates`, og setja `Mikra_snidmat.potx` þar.
2. Keyra í SharePoint Online PowerShell (sem SharePoint admin):

       Connect-SPOService -Url https://<tenant>-admin.sharepoint.com
       Add-SPOOrgAssetsLibrary -LibraryUrl "https://<tenant>.sharepoint.com/sites/Brand/OfficeTemplates" -OrgAssetType OfficeTemplateLibrary -ThumbnailUrl "https://<tenant>.sharepoint.com/sites/Brand/OfficeTemplates/thumb.png"

3. Bíða allt að 24 klst. Þá sést flipinn **Mikra** í PowerPoint → File → New.
4. Uppfærsla síðar: skipta skránni út í safninu. Allir fá nýju útgáfuna.

Sama safn tekur líka Word- og Excel-sniðmát þegar þau eru tilbúin.

## Leið 2 – fljótleg, án admin: Custom Office Templates

Hver og einn vistar skrána í `%USERPROFILE%\Documents\Custom Office Templates\`.
Birtist undir **Nýtt → Persónulegt**. Ókostur: engin miðlæg uppfærsla, hver er með sína útgáfu.

## Leið 3 – Intune: ýta skránni út á allar tölvur

IT dreifir `Mikra_snidmat.potx` með Intune (Win32-app eða PowerShell-skriftu) í
`C:\Program Files\Microsoft Office\root\Templates\1033\` eða í Custom Office Templates hvers notanda.
Virkar, en Leið 1 er einfaldari í rekstri.

## Letrið

Plus Jakarta Sans þarf að vera uppsett á tölvunum svo sniðmátið líti rétt út. IT dreifir letrinu
(TTF frá fonts.google.com/specimen/Plus+Jakarta+Sans, SIL OFL) með Intune á sama tíma. Án þess fellur
PowerPoint í Segoe UI, sem er í lagi en ekki brandið.

## Reglur fyrir notendur

- Nota sniðin úr „New Slide“, ekki afrita gamlar glærur úr öðrum kynningum.
- Þrjár titilglærur: dökk (C eða I) fyrir kynningar út á við, ljós (D) fyrir skjöl og innanhúss.
- Ekki breyta þemalitum eða letri. Ekki setja Sea-lógó á dökka glæru – lógóið á dökku er hvítt og er þegar í sniðinu.
