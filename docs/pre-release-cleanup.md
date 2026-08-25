# Pre-release cleanup — what has to go before `main`

The rewrite has accumulated scaffolding: things committed to get the work done
that must not survive into a release. **None of it fails a build, a lint or a
test.** That is the whole reason this file exists — cruft is invisible to every
gate in the project, so the only defence is a list someone reads on purpose.

Work this list *before* the release PR, not after. Anything still here when
`main` gets the rewrite is something a user can find.

---

## Must go

### 1. `docs/handover.md` — **DONE, 2026-08-25**

Deleted. What was worth keeping moved rather than vanishing:

- the publish bootstrap and the by-hand `:dev` build command →
  `docs/development-workflow.md`, "The publish bootstrap"
- the Node 16 ESLint trap (a *config* error that reads as a broken config) →
  `docs/development-workflow.md`, Prerequisites
- the frontend-verification rules → `tools/README.md` and `CLAUDE.md`
- the windowed-grid invariants → `CLAUDE.md`

The remaining punch-list item (5 — animate the movies/TV swipe) is not in a
doc; it is unstarted work, not a project rule.

### 2. The config adapter in `web/index.html`

Everything between `CONFIG ADAPTER — temporary, removed by the frontend rewrite`
and `END OF CONFIG ADAPTER`. Introduced by `replace-boot-time-html-rewriting` to
do what `sed` used to do at container start; it is marked in-file for removal by
the ES-modules change. If that change lands, this goes with it. **If the
ES-modules change does NOT land before release, this block stays** — it is
working code, not dead code, and removing it without its replacement breaks the
app. Say so in the PR rather than deleting it on principle.

### 3. `tools/` — **DECIDED: keep all three, 2026-08-25**

`tools/browser.py`, `tools/seed_library.py` and `tools/grid_metrics.py` are
development scaffolding. None is shipped — the `Dockerfile` copies `scripts/`,
`web/` and `config/` only — so leaving them costs a user nothing, and they are
genuinely useful for anyone verifying a frontend change later.

`grid_metrics.py` has a stronger claim to staying than the other two. The media
grid is windowed, and the guarantee that makes it worth having — a bounded
number of rendered elements at any library size — **cannot be checked by
`make test`**: CI has no browser and no seeded library. `tests/test_grid_windowing.py`
pins the source decisions, but the numbers themselves only exist when someone
runs this against thousands of items. Delete it and the next regression is found
by a user.

**Decided: all three stay.** They never enter the image, so they cost a user
nothing, and two of them now guard live invariants — `grid_metrics.py` produces
the only evidence that the grid's bound still holds, and `browser.py` had
already been rebuilt from transcripts twice. The obligation that comes with
keeping them is keeping `tools/README.md` accurate and keeping them working.

**This file goes when the list is empty.** It is not: items 2, 5, 7 and 8
remain.

### 4. The `openspec/changes/` backlog

Six changes are implemented and unarchived, and `openspec/specs/` is still
**empty** — nothing in this repo has ever been archived. Archiving is what makes
the specs the source of truth, and it must happen in the same PR as the code.
`/ship` handles it. Do not archive before the user has validated a `:dev` image.

### 5. Stale screenshots in `assets/` — **DEFERRED, and the README no longer
shows them**

All six predate the rewrite. `screenshot-details-*` show the detail view as a
centred box with a corner close button — the presentation the tray conversion
replaced.

On 2026-08-25 the image block was **removed from `README.md`** rather than
shipped wrong: a picture of an interface that no longer exists is the first
thing a prospective user sees, and worse than no picture.

The **`.png` files stay in `assets/`**, deliberately. The README referenced them
by absolute `raw.githubusercontent.com/.../main/assets/...` URLs, and those URLs
are not necessarily reachable only from here — Docker Hub mirrors this README,
and anything else that ever linked one would 404 the moment the file left the
branch. Removing the markdown costs nothing; removing the files is outward-facing
and has not been assessed.

**Still outstanding.** New screenshots need a real media library, so this is a
release-time follow-up rather than a blocker. Add them back as an ordinary image
block; there is no commented-out scaffolding to restore.

---

## Must be decided

### 6. `VERSION` and the publish bootstrap

`VERSION` reads `1.3.0` and the `v1.3.0` tag exists, so a merge today publishes
`:latest` and nothing else. The first release cut through CI has to **bump past
1.3.0**, or the tag would overwrite a published image with different code.

Separately: `main` has no `.github/workflows/`, so `docker-publish.yml` has never
been registered and `:dev` is built by hand. The first merge to `main` is what
registers the trigger — which means that merge may itself publish nothing.
Verify Docker Hub afterwards. See "The publish bootstrap" in
`docs/development-workflow.md`.

### 7. `error_page 500 … /50x.html` with no `50x.html` — **DONE, 2026-08-25**

Fixed, and it was worse than this entry recorded. The location rooted at
`/usr/share/nginx/html`, which ships only the distro's own index, so a 5xx fell
through to `error_page 404 /index.html` and returned **HTTP 404 with 186,727
bytes — the entire application shell**. A user whose backend had failed saw a
working-looking app with no data, indistinguishable from an empty library.

Now `web/50x.html`, rooted at `/app/web`, `internal`, self-contained, and not
precached by the service worker. Measured after: HTTP 500, 4,538 bytes. Four
tests in `tests/test_cache_policy.py` keep the directive and the file together.

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
