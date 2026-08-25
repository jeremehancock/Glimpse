"""Generate a fake library snapshot, at any size, for a development container.

Development tooling. Not shipped.

WHY SIZE IS THE POINT. `web/index.html` renders every item as a DOM node —
`mediaData.forEach`, with only the images lazy-loading — so the document grows
with the library. The user's is ~7,000 items. Several suspected defects are
believed to be relayout costs at that scale: the overlay scroll lock sets
`position: fixed` on `<body>` on the same frame a tray starts moving, which
forces a full relayout of every card at frame 1.

**A few-hundred-item fixture cannot reproduce any of that.** One session drove a
real browser against 400 items, saw nothing wrong, and that was not evidence of
health. Default here is 7000 for exactly that reason.

    python tools/seed_library.py --out ./data                 # 7000 items
    python tools/seed_library.py --out ./data --movies 400 --shows 250

Then, because `config/entrypoint.sh` runs a fetch on every container start and
that fetch DELETES the snapshots when it cannot reach a media server, copy them
in after the container is up rather than mounting and hoping:

    python tools/seed_library.py --out /tmp/seed --posters 0
    for s in plex jellyfin; do for k in movies tvshows; do
      docker cp /tmp/seed/$s/$k.json <container>:/app/data/$s/$k.json
    done; done
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

SERVERS = ('plex', 'jellyfin', 'emby')

GENRES = [
    'Action',
    'Adventure',
    'Animation',
    'Comedy',
    'Crime',
    'Documentary',
    'Drama',
    'Family',
    'Fantasy',
    'Horror',
    'Mystery',
    'Romance',
    'Sci-Fi',
    'Thriller',
    'War',
    'Western',
]

# A 1x1 JPEG. Real dimensions do not matter — what is being exercised is the
# request count and the node count, not decode cost.
PIXEL = bytes.fromhex(
    'ffd8ffe000104a46494600010100000100010000ffdb004300ff'
    'ffffffffffffffffffffffffffffffffffffffffffffffffffff'
    'ffffffffffffffffffffffffffffffffffffffffffffffffffff'
    'ffffffffffffffffffffffffffffffffffffffffffffffffffff'
    'ffffffffffffffffffffffffffffffffffffffffffffc2000b08'
    '0001000101011100ffc40014000100000000000000000000'
    '0000000000ffda0008010100000001bfffc40014100100000000'
    '00000000000000000000000000ffda0008010100010502ffc400'
    '141001000000000000000000000000000000000000ffda000801'
    '0100063f02ffc40014100100000000000000000000000000000000'
    '0000ffda0008010100013f21ffda000c03010002000300000010'
    '00ffc40014110100000000000000000000000000000000000fff'
    'da0008010301013f10ffc4001411010000000000000000000000'
    '00000000000000ffda0008010201013f10ffc400141001000000'
    '0000000000000000000000000000ffda0008010100013f10ffd9'
)


def build(kind: str, count: int, offset: int) -> list[dict]:
    """Items shaped like what the fetchers write. Deterministic per offset."""
    rng = random.Random(offset)
    return [
        {
            'id': str(offset + index),
            'title': f'{kind.title()} Title {index:05d}',
            'year': 1970 + (index % 55),
            # Descending by index, so a date sort visibly reorders an alpha sort.
            'addedAt': 1_700_000_000 - index * 3600,
            'summary': f'Seeded {kind} #{index} for development. Not a real title.',
            'genres': rng.sample(GENRES, k=rng.randint(1, 3)),
        }
        for index in range(count)
    ]


def seed(out: Path, movies: int, shows: int, posters: int, servers: tuple[str, ...]) -> None:
    for server in servers:
        base = out / server
        for kind, count, offset in (('movies', movies, 0), ('tvshows', shows, 1_000_000)):
            base.mkdir(parents=True, exist_ok=True)
            items = build(kind, count, offset)
            (base / f'{kind}.json').write_text(json.dumps(items))

            if posters:
                directory = base / 'posters' / kind
                directory.mkdir(parents=True, exist_ok=True)
                # Only the first N: the grid lazy-loads its images, so these are
                # the ones actually requested on a first screen.
                for item in items[:posters]:
                    (directory / f'{item["id"]}.jpg').write_bytes(PIXEL)

        print(f'{server}: {movies} movies, {shows} shows, {posters} posters each')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', type=Path, required=True, help='data directory to write into')
    parser.add_argument('--movies', type=int, default=7000, help='default 7000 — see the note')
    parser.add_argument('--shows', type=int, default=1200)
    parser.add_argument('--posters', type=int, default=60, help='poster files per kind; 0 for none')
    parser.add_argument('--servers', default='plex,jellyfin')
    arguments = parser.parse_args()

    chosen = tuple(name.strip() for name in arguments.servers.split(',') if name.strip())
    unknown = [name for name in chosen if name not in SERVERS]
    if unknown:
        parser.error(f'unknown server(s): {", ".join(unknown)}')

    seed(arguments.out, arguments.movies, arguments.shows, arguments.posters, chosen)


if __name__ == '__main__':
    main()
