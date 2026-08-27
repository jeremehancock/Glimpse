"""Publish the library snapshot without ever taking it away.

nginx serves `/app/data` to a frontend that may load at any instant, including
every instant of a fetch run. So the question a writer has to answer is not "is
the file correct when I finish" but "is the file correct at every moment in
between" — and the answer used to be no, in three separate ways.

Both fetchers opened a run by *deleting* `movies.json` and `tvshows.json` and
wrote the replacements at the very end. For the minutes between, the files did
not exist: the page shell still loaded, the snapshot 404'd, and the viewer was
told `Failed to load movie data. Please try again later.` A run that gave up in
between — an unreachable server, a rejected token — never wrote the replacements
at all, so the library stayed gone until a later run happened to succeed. And
the final write was a plain truncating `open(path, 'w')`, so even the happy path
had a window where a reader could see half a file.

All three have one fix: never modify a published file. Write a complete copy
beside it and rename it over the top. A rename within a filesystem is
indivisible — a reader holds either the whole old file or the whole new one, and
there is no third possibility.

This module is shared by both fetchers on purpose. It is small enough to copy
and subtle enough that the two copies would drift, and those two files are the
ones this project has already let drift apart once (Emby and Jellyfin are one
adapter with two identities; a fix applied to one and not the other has shipped
here before).

See `glimpse_config.py::_write_json`, which does the same thing for
`config.json` and is where this pattern was first settled.
"""

import json
import os
from collections.abc import Callable, Sequence
from pathlib import Path

# Readable by nginx, which runs as www-data. Set on the TEMP file, because
# permissions travel with a rename and a mode fixed afterwards is fixed too
# late — see _write_temp.
PUBLISHED_MODE = 0o644


def temp_path_for(target: Path) -> Path:
    """The temporary file a given target is staged through.

    In the target's own directory, because `Path.replace()` is only atomic
    within one filesystem. `/app/data` is a mounted volume, so staging through
    `/tmp` would silently turn the rename into a copy and give up the only
    property this module exists to provide.

    The name is fixed rather than randomised. A run killed mid-write leaves its
    temp behind, and a fixed name means the next run overwrites it — at most one
    stale file per target, forever, instead of an unbounded pile in a directory
    nginx serves.
    """
    return target.with_name(f'.{target.name}.tmp')


def _write_temp(
    target: Path,
    payload: object,
    prepare: Callable[[Path], None] | None,
) -> Path:
    """Write `payload` as JSON to `target`'s temp file. Does not publish it."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = temp_path_for(target)

    with temp.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.flush()
        # The rename below is atomic with respect to readers, not with respect
        # to power loss. fsync is what makes the published file whole after a
        # hard stop rather than an entry pointing at unwritten blocks.
        os.fsync(handle.fileno())

    # Before the rename, never after: a renamed file keeps the mode and owner it
    # had as a temp. Get this wrong and the swap is flawless and nginx answers
    # 403 — a fresh way to break the site, reached while fixing the old one, and
    # invisible to any test that does not involve a web server.
    temp.chmod(PUBLISHED_MODE)
    if prepare is not None:
        prepare(temp)

    return temp


def publish_json(
    pairs: Sequence[tuple[Path, object]],
    prepare: Callable[[Path], None] | None = None,
) -> None:
    """Publish several JSON files together, or publish none of them.

    Every payload is written to its temp file first; only when all of them are
    complete does anything get renamed into place. The snapshots are read as a
    **pair** by a single page load, so publishing `movies.json` before
    `tvshows.json` is finished would show the viewer two different points in
    time.

    The renames are consecutive with nothing between them. Two renames are not
    one atomic operation and this does not pretend otherwise — it bounds the
    window in which the files disagree to the gap between two system calls
    instead of to the length of a fetch. Closing it completely would mean
    swapping the server's directory, which is not available: that directory also
    holds `posters/`, `backdrops/` and `checksums.pkl`, none of which a run
    rebuilds, and swapping it would discard the artwork cache.

    `prepare` is called with each temp path before it is published, for
    ownership the caller knows about and this module does not.

    On any failure nothing is published and every temp is removed, so the
    previous snapshot is left exactly as it was found.
    """
    staged: list[tuple[Path, Path]] = []
    try:
        for target, payload in pairs:
            # Registered BEFORE the write, not after it. A payload that fails to
            # serialise has already had its temp file created and partly
            # written; registering on the way out would leave that one — the
            # only one that matters — behind in a directory nginx serves.
            staged.append((temp_path_for(target), target))
            _write_temp(target, payload, prepare)
        for temp, target in staged:
            temp.replace(target)
    except BaseException:
        for temp, _ in staged:
            temp.unlink(missing_ok=True)
        raise
