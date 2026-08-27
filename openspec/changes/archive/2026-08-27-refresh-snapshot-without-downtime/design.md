# Design: refresh-snapshot-without-downtime

## Context

Two independent defects share one cause: the refresh path takes the library apart
before it has anything to put in its place.

**The current fetch run.** Both fetchers open with `clean_existing_data()`
(`plex_data_fetcher.py:362`, `jellyfin_data_fetcher.py:384`), which unlinks
`movies.json` and `tvshows.json`. Items and artwork are fetched next, and the
replacements are written last (`plex_data_fetcher.py:443-449`) with a plain
`open(path, 'w')`. So the snapshot is absent for the whole run, and the final
write truncates in place.

**The current boot.** `config/entrypoint.sh` calls `run_initial_fetch` for each
configured server unconditionally, before `exec /usr/bin/supervisord` on its last
line. nginx therefore does not exist until every fetch has finished.

**What already exists and should be reused.** `glimpse_config.py::_write_json`
is already a correct atomic writer — temp file in the same directory, `fsync`,
`chmod(0o644)` before the rename, unlink on failure — and its docstring already
records why. This change does not invent that pattern; it extends its reach to
the two files that need it most.

**What constrains the solution.**

- `docker-compose.yml` is frozen and `tests/test_compose_surface.py` asserts its
  variable list exactly, in both directions. No new environment variable.
- `/app/data` is served by nginx (`location ^~ /data/` with `alias /app/data/`),
  so anything written there is publicly readable on an unauthenticated app.
- The generated crontab **inlines** each server's URL, token and exclusion list
  as literal arguments (`glimpse_config.py::crontab`). A scheduled run never
  re-reads the environment.
- "Which servers are configured, and with what" has exactly one implementation,
  in `glimpse_config.py`. The entrypoint this replaced answered it in three
  places and they drifted.

## Goals / Non-Goals

**Goals**

- A reader of the snapshot never sees a 404, a partial body, or the two files
  disagreeing by more than two system calls.
- A failed fetch is a no-op against the previous snapshot.
- A restart that changes nothing relevant runs no fetch and serves in seconds.
- A restart that changes a server's URL, token or exclusion list re-imports that
  server, and only that server.
- No new environment variable, and no credential written to disk.

**Non-Goals**

- Telling the frontend that an import is in progress. A first install still shows
  the generic load error while its first import runs. That needs a status
  contract between fetcher and page which does not exist today.
- Moving `exec supervisord` earlier, or running fetches in the background.
- Staggering the cron schedule across servers.
- Making `checksums.pkl` durable against an interrupted run.
- Any change to how artwork is fetched, stored, or invalidated.

## Decisions

### D1 — Publish the snapshot by temp file and rename; delete `clean_existing_data()`

Each fetcher writes `movies.json` and `tvshows.json` to a temp file in the **same
directory** as the target, then renames both into place, consecutively, after
both have been written in full. `clean_existing_data()` is removed outright
rather than moved: there is no point in the run at which deleting the previous
snapshot is the right thing to do.

**The writer is a shared module, `scripts/snapshot_io.py`, not a method copied
into each fetcher.** The design originally said "reuse the shape of
`glimpse_config.py::_write_json`", which read as "write it twice". Two copies of
a subtle routine in the two files this project has already let drift apart is the
wrong shape for exactly this change. A module also earns two things a private
method cannot: it is a **new** file, so it is not covered by the fetchers' ruff
carve-out in `pyproject.toml` and must pass the gate; and it can be unit-tested
directly instead of through a fetcher. `Dockerfile` copies `scripts/` as a
directory, and `tests/conftest.py` puts that directory on `sys.path`, so it is
importable in the container and in the tests with no packaging.

Reuse the shape of `glimpse_config.py::_write_json`. Its two non-obvious details
are the ones that bite:

- **The temp file must be in the target's directory.** `os.replace` is atomic
  only within one filesystem. `/app/data` is a mounted volume, so a temp file in
  `/tmp` would make the rename a copy — non-atomic, and the whole point lost.
- **`chmod(0o644)` on the temp file, before the rename.** `mkstemp` creates at
  `0600` and permissions travel with the rename. Skip this and the atomic swap
  works perfectly and nginx returns 403 — a new way to break the site, reached
  while fixing the old one. The fetchers' existing `set_permissions()` runs
  against the final path, so it must move to the temp path or it fires too late.

Deferring the rename until both files are written is what keeps a page load from
seeing a new movie list beside an old TV list. The residual window is two
consecutive `os.replace` calls. Closing it fully would require swapping the
server directory, which is not available — that directory also holds `posters/`,
`backdrops/` and `checksums.pkl`, and swapping it would discard the artwork cache.

*Alternative considered — write in place but hold a lock.* nginx does not
participate in any lock this project could take, so it would not stop a partial
read. Rejected.

*Alternative considered — keep `clean_existing_data()` and restore on failure.*
A restore path only runs when the process survives to run it. A killed container
or an OOM leaves the library deleted. The temp-file approach has no such path
because the destructive step never happens.

### D2 — Fetch failures leave the previous snapshot untouched, for free

This needs no separate mechanism once D1 lands: a run that returns early has
written only a temp file. The requirement is stated separately in the spec
because it is the failure that reached users, and because a future refactor that
reintroduces an up-front delete would satisfy D1's happy path while re-breaking
this.

Both fetchers' early-return paths (unreachable server, rejected token, user
lookup returning nothing) are then correct without individually auditing them,
which is the point — the safety comes from the ordering, not from enumerating
failure modes.

### D3 — Fingerprint contents: three inputs, normalised, hashed as JSON

A server's fingerprint covers exactly `url`, `token`, and `exclude_libraries` —
the three fields of `Server` that determine what a snapshot contains. Everything
else in `Resolved` affects display or scheduling only.

**Hash `json.dumps` of a list, not a delimiter join.** A URL and an exclusion
list both admit commas and spaces, so a joined string collides: `"a,b" + "c"` and
`"a" + "b,c"` produce identical text. A collision here is a fingerprint that
matches when the settings differ, which silently withholds a user's change — the
one direction this must never be wrong in. This repo already made this exact
decision once, for `renderSignature()`, for the same reason.

**Normalise the exclusion list the way the fetcher parses it** — strip each
entry, drop empties, sort. The fingerprint should describe the exclusion's
*effect*, not its spelling; reordering `A,B` to `B,A` excludes the same libraries
and should not cost a full re-import. Normalising differently from the fetcher
would be worse than not normalising, so this reuses the fetcher's parse.

**SHA-256, hex-encoded.** No security property is claimed beyond one-wayness; the
requirement is that the file discloses nothing and that a change is always
detected.

### D4 — The fingerprint file lives at `/app/data/<server>/fingerprint`

Per-server, beside the snapshot it describes, on the mounted volume so it
survives a container rebuild — which is the entire point.

It holds the hash and nothing else. `/app/data` is publicly readable, so a file
containing `PLEX_TOKEN` would be a credential download away from anyone who can
reach the port. A hash is safe to sit there.

Under `/app/data`, never `/app/web`. The entrypoint generates exactly two files
under the web root and that list does not grow here.

*A plain name, not a dotfile.* `checksums.pkl` sets the precedent, and a leading
dot is skipped by enough backup and sync tools to be a liability on a volume
users copy around.

### D5 — `glimpse_config.py` computes fingerprints; the entrypoint compares files

`Server` gains a `fingerprint()` method. `main()` gains `--fingerprint-dir
<path>`: it writes one file per configured server, named by server id, each
holding that server's current hash. The entrypoint passes
`/run/glimpse/fingerprints` alongside the existing `--output` and `--crontab`.

The entrypoint then never computes a hash and never parses a format:

```
cmp -s "$FP_DIR/$id" "$DATA_DIR/$id/fingerprint"   # equal → skip
cp    "$FP_DIR/$id" "$DATA_DIR/$id/fingerprint"    # after a successful fetch
```

`cmp` treats a missing file as a difference, so "no fingerprint recorded" falls
out of the same comparison as "fingerprint differs" — both run the fetch, which
is what the spec requires, with no branch to get wrong.

`/run` is deliberate: the expected fingerprint is derived from the current
environment on every boot and must never persist. Only the *recorded* one, under
`/app/data`, survives a restart.

*Alternative considered — `--fingerprint <server-id>` printing to stdout.* One
python invocation per server, and `main()` already prints resolution output that
would have to be suppressed for that mode. File comparison in shell is less code
in the harder language.

*Alternative considered — carry fingerprints in `config.json`.* That file is the
frontend contract. The frontend has no use for these, and adding them would put a
hash of the token into a document the page reads. Rejected.

### D6 — Write the fingerprint only after a successful fetch

`run_initial_fetch` already distinguishes success from failure; it warns and
continues on failure so one bad server does not stop the others. The `cp` goes on
the success path only.

Writing it earlier would assert that the data on disk was produced by the current
settings. If the fetch then fails, the next restart reads that assertion, skips,
and withholds the user's change until a scheduled run happens to succeed — with
nothing reporting it, because the container started cleanly and the site serves.

### D7 — Scheduled runs do not touch the fingerprint

Only the boot path reads or writes it. A scheduled run always fetches and has no
skip decision to make.

This is safe for a non-obvious reason worth recording: `crontab()` **inlines**
each server's URL, token and exclusion list into the cron line as literal
arguments. A scheduled run therefore executes with the settings that were
resolved at the last boot, not with the current environment. A settings change
that has not been through a restart cannot reach cron at all, so there is no
state for a scheduled run to keep current.

### D8 — A missing fingerprint means fetch, including on upgrade

An install upgrading to this version has a snapshot and no fingerprint. That is
indistinguishable from a first install by design, and it takes one blocking
import — the last one it will take unless a fingerprinted variable changes.

The alternative (write the fingerprint and skip) was put to the user and
rejected: it assumes the settings that produced the existing data match the
current ones, and it is wrong exactly when someone changes a setting in the same
deploy as the upgrade — silently, and in the direction that withholds their
change. **Do not soften this later without going back to that decision.**

### D9 — A fetcher must report failure through its exit status

**Found during implementation, and it blocks D6.** `fetch_and_save_data()`
signals failure by returning early, but `main()` in both fetchers ignores the
return value and falls off the end — so the process exits **0 whether the fetch
succeeded or not**. `run_initial_fetch` tests that exit code, and its existing
"Warning: initial <server> fetch failed" branch has therefore never once run.

Left alone, this defeats the fingerprint entirely: the entrypoint would record a
fingerprint after a fetch that failed, assert the snapshot came from the current
settings, and skip on the next restart. That is precisely the failure D6 exists
to prevent, arriving through the back door.

So `fetch_and_save_data()` returns a bool and `main()` exits non-zero on false.
Only the paths that already give up early count as failure — an unreachable
server, an unusable token, a library or user lookup that returns nothing. A
library that is legitimately empty is a **success**: it is a real state of a real
install, and failing it would break the one case this project is most careful
about elsewhere. A run where individual items failed to process is also a
success, matching what the fetchers already tolerate.

This makes the pre-existing warning branch live for the first time, which is a
small independent improvement: a cron fetch that fails now says so in
`docker logs` instead of passing silently.

## Risks / Trade-offs

- **Restart no longer forces a re-import, and some users use it that way** →
  Deleting `/app/data/<server>/fingerprint` and restarting is the replacement
  gesture. Document it in `docs/docker.md` as the supported way to force a
  refresh; it is more precise than what it replaces, since it is per server.

- **`set_permissions()` applied to the final path instead of the temp path** →
  Produces a correct atomic swap that nginx answers with 403. Silent in
  `make test` (no nginx) and invisible in code review. `make docker-smoke` must
  assert the snapshot is *readable over HTTP* after a fetch, not merely present.

- **A killed run leaves a temp file in the served directory** → Use a fixed temp
  name per target so at most two stale temps exist per server and each run
  overwrites them. They are inert: nothing references them, and the next
  successful run replaces them.

- **The fingerprint drifts from what the fetcher actually uses** → Both read from
  the same `Server` instance, which is the single resolution point. The risk is a
  future field being added to `Server` that affects the snapshot without being
  added to `fingerprint()`. A test asserts the exact field set, in both
  directions, so adding one fails until the decision is made deliberately — the
  same shape as `test_compose_surface.py`.

- **The fix lands in one fetcher and not the other** → Jellyfin and Emby share
  one fetcher, so "both fetchers" means two files covering three servers. This
  project has already shipped a fix to one and not the other. Tests must exercise
  both fetcher modules, not one.

- **A first install still looks broken while it imports** → Unchanged from today,
  and out of scope. Worth stating so it is not read as a regression introduced
  here.

## Migration Plan

1. Ship. On first start, every server has a snapshot and no fingerprint, so every
   configured server imports once and records its fingerprint. The site is
   unavailable for that one import, as it is today.
2. Every subsequent restart with unchanged settings skips all fetches and serves
   immediately.
3. No data migration. No change to the snapshot schema, the artwork layout, or
   `checksums.pkl`.

**Rollback.** Revert the image tag. An older image ignores
`/app/data/<server>/fingerprint` — it is an unknown file in a directory it
already tolerates unknown files in — and resumes fetching on every boot. No
cleanup needed, and none of this change's on-disk output is load-bearing for the
previous version.

## Open Questions

None blocking. One to settle during implementation: whether `make docker-smoke`
grows a fetch-and-verify step, or whether the HTTP-readability assertion in
*Risks* is checked against the boot-time snapshot only. The second is cheaper and
catches the permissions regression; the first also covers the rename path.
