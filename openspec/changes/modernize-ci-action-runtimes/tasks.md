## 1. Bump the actions in `ci.yml`

- [x] 1.1 `actions/checkout@v4` → `@v7` on **both** lines (the `quality` job and the `docker` job). Two lines, one action — the second is the one that gets missed.
- [x] 1.2 `actions/setup-python@v5` → `@v7`. Leave `python-version: '3.13'` alone.
- [x] 1.3 `actions/setup-node@v4` → `@v7`. Keep `cache: npm` explicit — v5 added automatic caching and v6 narrowed it, and the explicit input is what makes this bump a no-op rather than something to reason about.
- [x] 1.4 `node-version: '20'` → `'24'`. This is the toolchain's Node, not the runner's; it silences nothing in the deprecation warning and is being changed for its own reason.

## 2. Bump the actions in `docker-publish.yml`

- [x] 2.1 `actions/checkout@v4` → `@v7`. Leave `ref`, `fetch-depth: 0` and `fetch-tags: true` exactly as they are — the release detection reads tags from this checkout.
- [x] 2.2 `docker/setup-qemu-action@v3` → `@v4` and `docker/setup-buildx-action@v3` → `@v4`.
- [x] 2.3 `docker/login-action@v3` → `@v4`. Secrets references unchanged.
- [x] 2.4 `docker/metadata-action@v5` → `@v6`. The four `tags:` expressions and `context: git` are untouched — they are the branch-to-tag mapping and are not part of this change.
- [x] 2.5 `docker/build-push-action@v6` → `@v7`. `platforms`, `cache-from`/`cache-to` and `push: true` unchanged.
- [x] 2.6 `softprops/action-gh-release@v2` → `@v3`. It was **not** in the reported warning only because its step is conditional and did not run; it is on `node20` like the rest.
- [x] 2.7 Re-read the diff for this file and confirm it contains version numbers and nothing else — no trigger, `if:`, `concurrency`, `permissions`, or tag-expression change.

## 3. Pin the version set with a test

- [x] 3.1 Add `tests/test_workflow_actions.py`. Load every `*.yml` in `.github/workflows/` with `yaml.safe_load` (already a CI dependency, and already how `test_compose_surface.py` reads YAML) — not a regex over `uses:` lines, which reads commented-out steps as live.
- [x] 3.2 Walk `jobs.*.steps[].uses` and collect `action -> version`. Assert the collected mapping equals an expected table **exactly**, in both directions, so an unnamed action fails and an unused table entry fails.
- [x] 3.3 Make the failure message name the action and the version found, so a red test is readable without opening the workflow.
- [x] 3.4 Comment the test with what it does **not** do: it cannot tell whether a pinned version is still current, because that needs the network and a gate that needs the network fails on GitHub's bad days instead of on the repo's. Say that an intentional bump is expected to fail it and the fix is to move the table in the same commit — never to relax the assertion.

## 4. Verify locally

- [x] 4.1 `make lint` — the workflow files are covered by Prettier; a reflowed YAML value fails the gate rather than CI.
- [x] 4.2 `make test` — the new test passes against the bumped files, and passes for the right reason. Temporarily change one table entry, confirm it fails, and change it back. A table asserted against itself passes whatever the code does.
- [x] 4.3 Do **not** run `make docker-smoke`. Neither `Dockerfile` nor `config/` is touched; running it proves nothing about this change.

## 5. Confirm the pipeline, on `dev`

- [x] 5.1 Push to `dev` and open the `CI` run. Both jobs green, **and** no step reports being forced onto a newer Node runtime — the absence of the warning is the deliverable, so read the log rather than the check mark. **Done:** run `33089217779`, both jobs green, zero matches for the warning. Grepped the previous run (`33087335808`) as a control, which returns it in *both* jobs — confirming the grep works and that `ci.yml` had been warning in its own log all along.
- [x] 5.2 Open the `Publish Docker image` run that follows and confirm it is green and pushed `:dev`. **Done:** run `33089273842` green, `:dev` pushed at 15:42:58Z for amd64 and arm64. **But the premise of this task was wrong:** it is *not* an exercise of the bumped workflow. The run executed `actions/checkout@v4` and emitted the original six-action warning, because `workflow_run` reads the workflow file from the default branch. `main` still holds the old pins, so every version bump in `docker-publish.yml` is inert until the merge.
- [x] 5.3 Note in the PR what is still unexercised, which is **more than anticipated**. Not just `action-gh-release@v3` behind its `if:` — the whole of `docker-publish.yml`, for the `workflow_run` reason in 5.2. The post-merge publish run is the first exercise of any of it, and is the one to watch.

## 6. Docs

- [x] 6.1 Confirm no doc change is needed and say so rather than inventing one. `docs/development-workflow.md` states Node **18+** as a floor for local development, which 24 satisfies; its Node 16 warning is unaffected. `CLAUDE.md`'s "Node 18+ with `npm ci`" is the same floor. Nothing user-facing changed — no file a user holds was edited, and the published image is byte-identical in composition.
