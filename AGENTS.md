# Dashboard zakázek nábytku na míru — příspěvky kolegů

Tenhle repo je **veřejný web** https://make-more-s-r-o.github.io/nabytek-dashboard/ (GitHub Pages z větve `main`,
kořen repa). Přehled firemních zakázek nábytku na míru: karty s renderem, detail, verze, 3D model, poznámky.
Kolegové s právem zápisu sem přidávají **vlastní zakázky**; stránka je načte sama a ukáže je vedle firemních
se štítkem „příspěvek: <autor>“.

`CLAUDE.md` a `AGENTS.md` mají stejný obsah. Při změně pravidel uprav oba.

## Tvrdá pravidla

1. **`index.html` a `.nojekyll` NEUPRAVUJ.** Stránku generuje a přepisuje publikace ze soukromého repa
   (`crm/src/publish_pages.sh`); tvoje změna by se při příští publikaci ztratila. Když na stránce něco chybí, napiš Danovi.
2. **Měň jen svou složku `zakazky/<id>/` a svůj řádek v `zakazky/index.json`.** Cizí zakázky, `tools/`
   a tyhle návody neměň bez domluvy s Danem.
3. **Repo je VEŘEJNÉ a git si pamatuje všechno navždy.** Smazání v dalším commitu nestačí, údaj zůstane v historii.
   Do repa proto nikdy nepatří:
   - jména, adresy, telefony a e-maily klientů. Klienta uváděj obecně: „rodina, Praha“, „kancelář, Brno“,
   - fotky skutečných interiérů klientů bez jejich souhlasu. Používej rendery z Blenderu,
   - interní nákupní ceny, ceny po slevě a slevy dodavatelů. Ceny uváděj jen ceníkové nebo nabídnuté klientovi,
   - tajné klíče, tokeny, hesla, soubory `.env`,
   - soubory `.blend`, HTML, SVG a skripty. Povolené typy hlídá kontrola.

   Když něco takového omylem odejde, **hned to řekni Danovi**. Samo smazání nepomůže.
4. **Před každým pushem spusť `python3 tools/zkontroluj.py`.** Exit 1 znamená, že je potřeba nejdřív opravit chyby.
5. Push jen na `main` a **nikdy `--force`**. Před commitem udělej `git pull --rebase`, ať nepřepíšeš cizí příspěvek
   ani publikaci dashboardu.

## Přidání zakázky krok za krokem

1. **Zvol id** ve tvaru `<iniciály>-<NNN>`, malými písmeny, 2–4 písmena a tři číslice: `vk-001`, `ok-001`, další
   zakázka `vk-002`. Firemní zakázky mají id `z-001`, `z-002`… a s tvým se tak nepotkají.
2. **Založ složku** `zakazky/<id>/` a do ní zkopíruj `zakazky/_ukazka/zakazka.json` (vzor se všemi poli). Přepiš ho
   podle své zakázky a pole, která nepotřebuješ, smaž.
3. **Přidej obrázky** (render JPG nebo WebP) a případně 3D model `model.glb` do téže složky (návod níž).
4. **Přidej id** na konec seznamu v `zakazky/index.json`, např. `["vk-001"]`. Co v seznamu není, stránka nezobrazí.
5. **Zkontroluj**: `python3 tools/zkontroluj.py`. Volitelně si stránku prohlédni lokálně (níž).
6. **Commitni a pushni**:
   ```sh
   git pull --rebase
   git add zakazky/<id> zakazky/index.json
   git commit -m "Add <id>: <krátký název>"
   git push origin main
   ```
   Za 1–2 minuty je zakázka na https://make-more-s-r-o.github.io/nabytek-dashboard/ (detail na `#<id>`).
   Ověříš to příkazem `curl -s -o /dev/null -w '%{http_code}\n' https://make-more-s-r-o.github.io/nabytek-dashboard/zakazky/<id>/zakazka.json`,
   který má vrátit `200`. Pak obnov stránku v prohlížeči.

**Úprava** = změň soubory ve složce, zkontroluj a pushni. **Smazání** = odeber id z `index.json` a smaž složku
(v historii gitu zůstane, viz pravidlo 3).

## Pole `zakazka.json`

Povinná jsou jen `autor`, `nazev` a `stav`. Všechny cesty k souborům jsou **relativní ke složce zakázky**
(`render.jpg`, `img/detail.jpg`). Nesmí obsahovat `..`, `/` na začátku, mezery ani diakritiku a záleží v nich
na velikosti písmen, protože GitHub Pages rozlišuje `Render.JPG` a `render.jpg` (macOS ne).

| Pole | Typ | Co to je |
|---|---|---|
| `autor` | text, **povinné** | tvoje jméno, zobrazí se ve štítku „příspěvek: …“ |
| `nazev` | text, **povinné** | název zakázky, např. „Regál do obýváku“ |
| `stav` | text, **povinné** | `poptavka` · `navrh` · `nabidka` · `vyroba` · `montaz` · `hotovo` |
| `cislo` | text | číslo na kartě („Zakázka …“); když chybí, použije se id |
| `popis` | text | odstavec o zakázce |
| `faze` | objekt | kdy zakázka vstoupila do fáze: `{"poptavka": "2026-10-01", "navrh": "2026-10-06"}` |
| `klient` | objekt | `jmeno` (OBECNĚ: „rodina, Praha“), `poznamka`; pole `kontakt` je zakázané |
| `rozmery` | objekt | `sirka_mm`, `hloubka_mm`, `vyska_mm` (čísla), `pozn` (text) |
| `cena` | objekt | `material_bez_dph`, `sluzby_low`, `sluzby_high`, `nabidnuto`, `marze_pct` (čísla bez „Kč“ nebo `null`), `pozn`. Jen ceníkové ceny, žádné nákupní ceny po slevě |
| `termin` | datum | `"2026-11-15"` nebo `null` |
| `rendery` | seznam | `[{"id": "r1", "soubor": "render.jpg", "popis": "Hlavní pohled"}]`, první nebo `hlavni_render` je na kartě |
| `hlavni_render` | text | `id` renderu pro kartu a začátek galerie |
| `soubory` | seznam | `[{"nazev": "Nabídka", "typ": "PDF", "url": "nabidka.pdf"}]`, kde `url` je relativní cesta ve složce, nebo odkaz `https://` |
| `verze` | seznam | verze návrhu: `cislo` (povinné, `"v1"`), `poradi`, `datum`, `nazev`, `popis_zmen`, `render {"soubor": …}`, `pohledy [{id, nazev, soubor}]` (stejné záběry verzí, pak jde porovnat posuvníkem), `stav`, `cena_material_bez_dph`, `pocet_dilu`, `git_tag`, `git_ref` |
| `poznamky` | seznam | `[{"datum": "2026-10-06 14:30", "autor": "Viktor", "text": "…"}]`, text smí mít Markdown (`**tučně**`, odrážky) |
| `model` | text nebo objekt | `"model.glb"`, nebo `{"soubor": "model.glb", "nazev": "Regál v1", "verze": "v1", "pozn": "…", "skupiny": [{"id": "korpus", "nazev": "Korpus", "vychozi": true}]}` |
| `aktualizovano` | ISO čas | `"2026-10-07T09:00:00Z"`, kvůli řazení „naposledy upraveno“ |

Kompletní vzor najdeš v `zakazky/_ukazka/zakazka.json`. Složka začíná podtržítkem a v `index.json` není, takže se
na webu nezobrazí, ale kontrola ji ověřuje.

## Obrázky

- **JPG nebo WebP**, delší strana **nejvýš 1600 px**, ideálně **do 1 MB** (kontrola odmítne nad 1600 px nebo nad 2 MB).
- Render z Blenderu: Output Properties → Resolution třeba 1600 × 1200, File Format JPEG, Quality 80–85.
  Z příkazové řádky: `Blender -b scena.blend -o //render_# -F JPEG -f 1`.
- Zmenšení hotového obrázku na Macu: `sips -Z 1600 -s format jpeg -s formatOptions 82 vstup.png --out render.jpg`.
- Žádné fotky skutečných interiérů klientů bez souhlasu (pravidlo 3).

## 3D model z Blenderu (GLB)

Prohlížeč ve stránce ukáže GLB nebo glTF, model jde otáčet a klikem na díl se ukáže jeho ID, název, rozměr a materiál.

**Export v Blenderu:** File → Export → glTF 2.0, a v něm:
- Format **glTF Binary (.glb)**, soubor `zakazky/<id>/model.glb`,
- Include → Limit to **Visible Objects** (nebo Selected), Cameras a Punctual Lights vypnout,
  **Custom Properties** zapnout, pokud díly nesou metadata (níž),
- Transform → **+Y Up** zapnuté (výchozí),
- Mesh → **Apply Modifiers** zapnout,
- **Compression (Draco) VYPNOUT.** Prohlížeč Draco neumí a kontrola takový model odmítne.

**Totéž z příkazové řádky:**
```sh
/Applications/Blender.app/Contents/MacOS/Blender -b moje.blend --python-expr "
import bpy
for o in bpy.data.objects: o.select_set(o.type == 'MESH' and o.visible_get())
bpy.ops.export_scene.gltf(filepath='zakazky/vk-001/model.glb', export_format='GLB', use_selection=True,
    export_apply=True, export_extras=True, export_yup=True, export_cameras=False, export_lights=False)
"
```

**Jednotky:** na jednotkách pro zobrazení nezáleží, protože prohlížeč model sám vycentruje a přiblíží. Doporučené je
modelovat v metrech (výchozí Blender). Když je scéna v milimetrech (1 jednotka = 1 mm), model je v GLB tisíckrát větší
a prohlížeč to pozná sám: model větší než 50 jednotek bere jako milimetry.

**Díly pojmenuj** ve tvaru `<ID> <název>`, např. `BK-01 Bok levý`. První slovo jména objektu je ID dílu,
zbytek jeho název. Obojí uvidí ten, kdo na díl klikne (`Cube.017` nic neřekne). Volitelně můžeš objektu přidat Custom Properties (Object Properties → Custom Properties) a v exportu
zapnout Custom Properties:

| Vlastnost | Příklad | Bez ní |
|---|---|---|
| `id` | `BK-01` | první slovo jména objektu |
| `nazev` | `Bok levý` | zbytek jména objektu |
| `rozmer` | `1200 × 300 × 18 mm` | dopočítá se z modelu jako „≈ … mm (z modelu)“ |
| `material` | `Bříza překližka 18` | název materiálu v Blenderu |
| `skupina` | `korpus` | bez přepínání skupin |

Když díly mají `skupina`, uveď skupiny v `zakazka.json` v `model.skupiny`. Na stránce pak jdou zapínat a vypínat,
přičemž `"vychozi": false` skupinu na začátku skryje (hodí se třeba pro místnost).

**Velikost:** cíl **do 5 MB**, kontrola odmítne nad 15 MB. Drobné kování (šrouby, kolíky, panty, cokoli pod
~200 mm) do modelu nedávej, skryj ho nebo nevybírej. Těžké tvary zmenši modifikátorem Decimate. Ukázkový GLB
s metadaty je `zakazky/_ukazka/model.glb` (12 KB).

## Kontrola a náhled

```sh
python3 tools/zkontroluj.py            # všechno, co je v index.json, plus _ukazka
python3 tools/zkontroluj.py vk-001     # jen jedna zakázka
```
Kontrola ověří tvar a typy polí, existenci souborů včetně velikosti písmen, rozměr a velikost obrázků, GLB bez Draco
a zakázané údaje (e-mail, telefon, PSČ s obcí, ulice s číslem popisným, pole s kontaktem, slevou nebo nákupní cenou).
Varování push nezastaví, chyby ano.

**Lokální náhled** (stránka načítá příspěvky jen přes http, z `file://` je neuvidíš):
```sh
python3 -m http.server 8000     # v kořeni repa, pak otevři http://localhost:8000/#vk-001
```

## Když něco nefunguje

- **Karta ukazuje „Příspěvek … se nenačetl“**: chybí `zakazka.json` nebo je to neplatný JSON. Hláška na kartě
  řekne, co přesně je špatně, a spusť kontrolu.
- **Zakázka na webu není**: id chybí v `index.json`, Pages ještě nedoběhly (počkej 1–2 minuty), nebo id koliduje
  s firemní zakázkou (v konzoli prohlížeče je varování).
- **Obrázek se nezobrazí**: velikost písmen v cestě, nebo cesta mimo složku zakázky. Stránka takovou cestu zahodí
  a v konzoli prohlížeče napíše proč.
- **3D model se nenačte**: Draco komprese, nebo chybějící `.bin` u `.gltf`. Exportuj jako `.glb` bez komprese.
