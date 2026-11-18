"""Syntetyczna mapa .mp do pomiarow wydajnosci (np. pwmapedit --bench).

uzycie: python gen_bench_map.py wynik.mp [liczba_obiektow=110000] [ziarno=1]

Sklad przypomina mape UMP: POI z etykietami, ulice z numeracja, drogi glowne z Data1 (inna geometria na poziomie 1),
budynki, lasy, jeziora oraz nieliczne dlugie drogi i duze polygony - te ostatnie trafiaja do wielu lisci indeksu BSP.
"""
import math
import random
import sys

LAT0, LAT1 = 51.0, 52.0
LON0, LON1 = 19.0, 20.5

HEADER = """; mapa syntetyczna - cpp/tools/gen_bench_map.py
[IMG ID]
CodePage=1250
LblCoding=9
ID=48999998
Name=bench
Levels=4
Level0=24
Level1=22
Level2=20
Level3=17
Zoom0=0
Zoom1=1
Zoom2=2
Zoom3=3
[END-IMG ID]

"""

NAMES = ['Lipowa', 'Polna', 'Leśna', 'Słoneczna', 'Krótka', 'Szkolna', 'Ogrodowa', 'Łąkowa', 'Kościelna', 'Żytnia']


def coord(lat, lon):
    return f'({lat:.5f},{lon:.5f})'


def data(points):
    return ','.join(coord(lat, lon) for lat, lon in points)


def random_point(rnd, margin=0.0):
    return rnd.uniform(LAT0 + margin, LAT1 - margin), rnd.uniform(LON0 + margin, LON1 - margin)


def walk(rnd, n, step):
    lat, lon = random_point(rnd, 0.05)
    heading_lat, heading_lon = rnd.uniform(-1, 1), rnd.uniform(-1, 1)
    points = []
    for _ in range(n):
        points.append((min(max(lat, LAT0), LAT1), min(max(lon, LON0), LON1)))
        heading_lat += rnd.uniform(-0.4, 0.4)
        heading_lon += rnd.uniform(-0.4, 0.4)
        norm = max((heading_lat ** 2 + heading_lon ** 2) ** 0.5, 1e-6)
        heading_lat, heading_lon = heading_lat / norm, heading_lon / norm
        lat += heading_lat * step * rnd.uniform(0.5, 1.5)
        lon += heading_lon * step * rnd.uniform(0.5, 1.5)
    return points


def ring(rnd, size, n):
    lat, lon = random_point(rnd, size)
    points = []
    for i in range(n):
        angle = 2 * math.pi * i / n
        r = size * rnd.uniform(0.6, 1.0)
        points.append((lat + r * 0.6 * math.sin(angle), lon + r * math.cos(angle)))
    return points


def poi(rnd):
    t = rnd.choice(['0x2a00', '0x2c00', '0x2f00', '0x6400', '0x2e00'])
    lat, lon = random_point(rnd)
    return f'[POI]\nType={t}\nLabel={rnd.choice(NAMES)} {rnd.randint(1, 99)}\nEndLevel=0\nData0={coord(lat, lon)}\n[END]\n\n'


def street(rnd):
    points = walk(rnd, rnd.randint(4, 25), 0.0008)
    out = [f'[POLYLINE]\nType={rnd.choice(["0x6", "0x6", "0x6", "0x5", "0x7", "0x16"])}']
    if rnd.random() < 0.7:
        out.append(f'Label={rnd.choice(NAMES)}')
    out.append('EndLevel=0')
    out.append(f'Data0={data(points)}')
    if rnd.random() < 0.3:
        last = len(points) - 1
        out.append(f'Numbers1=0,O,1,{2 * last + 1},E,2,{2 * last + 2}')
        if last > 2:
            out.append(f'Numbers2={last // 2},N,-1,-1,N,-1,-1')
    out.append('[END]\n\n')
    return '\n'.join(out)


def main_road(rnd, long_road=False):
    n = rnd.randint(200, 800) if long_road else rnd.randint(20, 120)
    points = walk(rnd, n, 0.004 if long_road else 0.002)
    out = [f'[POLYLINE]\nType={rnd.choice(["0x1", "0x2", "0x3", "0x4"])}', f'Label=~[0x2a]{rnd.randint(1, 999)}',
           f'EndLevel={rnd.randint(1, 3)}', f'Data0={data(points)}']
    if rnd.random() < 0.8:
        out.append(f'Data1={data(points[::4] + ([points[-1]] if (len(points) - 1) % 4 else []))}')
    out.append('[END]\n\n')
    return '\n'.join(out)


def polygon(rnd, kind):
    if kind == 'building':
        t, size, n, end, data1 = rnd.choice(['0x13', '0x13', '0x6c']), rnd.uniform(0.0001, 0.0004), rnd.randint(4, 10), 0, False
    elif kind == 'forest':
        t, size, n, end, data1 = '0x50', rnd.uniform(0.003, 0.03), rnd.randint(15, 80), rnd.randint(0, 2), True
    elif kind == 'lake':
        t, size, n, end, data1 = '0x3c', rnd.uniform(0.002, 0.02), rnd.randint(15, 60), rnd.randint(0, 2), True
    else:  # big: duzy las / obszar zabudowy na pol mapy
        t, size, n, end, data1 = rnd.choice(['0x50', '0x1', '0x4e']), rnd.uniform(0.1, 0.35), rnd.randint(200, 600), 3, True
    points = ring(rnd, size, n)
    out = [f'[POLYGON]\nType={t}', f'EndLevel={end}', f'Data0={data(points)}']
    if data1 and end >= 1:
        out.append(f'Data1={data(points[::3])}')
    out.append('[END]\n\n')
    return '\n'.join(out)


def main():
    path = sys.argv[1]
    total = int(sys.argv[2]) if len(sys.argv) > 2 else 110000
    rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    parts = [HEADER]
    for _ in range(total):
        r = rnd.random()
        if r < 0.30:
            parts.append(poi(rnd))
        elif r < 0.65:
            parts.append(street(rnd))
        elif r < 0.72:
            parts.append(main_road(rnd, long_road=rnd.random() < 0.02))
        elif r < 0.92:
            parts.append(polygon(rnd, 'building'))
        elif r < 0.96:
            parts.append(polygon(rnd, 'forest'))
        elif r < 0.995:
            parts.append(polygon(rnd, 'lake'))
        else:
            parts.append(polygon(rnd, 'big'))
    with open(path, 'w', encoding='cp1250', newline='\r\n') as f:
        f.write(''.join(parts))


if __name__ == '__main__':
    main()
