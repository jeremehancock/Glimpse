# Quality gates. CI runs exactly these on every push (plus a Docker build and a
# container smoke test, which cannot run before the image exists). Keep them
# green — /ship refuses to commit through a failure.
#
#   make lint   ruff check + ruff format --check + eslint + prettier --check
#   make test   pytest
#   make fmt    apply every fix lint would ask for
#   make check  lint + test, the whole gate

.PHONY: check lint test fmt lint-py lint-js fmt-py fmt-js install docker-smoke

check: lint test

lint: lint-py lint-js

lint-py:
	ruff check .
	ruff format --check .

lint-js:
	npx --no-install eslint web --no-error-on-unmatched-pattern
	npx --no-install prettier --check .

test:
	pytest

fmt: fmt-py fmt-js

fmt-py:
	ruff check --fix .
	ruff format .

fmt-js:
	npx --no-install eslint web --fix --no-error-on-unmatched-pattern
	npx --no-install prettier --write .

# Both toolchains, for a fresh checkout.
install:
	python3 -m pip install --upgrade 'ruff' 'pytest' 'pyyaml' 'requests'
	npm ci || npm install

# Build the image and prove the container actually serves the app. CI does this
# only AFTER a push, so run it locally before touching the Dockerfile or the
# entrypoint. See docs/docker.md.
docker-smoke:
	docker build -t glimpse:smoke .
	docker rm -f glimpse-smoke 2>/dev/null || true
	docker run -d --name glimpse-smoke -p 18080:80 \
		-e PLEX_URL=http://127.0.0.1:32400 -e PLEX_TOKEN=smoke glimpse:smoke
	@for i in $$(seq 1 30); do \
		if curl -fsS http://127.0.0.1:18080/ >/dev/null 2>&1; then \
			echo "OK: nginx is serving"; break; fi; sleep 2; done
	curl -fsS http://127.0.0.1:18080/config.json | tee /dev/stderr | grep -q primaryServer
	docker rm -f glimpse-smoke
