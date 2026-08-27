## ADDED Requirements

### Requirement: A snapshot is replaced whole, or not at all

A fetcher SHALL publish `movies.json` and `tvshows.json` by writing each to a
temporary file in the same directory and renaming it into place after the run has
succeeded. It MUST NOT delete, truncate, or write in place over a snapshot file
that a reader may be serving.

Both fetchers are bound by this identically. Emby and Jellyfin share one fetcher,
so a discipline applied to Plex and not to that one gives two of the three
servers a behaviour the third does not have.

The snapshot is served by nginx to a running frontend, so every instant of a
fetch run is an instant a reader may arrive. The previous implementation deleted
both files as its **first** act and wrote the replacements as its last, which
meant the files were absent for the entire duration of an import — minutes, on a
large library. The page shell still loaded, so the viewer did not see a site that
was down; they saw one that reported `Failed to load movie data`. That is worse
than an outage, because nothing about it says the cause is temporary.

A rename onto an existing path on the same filesystem is indivisible: a reader
holds either the old file or the new one and never observes a state between them.
Writing the temp file into the same directory is what guarantees the same
filesystem, and therefore what makes the rename atomic rather than a copy.

Ordering matters between the two files as much as within each one. They are read
as a pair by a single page load, so a window in which `movies.json` is the new
snapshot and `tvshows.json` is still the old one shows the viewer two different
points in time. Neither file SHALL be renamed into place until both have been
written in full, and the two renames SHALL be consecutive with no other work
between them.

Two renames are not one atomic operation, and this requirement does not pretend
otherwise. It bounds the disagreement window to the gap between two system calls
instead of to the duration of a fetch — from minutes to microseconds. Closing it
completely would mean swapping the server directory itself, which is not
available: that directory also holds `posters/`, `backdrops/` and
`checksums.pkl`, none of which are rebuilt by a run, and swapping it would
discard the artwork cache this project takes care to preserve.

#### Scenario: A reader during a run sees the previous snapshot

- **WHEN** a fetch run is in progress and a request is made for
  `/data/<server>/movies.json`
- **THEN** the request SHALL be answered with the complete snapshot from the
  previous successful run, and SHALL NOT return a 404 or a partial body

#### Scenario: Neither file is published until both are written

- **WHEN** a fetch run has written its new `movies.json` but has not yet finished
  writing its new `tvshows.json`
- **THEN** both published files SHALL still be the previous run's

#### Scenario: The first run has nothing to preserve

- **WHEN** a fetch run completes successfully in a server directory that held no
  previous snapshot
- **THEN** `movies.json` and `tvshows.json` SHALL exist and SHALL be complete

#### Scenario: Every fetcher is bound by this

- **WHEN** a snapshot is published for Plex, for Jellyfin, or for Emby
- **THEN** it SHALL be published by the same temporary-file-and-rename
  discipline

### Requirement: A failed fetch leaves the previous snapshot intact

A fetch run that does not complete SHALL leave the previous snapshot exactly as
it found it. A fetcher MUST NOT reach a state in which it has discarded the
previous snapshot and has not yet produced a replacement.

This is a consequence of the requirement above rather than a separate mechanism,
and it is stated separately because it is the failure that reached users. A
fetcher gives up early on a great many conditions — an unreachable server, a
rejected token, a user lookup that returns nothing — and under the previous
delete-first ordering every one of those paths ran **after** the files were
already gone. A media server that happened to be restarting when cron fired left
the viewer with an empty library until a later run succeeded, up to a full cron
interval later.

An empty library is indistinguishable from a correctly configured server with no
media. This project refuses that ambiguity everywhere else it appears; a failed
refresh must not be the one place it is manufactured.

#### Scenario: The server cannot be reached

- **WHEN** a fetch run cannot reach its media server
- **THEN** `movies.json` and `tvshows.json` SHALL still hold the previous
  successful run's snapshot, and the failure SHALL be reported on stdout

#### Scenario: The run fails partway through

- **WHEN** a fetch run fails after fetching some items but before publishing
- **THEN** no partial snapshot SHALL be visible, and the previous snapshot SHALL
  remain the one that is served

#### Scenario: A failure on one server does not affect another

- **WHEN** a Jellyfin fetch fails and a Plex fetch succeeds
- **THEN** the Plex snapshot SHALL be updated and the Jellyfin snapshot SHALL be
  unchanged
