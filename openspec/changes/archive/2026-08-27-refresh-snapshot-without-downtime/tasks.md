## 1. Publish the snapshot atomically

- [x] 1.1 Add `scripts/snapshot_io.py` — a shared atomic publisher modelled on
      `glimpse_config.py::_write_json` (`:285`): temp file in the **target's own
      directory**, write, `flush`, `os.fsync`, `chmod(0o644)`, then
      `Path.replace()`. Unlink every temp on any exception. Shared rather than
      copied into each fetcher: two copies of a subtle routine in the two files
      this project has already let drift is the wrong shape here, and a new file
      is outside the fetchers' ruff carve-out so it must pass the gate. Comment
      the two details that bite — same directory or the rename becomes a
      cross-filesystem copy and stops being atomic, and the mode must be set on
      the temp because permissions travel with the rename and nginx answers 403
      to a file it cannot read.
- [x] 1.2 Give it a `publish_json(pairs, ...)` entry point that writes **every**
      temp first and renames them only afterwards, back to back with nothing in
      between. A page load reads `movies.json` and `tvshows.json` as a pair, so
      publishing one early shows the viewer two points in time. Change the save
      block in `plex_data_fetcher.py` (`:437-450`) to call it.
- [x] 1.3 Delete `clean_existing_data()` (`:85-96`) and its call site (`:362`).
      Removed rather than relocated: there is no point in a run at which
      deleting the previous snapshot is correct.
- [x] 1.4 Move `set_permissions()` off the final path and onto the temp path, or
      fold it into 1.1. Applied after the rename it is too late; applied to the
      final path it is applied to a file that no longer needs it.
- [x] 1.5 Use a fixed temp name per target rather than a random one, so a killed
      run leaves at most two inert files per server instead of accumulating
      them. They sit in a directory nginx serves, so they must be predictable
      and self-replacing.
- [x] 1.6 Apply 1.1–1.5 identically in `scripts/jellyfin_data_fetcher.py`
      (`clean_existing_data` at `:85`, called at `:384`). This is two files
      covering three servers — Emby is fetched by the Jellyfin fetcher. A fix
      landing in one and not the other is the bug this project has already
      shipped once.
- [x] 1.7 Confirm the early-return failure paths in both fetchers now leave the
      previous snapshot intact — the Jellyfin `if not user_id: return` (`:388`)
      is the one that reached users. No restore path should be added: the safety
      comes from never having deleted anything.
- [x] 1.8 Make `fetch_and_save_data()` return a bool and `main()` exit non-zero
      on failure, in both fetchers. **Found during implementation and it blocks
      group 3:** `main()` currently ignores the return value, so the process
      exits 0 whether the fetch worked or not, and the entrypoint's existing
      "initial fetch failed" warning has never once fired. Without this the
      entrypoint cannot tell success from failure and would record a fingerprint
      after a failed fetch — the exact defect 3.3 exists to prevent. See D9.
- [x] 1.9 Count only the existing give-up paths as failure. A library that is
      legitimately empty is a **success** — it is a real state of a real install,
      and failing it would manufacture the ambiguity this project is careful
      about everywhere else. A run where individual items failed to process stays
      a success too, matching what the fetchers already tolerate.

## 2. Compute the fingerprint

- [x] 2.1 In `scripts/glimpse_config.py`, add `Server.fingerprint()` returning a
      hex SHA-256 over exactly `url`, `token`, and the normalised
      `exclude_libraries`. Nothing else on `Server` or `Resolved` contributes.
- [x] 2.2 Hash `json.dumps` of a list, never a delimiter join. A URL and an
      exclusion list both admit commas and spaces, so a joined string collides —
      and a collision here means a fingerprint that matches when the settings
      differ, silently withholding the user's change. Comment it; this repo made
      the same call for `renderSignature()` for the same reason.
- [x] 2.3 Normalise the exclusion list exactly the way the fetchers parse it —
      strip each entry, drop empties, sort — so the fingerprint describes the
      exclusion's effect rather than its spelling. Reordering `A,B` to `B,A`
      must not cost a re-import. Normalising differently from the fetcher would
      be worse than not normalising at all.
- [x] 2.4 Add `--fingerprint-dir <path>` to `main()`, alongside the existing
      `--output` and `--crontab`. It writes one file per configured server,
      named by server id, each containing that server's hash and nothing else.
- [x] 2.5 Keep resolution pure. `fingerprint()` is a method on the dataclass and
      does no I/O; only `main()` writes.

## 3. Decide at boot

- [x] 3.1 In `config/entrypoint.sh`, pass `--fingerprint-dir /run/glimpse/fingerprints`
      on the existing `glimpse_config.py` invocation (`:77`), creating the
      directory first. `/run` is deliberate — the expected fingerprint is derived
      from the current environment every boot and must not persist. Only the
      recorded one, under `/app/data`, survives a restart.
- [x] 3.2 Add a per-server decision to `run_initial_fetch`: skip when
      `cmp -s "$FP_DIR/$id" "$DATA_DIR/$id/fingerprint"` succeeds. `cmp` treats a
      missing recorded file as a difference, so "never imported" and "settings
      changed" take the same branch with no extra condition to get wrong.
- [x] 3.3 On a successful fetch, and **only** on a successful fetch, copy
      `$FP_DIR/$id` to `$DATA_DIR/$id/fingerprint`. `run_initial_fetch` already
      separates success from failure — it warns and continues so one bad server
      does not stop the others. Writing it any earlier asserts the data on disk
      came from the current settings, which a subsequent failure makes false, and
      the next restart then skips and withholds the change with nothing
      reporting it.
- [x] 3.4 Print what was decided per server — skipped, or fetching and why
      (no recorded fingerprint, or settings changed). `print()` is the fetchers'
      interface and `docker logs` is how a user watches a boot; a silent skip is
      indistinguishable from a fetch that did nothing.
- [x] 3.5 Leave `exec /usr/bin/supervisord` exactly where it is, on the last
      line. It does not need to move: once a restart skips its fetches there is
      nothing slow ahead of it. Moving it is explicitly out of scope and would
      require background-fetch machinery this change does not build.
- [x] 3.6 Confirm the crontab is untouched by all of this. `crontab()` inlines
      each server's URL, token and exclusion list as literal arguments, so a
      scheduled run never re-reads the environment and has no skip decision to
      make. Only the boot path reads or writes a fingerprint.
- [x] 3.7 Update the entrypoint's header comment. It currently says the script
      "runs an initial fetch"; it now runs one conditionally, per server.

## 4. Pin the decisions

- [x] 4.1 Add `tests/test_snapshot_publishing.py`. Assert, in **both** fetcher
      modules, that no `clean_existing_data` remains and that no snapshot path
      is opened for writing directly — the same shape as
      `tests/test_cache_policy.py`, which pins a policy by structure rather than
      by running the thing.
- [x] 4.2 Test the writer against a temp directory: a successful write replaces
      the target; an exception mid-write leaves the previous content intact and
      no temp file behind; the resulting file is mode `0644`. The permissions
      assertion is the one that matters — a correct atomic swap that nginx
      answers 403 to is invisible to every other check here.
- [x] 4.3 Test that neither snapshot is published until both are written, by
      driving a fetch whose second write raises and asserting **both** files are
      still the previous run's.
- [x] 4.4 Add `tests/test_fetch_fingerprint.py`. Assert the field set feeding
      `fingerprint()` **exactly**, in both directions, the way
      `tests/test_compose_surface.py` pins the compose surface: adding a field to
      `Server` that affects the snapshot must fail this test until someone
      decides on purpose whether it belongs in the fingerprint.
- [x] 4.5 Assert a change to each of the three inputs changes the hash; that
      identical inputs produce an identical hash; that a reordered or
      re-spaced exclusion list does **not** change it; and that the two
      ambiguous splits of a comma-bearing pair (`"a,b"`/`"c"` versus
      `"a"`/`"b,c"`) produce different hashes.
- [x] 4.6 Assert the written fingerprint file contains none of the input values —
      specifically not the token. `/app/data` is served by nginx on an
      unauthenticated app, so this is the assertion standing between the design
      and a credential download.
- [x] 4.7 Assert `--fingerprint-dir` writes one file per **configured** server
      and none for an unconfigured one.
- [x] 4.8 Run `make test`. Then break each new assertion deliberately — restore
      an up-front delete, drop the `chmod`, swap the JSON hash for a join — and
      confirm each fails. A test that has never failed has not been shown to
      work.

## 5. Verify the image

- [x] 5.1 Run `make docker-smoke`. `config/entrypoint.sh` changed, so CI cannot
      cover this before a push.
- [x] 5.2 Extend the smoke test to fetch a snapshot path **over HTTP** after
      boot and assert a 200 with valid JSON, not merely that the file exists.
      File-existence checks pass for a file nginx cannot read.
- [x] 5.3 By hand: boot with data present and unchanged settings, and confirm
      the log says every server was skipped and the site serves the existing
      library within seconds.
- [x] 5.4 By hand: change `PLEX_EXCLUDE_LIBRARIES`, restart, and confirm only
      Plex re-imports and the exclusion has taken effect. Then restart again
      unchanged and confirm it skips.
- [x] 5.5 By hand: point a server at an unreachable URL and restart. Confirm the
      snapshot survives, no fingerprint is recorded, and a further restart
      retries rather than skipping.
- [x] 5.6 By hand: request `movies.json` repeatedly while a fetch runs, and
      confirm every response is a 200 with complete JSON. This is the reported
      defect; it must be checked during a run, not after one.
- [x] 5.7 Confirm the artwork cache survived all of the above — `checksums.pkl`
      intact and no full re-download. Nothing in this change should touch it,
      which is exactly why it is worth confirming.

## 6. Gates and docs

- [x] 6.1 Run `make lint` and `make fmt`; both must pass.
- [x] 6.2 Run `make test`; it must pass.
- [x] 6.3 Update `docs/docker.md`. The boot sequence description (`:59`) says the
      entrypoint runs an initial fetch unconditionally. Document the per-server
      skip, and document deleting `/app/data/<server>/fingerprint` as the
      supported way to force a re-import — it replaces "restart the container",
      and it is per server rather than all of them.
- [x] 6.4 Check `README.md` for anything that promises a restart re-imports. If
      nothing is stale, say so explicitly in the commit rather than inventing
      edits.
- [x] 6.5 Weigh whether `CLAUDE.md` should record the delete-first defect. Its
      conventions list already carries this project's silent-failure lessons, and
      "a refresh never deletes what it is replacing" is the same class as the
      cache-policy and config-fallback rules already there.
- [x] 6.6 Confirm `docker-compose.yml` is byte-identical and
      `tests/test_compose_surface.py` passes untouched. This change adds no
      environment variable by design; if that test fails, something in the
      implementation went the wrong way.
