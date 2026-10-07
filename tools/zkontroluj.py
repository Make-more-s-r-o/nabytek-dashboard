#!/usr/bin/env python3
"""Kontrola příspěvků do dashboardu zakázek (jen standardní knihovna Pythonu 3).

    python3 tools/zkontroluj.py          # zkontroluje zakazky/index.json, každou zakázku z něj a zakazky/_ukazka
    python3 tools/zkontroluj.py vk-001   # jen vybrané zakázky (index.json se kontroluje vždy)

Ověří: index.json, tvar a typy polí zakazka.json, existenci souborů (včetně velikosti písmen, GitHub Pages ji
rozlišuje), velikost a rozměr obrázků, GLB/glTF bez Draco, zakázané údaje (e-mail, telefon, adresa, ceny po slevě).
Exit 0 = v pořádku (varování nevadí), exit 1 = chyba, příspěvek takhle nepushuj.
"""
import json
import re
import struct
import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parents[1]
ZAKAZKY = KOREN / 'zakazky'

ID_RE = re.compile(r'^[a-z]{2,4}-\d{3}$')
SEGMENT_RE = re.compile(r'^[A-Za-z0-9_~-][A-Za-z0-9._~-]{0,119}$')
DATUM_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
CAS_RE = re.compile(r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$')
STAVY = ('poptavka', 'navrh', 'nabidka', 'vyroba', 'montaz', 'hotovo')
PRIPONY_OBR = ('.jpg', '.jpeg', '.webp', '.png')
PRIPONY_MODEL = ('.glb', '.gltf')
PRIPONY_SOUBOR = ('.pdf', '.md', '.txt', '.csv', '.jpg', '.jpeg', '.webp', '.png', '.glb', '.gltf', '.step', '.stp', '.dxf', '.zip')
PRIPONY_SLOZKA = PRIPONY_SOUBOR + ('.json', '.bin')    # co smí ve složce zakázky ležet (.bin = buffer k .gltf)

OBR_MAX_PX = 1600
OBR_VAROVANI_B, OBR_MAX_B = 1 * 1024 * 1024, 2 * 1024 * 1024
MODEL_VAROVANI_B, MODEL_MAX_B = 5 * 1024 * 1024, 15 * 1024 * 1024
SLOZKA_MAX_B = 25 * 1024 * 1024
ZAKAZANA_ROZSIRENI = ('KHR_draco_mesh_compression', 'EXT_meshopt_compression', 'KHR_texture_basisu')

POLE = {
    'autor': str, 'cislo': str, 'nazev': str, 'popis': str, 'stav': str, 'faze': dict, 'klient': dict, 'rozmery': dict,
    'cena': dict, 'termin': (str, type(None)), 'soubory': list, 'rendery': list, 'hlavni_render': str,
    'aktualizovano': str, 'verze': list, 'poznamky': list, 'model': (str, dict, type(None)),
}
POLE_KLIENT = {'jmeno', 'poznamka'}
POLE_ROZMERY = {'sirka_mm', 'hloubka_mm', 'vyska_mm', 'pozn'}
POLE_CENA = {'material_bez_dph', 'sluzby_low', 'sluzby_high', 'nabidnuto', 'marze_pct', 'pozn'}
POLE_VERZE = {'cislo', 'poradi', 'datum', 'nazev', 'popis_zmen', 'git_tag', 'git_ref', 'render', 'pohledy', 'stav',
              'cena_material_bez_dph', 'pocet_dilu'}
POLE_MODEL = {'soubor', 'nazev', 'verze', 'pozn', 'pocet_dilu', 'skupiny'}

VELKA = 'A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ'
MALA = 'a-záčďéěíňóřšťúůýž'
VZORY = [
    ('e-mail', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')),
    ('telefon', re.compile(r'(?:\+|\b00)\d{3}[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{3}\b|\b[67]\d{2}[\s-]?\d{3}[\s-]?\d{3}\b')),
    ('PSČ s obcí', re.compile(rf'\b\d{{3}}\s?\d{{2}},?\s+(?!Kč\b)[{VELKA}][{MALA}]{{2,}}')),
    ('ulice s číslem popisným', re.compile(rf'\b[{VELKA}][{MALA}]+\s+\d{{1,4}}/\d{{1,4}}[a-z]?\b')),
    ('cena po slevě', re.compile(r'cena_po_sleve', re.I)),
]
ZAKAZANE_KLICE = re.compile(r'sleva|sleve|nakup|kontakt|telefon|email|e-mail|adresa', re.I)


class Kontrola:
    def __init__(self):
        self.chyby, self.varovani = [], []

    def chyba(self, kde, text):
        self.chyby.append(f'{kde}: {text}')

    def varuj(self, kde, text):
        self.varovani.append(f'{kde}: {text}')


def rel(p):
    return str(p.relative_to(KOREN))


def presne_existuje(slozka, cesta):
    """Soubor existuje přesně v tomhle zápisu (macOS velikost písmen ignoruje, GitHub Pages ne)."""
    p = slozka
    for seg in cesta.split('/'):
        if not p.is_dir() or seg not in {x.name for x in p.iterdir()}:
            return None
        p = p / seg
    return p if p.is_file() else None


def rozmer_obrazku(data):
    """(šířka, výška) z hlavičky JPEG, PNG nebo WebP; None = formát nepoznán."""
    if data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24:
        return struct.unpack('>II', data[16:24])
    if data[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            m = data[i + 1]
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7 or m == 0xFF:
                i += 1 if m == 0xFF else 2
                continue
            delka = struct.unpack('>H', data[i + 2:i + 4])[0]
            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                v, s = struct.unpack('>HH', data[i + 5:i + 9])
                return s, v
            i += 2 + delka
        return None
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP' and len(data) >= 30:
        typ = data[12:16]
        if typ == b'VP8 ':
            w, h = struct.unpack('<HH', data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if typ == b'VP8L':
            b = data[21:25]
            return 1 + (((b[1] & 0x3F) << 8) | b[0]), 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        if typ == b'VP8X':
            return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
    return None


def hledej_vzory(k, kde, text):
    for nazev, vzor in VZORY:
        m = vzor.search(text)
        if m:
            k.chyba(kde, f'vypadá to na {nazev} („{m.group(0)}“), do veřejného repa nepatří')


def projdi_texty(k, kde, x, cesta=''):
    """Všechny klíče a texty v JSONu: zakázané klíče a vzory."""
    if isinstance(x, dict):
        for kk, v in x.items():
            if ZAKAZANE_KLICE.search(str(kk)) and kk not in ('popis_zmen',):
                k.chyba(kde, f'pole „{cesta}{kk}“ do veřejného repa nepatří (kontakty, adresy, nákupní ceny, slevy)')
            projdi_texty(k, kde, v, f'{cesta}{kk}.')
    elif isinstance(x, list):
        for i, v in enumerate(x):
            projdi_texty(k, kde, v, f'{cesta}{i}.')
    elif isinstance(x, str):
        hledej_vzory(k, f'{kde} ({cesta.rstrip(".")})', x)


def je_cislo(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Zakazka:
    def __init__(self, k, zid, slozka):
        self.k, self.zid, self.slozka = k, zid, slozka
        self.pouzite = {'zakazka.json'}
        self.kde = rel(slozka / 'zakazka.json')

    def cesta(self, kde, hodnota, pripony):
        """Relativní cesta ve složce zakázky; vrátí soubor nebo None (a zapíše chybu)."""
        if not isinstance(hodnota, str) or not hodnota.strip():
            self.k.chyba(self.kde, f'{kde}: chybí cesta k souboru')
            return None
        t = hodnota.strip()
        if t != hodnota or re.search(r'[\\:?#%]', t) or not all(SEGMENT_RE.match(s) for s in t.split('/')):
            self.k.chyba(self.kde, f'{kde}: cesta „{hodnota}“ neplatí — jen relativní cesta ve složce zakázky, '
                                   'písmena bez diakritiky, číslice, - _ . (žádné „..“, „/“ na začátku ani URL)')
            return None
        if not t.lower().endswith(pripony):
            self.k.chyba(self.kde, f'{kde}: „{t}“ musí mít příponu {", ".join(pripony)}')
            return None
        p = presne_existuje(self.slozka, t)
        if not p:
            self.k.chyba(self.kde, f'{kde}: soubor „{t}“ ve složce není (pozor na velká a malá písmena)')
            return None
        self.pouzite.add(t)
        return p

    def obrazek(self, kde, hodnota):
        p = self.cesta(kde, hodnota, PRIPONY_OBR)
        if not p:
            return
        data = p.read_bytes()
        n = len(data)
        if n > OBR_MAX_B:
            self.k.chyba(rel(p), f'{n / 1048576:.1f} MB, limit {OBR_MAX_B // 1048576} MB — zmenši a ulož jako JPG/WebP kvalita 80')
        elif n > OBR_VAROVANI_B:
            self.k.varuj(rel(p), f'{n / 1048576:.1f} MB, cíl je do 1 MB')
        r = rozmer_obrazku(data)
        if not r:
            self.k.chyba(rel(p), 'obsah není JPEG, PNG ani WebP (přípona neodpovídá?)')
        elif max(r) > OBR_MAX_PX:
            self.k.chyba(rel(p), f'{r[0]} × {r[1]} px, delší strana smí mít nejvýš {OBR_MAX_PX} px')

    def model(self, kde, hodnota):
        p = self.cesta(kde, hodnota, PRIPONY_MODEL)
        if not p:
            return
        data = p.read_bytes()
        celkem = len(data)
        if p.suffix.lower() == '.glb':
            if data[:4] != b'glTF' or len(data) < 20:
                self.k.chyba(rel(p), 'není GLB (chybí hlavička glTF)')
                return
            verze, _ = struct.unpack('<II', data[4:12])
            delka, typ = struct.unpack('<I4s', data[12:20])
            if verze != 2 or typ != b'JSON':
                self.k.chyba(rel(p), 'GLB musí být glTF 2.0 s blokem JSON na začátku')
                return
            text = data[20:20 + delka].decode('utf-8', 'replace')
        else:
            text = data.decode('utf-8', 'replace')
        try:
            gl = json.loads(text)
        except ValueError as e:
            self.k.chyba(rel(p), f'JSON modelu nejde přečíst ({e})')
            return
        rozs = set(gl.get('extensionsUsed', [])) | set(gl.get('extensionsRequired', []))
        for r in ZAKAZANA_ROZSIRENI:
            if r in rozs:
                self.k.chyba(rel(p), f'model používá {r} — prohlížeč ho neumí; exportuj znovu bez komprese (Draco vypnout)')
        if p.suffix.lower() == '.gltf':
            for co in ('buffers', 'images'):
                for i, b in enumerate(gl.get(co, [])):
                    u = b.get('uri')
                    if u is None or u.startswith('data:'):
                        continue
                    zaklad = str(Path(hodnota).parent)
                    q = self.cesta(f'{kde} → {co}[{i}]', u if zaklad == '.' else f'{zaklad}/{u}', ('.bin', '.png', '.jpg', '.jpeg', '.webp'))
                    if q:
                        celkem += q.stat().st_size
        if celkem > MODEL_MAX_B:
            self.k.chyba(rel(p), f'model má {celkem / 1048576:.1f} MB, limit {MODEL_MAX_B // 1048576} MB — vynech drobné kování, decimuj')
        elif celkem > MODEL_VAROVANI_B:
            self.k.varuj(rel(p), f'model má {celkem / 1048576:.1f} MB, cíl je do 5 MB')
        hledej_vzory(self.k, rel(p) + ' (jména a vlastnosti objektů)', text if len(text) < 2_000_000 else text[:2_000_000])

    def zkontroluj(self):
        k, kde = self.k, self.kde
        p = self.slozka / 'zakazka.json'
        if not presne_existuje(self.slozka, 'zakazka.json'):
            k.chyba(rel(self.slozka), 'chybí zakazka.json')
            return
        if p.stat().st_size > 1024 * 1024:
            k.chyba(kde, 'zakazka.json je větší než 1 MB (obrázky patří do souborů, ne do JSONu)')
            return
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except (UnicodeDecodeError, ValueError) as e:
            k.chyba(kde, f'neplatný JSON ({e})')
            return
        if not isinstance(d, dict):
            k.chyba(kde, 'zakazka.json musí být objekt { … }')
            return
        for pole, typ in POLE.items():
            if pole in d and not isinstance(d[pole], typ):
                k.chyba(kde, f'pole {pole} má špatný typ ({type(d[pole]).__name__})')
        for pole in d:
            if pole not in POLE:
                k.varuj(kde, f'neznámé pole „{pole}“, stránka ho nezobrazí (překlep?)')
        for pole in ('autor', 'nazev', 'stav'):
            if not isinstance(d.get(pole), str) or not d.get(pole).strip():
                k.chyba(kde, f'chybí povinné pole {pole}')
        if isinstance(d.get('stav'), str) and d['stav'] not in STAVY:
            k.chyba(kde, f'stav „{d["stav"]}“ neznám, povolené: {", ".join(STAVY)}')
        faze = d.get('faze') if isinstance(d.get('faze'), dict) else {}
        for s, v in faze.items():
            if s not in STAVY:
                k.chyba(kde, f'faze.{s}: neznámá fáze')
            elif v is not None and not (isinstance(v, str) and DATUM_RE.match(v)):
                k.chyba(kde, f'faze.{s}: datum piš jako 2026-10-06 nebo null')
        if d.get('termin') is not None and not (isinstance(d['termin'], str) and DATUM_RE.match(d['termin'])):
            k.chyba(kde, 'termin: datum piš jako 2026-10-06 nebo null')
        for pole, dovolene in (('klient', POLE_KLIENT), ('rozmery', POLE_ROZMERY), ('cena', POLE_CENA)):
            x = d.get(pole) if isinstance(d.get(pole), dict) else {}
            for kk, v in x.items():
                if kk not in dovolene:
                    (k.chyba if pole == 'klient' else k.varuj)(kde, f'{pole}.{kk}: pole nepatří do schématu (povolené: {", ".join(sorted(dovolene))})')
                elif kk not in ('pozn', 'jmeno', 'poznamka') and v is not None and not je_cislo(v):
                    k.chyba(kde, f'{pole}.{kk}: musí být číslo (bez mezer a „Kč“) nebo null')
        # rendery
        rendery = d.get('rendery') if isinstance(d.get('rendery'), list) else []
        ids = []
        for i, r in enumerate(rendery):
            if not isinstance(r, dict):
                k.chyba(kde, f'rendery[{i}] musí být objekt {{id, soubor, popis}}')
                continue
            if not isinstance(r.get('id'), str) or not r['id']:
                k.chyba(kde, f'rendery[{i}]: chybí id (např. "r1")')
            elif r['id'] in ids:
                k.chyba(kde, f'rendery[{i}]: id „{r["id"]}“ se opakuje')
            else:
                ids.append(r['id'])
            self.obrazek(f'rendery[{i}].soubor', r.get('soubor'))
        if not rendery:
            k.varuj(kde, 'zakázka nemá žádný render, karta bude bez obrázku')
        if d.get('hlavni_render') and d['hlavni_render'] not in ids:
            k.chyba(kde, f'hlavni_render „{d["hlavni_render"]}“ není mezi id v rendery')
        # soubory
        for i, f in enumerate(d.get('soubory') if isinstance(d.get('soubory'), list) else []):
            if not isinstance(f, dict) or not isinstance(f.get('url'), str):
                k.chyba(kde, f'soubory[{i}] musí být objekt {{nazev, typ, url}}')
                continue
            u = f['url']
            if re.match(r'^[a-z][a-z0-9+.-]*:', u, re.I):
                if not re.match(r'^https://\S+$', u):
                    k.chyba(kde, f'soubory[{i}].url: jen https:// odkaz nebo relativní cesta ve složce, ne „{u}“')
                elif 'nabytek-na-miru' in u:
                    k.varuj(kde, f'soubory[{i}].url vede do soukromého repa, veřejnost ho neotevře')
            else:
                self.cesta(f'soubory[{i}].url', u, PRIPONY_SOUBOR)
        # verze
        cisla = []
        for i, v in enumerate(d.get('verze') if isinstance(d.get('verze'), list) else []):
            if not isinstance(v, dict):
                k.chyba(kde, f'verze[{i}] musí být objekt')
                continue
            for kk in v:
                if kk not in POLE_VERZE:
                    k.varuj(kde, f'verze[{i}].{kk}: neznámé pole (git_url se u příspěvků nezobrazuje)')
            c = v.get('cislo')
            if not isinstance(c, str) or not re.match(r'^[A-Za-z0-9._-]{1,20}$', c):
                k.chyba(kde, f'verze[{i}].cislo: povinné, např. "v1"')
            elif c in cisla:
                k.chyba(kde, f'verze[{i}].cislo „{c}“ se opakuje')
            else:
                cisla.append(c)
            if v.get('datum') is not None and not (isinstance(v['datum'], str) and DATUM_RE.match(v['datum'])):
                k.chyba(kde, f'verze[{i}].datum: piš 2026-10-06')
            if v.get('stav') is not None and v['stav'] not in STAVY:
                k.chyba(kde, f'verze[{i}].stav „{v["stav"]}“ neznám')
            for kk in ('poradi', 'cena_material_bez_dph', 'pocet_dilu'):
                if v.get(kk) is not None and not je_cislo(v[kk]):
                    k.chyba(kde, f'verze[{i}].{kk}: musí být číslo')
            if isinstance(v.get('render'), dict):
                self.obrazek(f'verze[{i}].render.soubor', v['render'].get('soubor'))
            elif v.get('render') is not None:
                k.chyba(kde, f'verze[{i}].render musí být objekt {{"soubor": "…"}}')
            for j, pp in enumerate(v.get('pohledy') or []):
                if not isinstance(pp, dict) or not pp.get('id'):
                    k.chyba(kde, f'verze[{i}].pohledy[{j}] musí být objekt {{id, nazev, soubor}}')
                else:
                    self.obrazek(f'verze[{i}].pohledy[{j}].soubor', pp.get('soubor'))
        # poznámky
        for i, pz in enumerate(d.get('poznamky') if isinstance(d.get('poznamky'), list) else []):
            if not isinstance(pz, dict) or not isinstance(pz.get('text'), str) or not pz['text'].strip():
                k.chyba(kde, f'poznamky[{i}] musí být objekt {{datum, autor, text}} s neprázdným textem')
                continue
            if not (isinstance(pz.get('datum'), str) and CAS_RE.match(pz['datum'])):
                k.chyba(kde, f'poznamky[{i}].datum: piš 2026-10-06 nebo 2026-10-06 14:30')
        # model
        m = d.get('model')
        if m is not None:
            if isinstance(m, str):
                self.model('model', m)
            elif isinstance(m, dict):
                for kk in m:
                    if kk not in POLE_MODEL:
                        k.varuj(kde, f'model.{kk}: neznámé pole')
                self.model('model.soubor', m.get('soubor'))
                for j, g in enumerate(m.get('skupiny') or []):
                    if not isinstance(g, dict) or not isinstance(g.get('id'), str) or not g['id']:
                        k.chyba(kde, f'model.skupiny[{j}] musí být objekt {{id, nazev, vychozi}}')
        projdi_texty(k, kde, d)
        self.slozka_obsah()

    def slozka_obsah(self):
        celkem = 0
        for p in sorted(self.slozka.rglob('*')):
            if not p.is_file():
                continue
            r = p.relative_to(self.slozka).as_posix()
            celkem += p.stat().st_size
            if p.name.startswith('.'):
                if p.name != '.gitkeep':
                    self.k.chyba(rel(p), 'skrytý soubor do složky zakázky nepatří (smaž ho)')
                continue
            if not p.name.lower().endswith(PRIPONY_SLOZKA):
                self.k.chyba(rel(p), f'tenhle typ souboru do veřejného repa nepatří (povolené: {", ".join(PRIPONY_SLOZKA)})')
                continue
            if p.suffix.lower() in ('.md', '.txt', '.csv'):
                hledej_vzory(self.k, rel(p), p.read_text(encoding='utf-8', errors='replace'))
            if r not in self.pouzite and p.suffix.lower() not in ('.bin',):
                self.k.varuj(rel(p), 'soubor nikde v zakazka.json není použitý (smazat, nebo přidat do rendery/soubory?)')
        if celkem > SLOZKA_MAX_B:
            self.k.chyba(rel(self.slozka), f'složka má {celkem / 1048576:.1f} MB, limit {SLOZKA_MAX_B // 1048576} MB')


def main():
    k = Kontrola()
    vyber = sys.argv[1:]
    idx = ZAKAZKY / 'index.json'
    index = []
    if not idx.is_file():
        k.chyba('zakazky/index.json', 'chybí (má obsahovat seznam id, prázdný je [])')
    else:
        try:
            index = json.loads(idx.read_text(encoding='utf-8'))
        except ValueError as e:
            k.chyba('zakazky/index.json', f'neplatný JSON ({e})')
        if not isinstance(index, list):
            k.chyba('zakazky/index.json', 'musí být seznam, např. ["vk-001", "ok-001"]')
            index = []
    videne = set()
    for i, zid in enumerate(index):
        if not isinstance(zid, str) or not ID_RE.match(zid):
            k.chyba('zakazky/index.json', f'položka {i} „{zid}“: id piš jako iniciály-číslo, např. "vk-001"')
            continue
        if zid in videne:
            k.chyba('zakazky/index.json', f'id „{zid}“ je v seznamu dvakrát')
        videne.add(zid)
        if not (ZAKAZKY / zid).is_dir() or zid not in {x.name for x in ZAKAZKY.iterdir()}:
            k.chyba('zakazky/index.json', f'id „{zid}“ nemá složku zakazky/{zid}/')
    slozky = sorted(x.name for x in ZAKAZKY.iterdir() if x.is_dir()) if ZAKAZKY.is_dir() else []
    for s in slozky:
        if s not in videne and not s.startswith('_'):
            k.varuj(f'zakazky/{s}', 'složka není v zakazky/index.json, na dashboardu se nezobrazí')
    kontrolovat = [s for s in slozky if (s in videne or s.startswith('_')) and (not vyber or s in vyber)]
    for s in vyber:
        if s not in slozky:
            k.chyba(f'zakazky/{s}', 'složka neexistuje')
    for s in kontrolovat:
        Zakazka(k, s, ZAKAZKY / s).zkontroluj()
    for v in k.varovani:
        print('VAROVÁNÍ', v)
    for c in k.chyby:
        print('CHYBA   ', c)
    print(f'\nZkontrolováno {len(kontrolovat)} složek, {len(k.chyby)} chyb, {len(k.varovani)} varování.')
    if k.chyby:
        print('Oprav chyby a spusť kontrolu znovu. S chybou nepushuj.')
        sys.exit(1)
    print('V pořádku, můžeš commitnout a pushnout.')


if __name__ == '__main__':
    main()
