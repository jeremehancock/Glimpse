#!/bin/bash
#
# Container entrypoint.
#
# This script does four things: migrate an old data layout, generate the two
# files the frontend reads, run an initial fetch for each server that needs one,
# and start supervisord.
#
# "that needs one" is the whole of the boot-time logic. Each server records a
# fingerprint of the settings that produced its last SUCCESSFUL import; if the
# current settings still hash to that, its fetch is skipped and the site comes
# up in seconds on the snapshot already on the volume. A restart used to re-import
# every library unconditionally, and because supervisord starts last, the
# container refused connections for the whole of it.
#
# What it deliberately does NOT do is edit any file under /app/web. The previous
# version of this script was 1,915 lines, most of it `sed` rewriting index.html
# on every boot — injecting per-server themes, retitling the page, repointing
# every data path, copying the page into /plex/, /jellyfin/ and /emby/, and
# swapping a toggle for a dropdown. It then ran cleanup_duplicate_server_content()
# and fix_corrupted_files() to repair the damage it did to its own output.
#
# The rule that replaced it is: GENERATE, NEVER MUTATE. config.json and
# manifest.json are written whole, from templates owned by glimpse_config.py.
# index.html, sw.js, offline.html and images/ are authored and read-only at
# runtime. If something seems to need editing them here, it is a spec change to
# `application-shell`, not a change to this file.
#
# See CLAUDE.md and docs/docker.md.

set -euo pipefail

WEB_DIR=/app/web
DATA_DIR=/app/data
CRON_FILE=/etc/cron.d/media-cron
# The fingerprints of the CURRENT environment, one file per configured server.
# Under /run on purpose: these are derived fresh on every boot and must not
# survive one. Only the recorded fingerprints, under $DATA_DIR, persist.
FINGERPRINT_DIR=/run/glimpse/fingerprints

# ---------------------------------------------------------------------------
# Migrate the pre-multi-server data layout
# ---------------------------------------------------------------------------
#
# Before multi-server support, Plex data lived directly in /app/data. Moving it
# rather than re-fetching preserves checksums.pkl, and with it the whole point of
# the checksum cache: without this, the first run after upgrading re-downloads
# every poster and backdrop in the library.
migrate_existing_data() {
    if [ ! -f "$DATA_DIR/movies.json" ] &&
        [ ! -f "$DATA_DIR/tvshows.json" ] &&
        [ ! -d "$DATA_DIR/posters" ] &&
        [ ! -d "$DATA_DIR/backdrops" ]; then
        echo "No legacy data layout found; nothing to migrate."
        return
    fi

    echo "Found pre-multi-server data in $DATA_DIR — migrating to $DATA_DIR/plex/"
    mkdir -p "$DATA_DIR/plex"

    # checksums.pkl is included on purpose. Leaving it behind would silently
    # trigger a full re-download of every image on the next scheduled run.
    for item in movies.json tvshows.json checksums.pkl posters backdrops; do
        if [ -e "$DATA_DIR/$item" ]; then
            echo "  moving $item"
            mv "$DATA_DIR/$item" "$DATA_DIR/plex/"
        fi
    done

    chown -R www-data:www-data "$DATA_DIR/plex/" 2>/dev/null ||
        echo "Note: could not set ownership on migrated files"
    echo "Migration complete."
}

# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

migrate_existing_data

mkdir -p "$DATA_DIR/plex" "$DATA_DIR/jellyfin" "$DATA_DIR/emby"

# Resolve the environment and write config.json, manifest.json, and the crontab.
# All three come from one place so that "which servers are configured" has a
# single implementation — the previous script answered that question in three
# places and they drifted.
#
# A failure here is fatal: the app cannot start without knowing what it is
# configured with, and a container that serves a misconfigured library looks
# exactly like one that is working.
echo "Resolving configuration..."
mkdir -p "$FINGERPRINT_DIR"
if ! python3 /app/scripts/glimpse_config.py \
    --output "$WEB_DIR" --crontab "$CRON_FILE" --fingerprint-dir "$FINGERPRINT_DIR"; then
    echo "Error: could not resolve configuration. Refusing to start." >&2
    exit 1
fi

chmod 0644 "$CRON_FILE"
crontab "$CRON_FILE"
echo "Installed $(grep -c data_fetcher "$CRON_FILE") scheduled fetch(es)."

# nginx serves /data/ through an alias, but the regex location for image
# extensions is matched against the filesystem root as well. This symlink keeps
# an image request resolving either way. See config/nginx.conf.
ln -sfn "$DATA_DIR" "$WEB_DIR/data"

# ---------------------------------------------------------------------------
# Initial fetch
# ---------------------------------------------------------------------------
#
# Runs before supervisord, so a first install's first page load has data rather
# than an empty library. That ordering is unchanged and does not need to change:
# a server whose settings are unchanged is skipped outright, so a restart has
# nothing slow left ahead of supervisord.
#
# The fetchers are individually non-fatal — one unreachable server must not stop
# the others, or a single bad token takes down a working install.

# Whether $1's boot fetch is needed. True when its recorded fingerprint is
# missing or differs from the current one.
#
# `cmp` treats a missing file as a difference, so "never imported" and "settings
# changed" arrive at the same answer through the same call. There is deliberately
# no separate existence test: a second condition is a second thing to get wrong,
# and the one it would replace is already correct.
# Sets FETCH_REASON rather than printing, so the caller can name the reason on
# the same line as the action it is taking.
FETCH_REASON=""
needs_fetch() {
    local server_id=$1
    local current="$FINGERPRINT_DIR/$server_id"
    local recorded="$DATA_DIR/$server_id/fingerprint"

    if [ ! -f "$recorded" ]; then
        FETCH_REASON="no previous import recorded"
        return 0
    fi
    if ! cmp -s "$current" "$recorded"; then
        FETCH_REASON="settings changed since the last import"
        return 0
    fi
    return 1
}

run_initial_fetch() {
    local server_id=$1 fetcher=$2 url_var=$3 token_var=$4 exclude_var=$5
    local url=${!url_var:-} token=${!token_var:-}

    [ -n "$url" ] && [ -n "$token" ] || return 0

    if ! needs_fetch "$server_id"; then
        echo "Skipping $server_id fetch: settings unchanged since its last import."
        return 0
    fi

    echo "Fetching $server_id data ($FETCH_REASON)..."
    if ! env "$exclude_var=${!exclude_var:-}" \
        python3 "/app/scripts/${fetcher}_data_fetcher.py" \
        --url "$url" --token "$token" --output "$DATA_DIR/$server_id"; then
        echo "Warning: initial $server_id fetch failed. The scheduled run will retry." >&2
        # Deliberately no fingerprint written. Recording one here would assert
        # that the data on disk came from these settings; the next restart would
        # believe it, skip, and withhold the user's change with nothing on screen
        # or in the log to say so.
        return 0
    fi

    # Only now. The fingerprint describes a completed import, not an attempted one.
    cp "$FINGERPRINT_DIR/$server_id" "$DATA_DIR/$server_id/fingerprint"
    echo "Recorded $server_id settings fingerprint."
}

echo "Running initial data fetch..."
run_initial_fetch plex plex PLEX_URL PLEX_TOKEN PLEX_EXCLUDE_LIBRARIES
run_initial_fetch jellyfin jellyfin JELLYFIN_URL JELLYFIN_TOKEN JELLYFIN_EXCLUDE_LIBRARIES
# Emby uses the Jellyfin fetcher — the APIs are compatible.
run_initial_fetch emby jellyfin EMBY_URL EMBY_TOKEN EMBY_EXCLUDE_LIBRARIES

chown -R www-data:www-data "$DATA_DIR" 2>/dev/null || true
chown -R www-data:www-data "$WEB_DIR" 2>/dev/null || true

echo "Startup complete. Handing off to supervisord."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
