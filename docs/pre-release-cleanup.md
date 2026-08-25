# Pre-release cleanup — what has to go before `main`

The rewrite has accumulated scaffolding: things committed to get the work done
that must not survive into a release. **None of it fails a build, a lint or a
test.** That is the whole reason this file exists — cruft is invisible to every
gate in the project, so the only defence is a list someone reads on purpose.

Work this list *before* the release PR, not after. Anything still here when
`main` gets the rewrite is something a user can find.

---

## Must go

### 1. `docs/handover.md`

A snapshot of an in-progress rewrite, written for the next session. It names
unfinished work, open questions and a punch list. Once the rewrite lands it is
actively misleading — it describes a state that no longer exists. **Delete it**;
its own header says so. Anything in it still worth keeping belongs in
`CLAUDE.md` or a spec, and should be moved there rather than left behind.

### 2. The config adapter in `web/index.html`

Everything between `CONFIG ADAPTER — temporary, removed by the frontend rewrite`
and `END OF CONFIG ADAPTER`. Introduced by `replace-boot-time-html-rewriting` to
do what `sed` used to do at container start; it is marked in-file for removal by
the ES-modules change. If that change lands, this goes with it. **If the
ES-modules change does NOT land before release, this block stays** — it is
working code, not dead code, and removing it without its replacement breaks the
app. Say so in the PR rather than deleting it on principle.

### 3. `tools/` and this file

`tools/browser.py` and `tools/seed_library.py` are development scaffolding.
Neither is shipped — the `Dockerfile` copies `scripts/`, `web/` and `config/`
only — so leaving them costs a user nothing, and they are genuinely useful for
anyone verifying a frontend change later.

**Decide deliberately rather than by default.** Keeping them means keeping
`tools/README.md` accurate and keeping them working. Deleting them means the
next person rebuilds `browser.py` from a transcript for the third time. Either
answer is fine; drifting into "they're still there and nobody knows if they run"
is not.

This file goes when the list is empty.

### 4. The `openspec/changes/` backlog

Six changes are implemented and unarchived, and `openspec/specs/` is still
**empty** — nothing in this repo has ever been archived. Archiving is what makes
the specs the source of truth, and it must happen in the same PR as the code.
`/ship` handles it. Do not archive before the user has validated a `:dev` image.

### 5. Stale screenshots in `assets/`

All six predate the rewrite. `screenshot-details-*` show the detail view as a
centred box with a corner close button — the presentation the tray conversion
replaced. They are served from `main`, so nobody sees them as wrong until the
rewrite merges, and then all six are wrong at once. Needs a real media library,
so it is a release-time task.

---

## Must be decided

### 6. `VERSION` and the publish bootstrap

`VERSION` reads `1.3.0` and the `v1.3.0` tag exists, so a merge today publishes
`:latest` and nothing else. The first release cut through CI has to **bump past
1.3.0**, or the tag would overwrite a published image with different code.

Separately: `main` has no `.github/workflows/`, so `docker-publish.yml` has never
been registered and `:dev` is built by hand. The first merge to `main` is what
registers the trigger — which means that merge may itself publish nothing.
Verify Docker Hub afterwards. See `docs/handover.md` while it still exists.

### 7. `error_page 500 502 503 504 /50x.html` with no `50x.html`

`config/nginx.conf` declares the directive and the image ships no such file, so
every 5xx nginx generates is rewritten to a **404**. Found while testing the
caching change and left alone as out of scope. It is a real papercut for anyone
debugging a broken install: the status they see is not the status that occurred.
Either ship a `50x.html` or drop the directive.

### 8. The legacy fetchers' ruff carve-out

`pyproject.toml` excludes `scripts/plex_data_fetcher.py` and
`scripts/jellyfin_data_fetcher.py` from linting — 187 failures between them. The
comment there already frames it as the rewrite's checklist rather than a
permanent exemption: each entry is deleted along with the file it names, and the
block goes when the list is empty. It is not empty.

---

## Sweep before the PR

- `make lint`, `make test`, `make docker-smoke` — all green.
- Re-read `README.md` against the shipped behavior. It is the only doc a user
  reads, and the rewrite changed the interface substantially.
- `grep -rn "TODO\|FIXME\|XXX\|HACK" web/ scripts/ config/` — should be empty or
  explained.
- `grep -rn "temporary\|for now\|remove this" web/ scripts/ config/` — catches
  the ones that were never marked with a keyword.
- Confirm `docker-compose.yml` is byte-identical to what users already have, and
  that `tests/test_compose_surface.py` passes untouched.
