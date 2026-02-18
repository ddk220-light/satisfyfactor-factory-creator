#!/usr/bin/env python3
"""Download Satisfactory map tiles from satisfactory.th.gl and stitch into a single image."""
import urllib.request
import concurrent.futures
from PIL import Image
from io import BytesIO

TILE_URL = 'https://cdn.th.gl/satisfactory/map-tiles/world-2df35f0493da3e344578a15599341a95/{z}/{y}/{x}.webp'
ZOOM = 3
TILE_SIZE = 512
TILES_PER_SIDE = 2 ** ZOOM  # 8
TOTAL_SIZE = TILE_SIZE * TILES_PER_SIDE  # 4096

# Map coordinate bounds (game units = centimeters)
# From satisfactory.th.gl Leaflet config: bounds [[-374999,-324999],[374999,424999]]
# That's [[minY, minX], [maxY, maxX]] in Leaflet [lat,lng] format
MAP_BOUNDS = {
    'min_x': -324999,
    'max_x': 424999,
    'min_y': -374999,
    'max_y': 374999,
}


def download_tile(z, y, x):
    url = TILE_URL.format(z=z, y=y, x=x)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return (x, y, Image.open(BytesIO(data)))


def main():
    print(f'Downloading {TILES_PER_SIDE}x{TILES_PER_SIDE} = {TILES_PER_SIDE**2} tiles at zoom {ZOOM}...')
    canvas = Image.new('RGB', (TOTAL_SIZE, TOTAL_SIZE))
    tasks = [(ZOOM, y, x) for y in range(TILES_PER_SIDE) for x in range(TILES_PER_SIDE)]

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(download_tile, *t): t for t in tasks}
        for f in concurrent.futures.as_completed(futures):
            try:
                x, y, tile = f.result()
                canvas.paste(tile.convert('RGB'), (x * TILE_SIZE, y * TILE_SIZE))
                done += 1
                if done % 8 == 0 or done == len(tasks):
                    print(f'  {done}/{len(tasks)} tiles')
            except Exception as e:
                t = futures[f]
                print(f'  FAILED tile z={t[0]} y={t[1]} x={t[2]}: {e}')

    out = '/Users/deepak/AI/satisfy/satisfactory-map.jpg'
    canvas.save(out, 'JPEG', quality=85)
    print(f'Saved {out} ({TOTAL_SIZE}x{TOTAL_SIZE})')
    print(f'Map bounds: {MAP_BOUNDS}')


if __name__ == '__main__':
    main()
