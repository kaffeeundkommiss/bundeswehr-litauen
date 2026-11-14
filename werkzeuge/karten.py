# Erzeugt Umriss-Logo und Übersichtskarte Litauens aus Natural Earth (gemeinfrei).
# Eingabe: Ordner mit a0.geojson (ne_10m_admin_0_countries) und pp.geojson (ne_10m_populated_places_simple)
# aus https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
# Orte, die Natural Earth nicht führt (Rūdninkai, Rukla, Nemenčinė, Pabradė): Koordinaten aus den
# jeweiligen Wikipedia-Artikeln (abgerufen 14.11.2026), siehe ORTE_ZUSATZ.
# Aufruf: python3 werkzeuge/karten.py <ordner> <zielordner>
import json, math, sys, os
NE, OUT = sys.argv[1], sys.argv[2]
a0 = json.load(open(os.path.join(NE, 'a0.geojson')))
pp = json.load(open(os.path.join(NE, 'pp.geojson')))
def land(code):
    for f in a0['features']:
        if f['properties']['ADM0_A3'] == code: return f['geometry']
def rings(g):
    if g['type'] == 'Polygon': return g['coordinates']
    return [r for poly in g['coordinates'] for r in poly]
def dp(pts, eps):
    if len(pts) < 3: return pts
    (x1,y1),(x2,y2) = pts[0], pts[-1]
    dx,dy = x2-x1, y2-y1; L = math.hypot(dx,dy) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts)-1):
        x,y = pts[i]; d = abs(dy*x-dx*y+x2*y1-y2*x1)/L
        if d > dmax: dmax, idx = d, i
    if dmax > eps: return dp(pts[:idx+1], eps)[:-1] + dp(pts[idx:], eps)
    return [pts[0], pts[-1]]
def pfad(g, proj, eps, bbox=None):
    out = []
    for r in rings(g):
        if bbox:
            lo = [c[0] for c in r]; la = [c[1] for c in r]
            if max(lo) < bbox[0] or min(lo) > bbox[1] or max(la) < bbox[2] or min(la) > bbox[3]: continue
        pts = [proj(*c[:2]) for c in r]
        m = len(pts)//2
        s = dp(pts[:m+1], eps)[:-1] + dp(pts[m:], eps)
        if len(s) < 3: continue
        out.append('M' + ' L'.join(f'{x:.1f} {y:.1f}' for x,y in s) + 'Z')
    return ''.join(out)
K = math.cos(math.radians(55.2))
ltu = land('LTU')
# Logo: nur das Festland (größter Ring), 64 x 64, Rand 5
haupt = max(rings(ltu), key=len)
xs = [c[0] for c in haupt]; ys = [c[1] for c in haupt]
lon0, lon1, lat0, lat1 = min(xs), max(xs), min(ys), max(ys)
w, h = (lon1-lon0)*K, lat1-lat0
s = 54/max(w, h)
ox, oy = (64-w*s)/2, (64-h*s)/2
logo = pfad({'type': 'Polygon', 'coordinates': [haupt]}, lambda lon,lat: (ox+(lon-lon0)*K*s, oy+(lat1-lat)*s), 0.35)
open(os.path.join(OUT, 'logo-pfad.txt'), 'w').write(logo)
# Karte: Ausschnitt mit Nachbarn
B = (20.4, 27.2, 53.6, 56.6)  # lon min, lon max, lat min, lat max
S = 145
W, H = (B[1]-B[0])*K*S, (B[3]-B[2])*S
pk = lambda lon,lat: ((lon-B[0])*K*S, (B[3]-lat)*S)
teile = []
for code, name in [('LVA','Lettland'),('BLR','Belarus'),('POL','Polen'),('RUS','Russland (Oblast Kaliningrad)')]:
    teile.append(f'<path class="nachbar" d="{pfad(land(code), pk, 0.5, B)}"><title>{name}</title></path>')
teile.append(f'<path class="litauen" d="{pfad(ltu, pk, 0.5, B)}"><title>Litauen</title></path>')
punkte = {}
for f in pp['features']:
    p = f['properties']
    if p['name'] in ('Vilnius', 'Kaunas') and p.get('adm0name') == 'Lithuania':
        punkte[p['name']] = pk(p['longitude'], p['latitude'])
ORTE_ZUSATZ = {'Rūdninkai': (25.150, 54.438), 'Rukla': (24.37778, 55.05278),
               'Nemenčinė': (25.48333, 54.85000), 'Pabradė': (25.76639, 54.98306)}
for n, (lon, lat) in ORTE_ZUSATZ.items():
    punkte[n] = pk(lon, lat)
def massstab(x, y, km, einh_je_km, fs):
    L = km * einh_je_km; h = fs * .42; sw = fs * .07
    r = lambda v: f'{v:.1f}'.rstrip('0').rstrip('.')
    return (f'<g class="massstab" aria-hidden="true">'
            f'<rect class="a" x="{r(x)}" y="{r(y-h)}" width="{r(L/2)}" height="{r(h)}" stroke-width="{r(sw)}"/>'
            f'<rect class="b" x="{r(x+L/2)}" y="{r(y-h)}" width="{r(L/2)}" height="{r(h)}" stroke-width="{r(sw)}"/>'
            f'<text x="{r(x)}" y="{r(y-h-fs*.35)}" font-size="{r(fs)}" style="stroke-width:{fs*.25:.2f}px">0</text>'
            f'<text x="{r(x+L)}" y="{r(y-h-fs*.35)}" font-size="{r(fs)}" style="stroke-width:{fs*.25:.2f}px">{km} km</text></g>')
# Maßstab: 1 Grad Breite = 111,32 km = S Karteneinheiten; links unten, 100 km
teile.append(massstab(15, H-12, 100, S / 111.32, 14))
json.dump({'breite': round(W), 'hoehe': round(H), 'pfade': ''.join(teile), 'orte': {k: [round(v[0],1), round(v[1],1)] for k,v in punkte.items()}},
          open(os.path.join(OUT, 'karte.json'), 'w'), ensure_ascii=False)
print(round(W), round(H), {k: [round(v[0]), round(v[1])] for k,v in punkte.items()})
