## ADDED Requirements

### Requirement: A rebuilt static asset reaches an installed client

The service worker SHALL serve the application's stylesheets and scripts from the
network when the network is reachable, falling back to its cache when it is not.

It SHALL NOT serve a cached stylesheet or script in preference to an available
network copy. The application shell is already fetched network-first, so a
cache-first rule for the assets it loads pairs new markup with old behavior
indefinitely — and the resulting faults present as feature bugs in code that is
correct, which is the most expensive kind of report to answer.

The server SHALL NOT instruct the browser to hold those files beyond
revalidation. Their filenames carry no content hash and never will — nothing
under the web root is built or bundled, so a changed file keeps its URL. A
long-lived `max-age` therefore defeats the network-first strategy above, because
the worker's own fetch consults the HTTP cache. Neither layer is wrong on its
own, which is what makes the pair hard to see.

The service worker script itself SHALL always be revalidated. It is the code that
decides what every other response may serve, so a held copy freezes the caching
policy of the whole application at whatever it was — and withholds the upgrade
that would correct it.

The install control offered inside the Actions tray SHALL prompt for
installation, in the same way as the header's copy.

#### Scenario: An upgraded container serves upgraded assets

- **WHEN** a client that has previously loaded the app requests it again after
  the container has been rebuilt with changed stylesheets or scripts
- **THEN** the client SHALL receive the rebuilt stylesheets and scripts

#### Scenario: The app still runs offline

- **WHEN** the network is unreachable and the client has loaded the app before
- **THEN** the app SHALL load from cache, including its vendored Alpine build,
  the overlay stylesheet and the overlay script

#### Scenario: Assets are revalidated rather than held

- **WHEN** the app's stylesheets, scripts or the service worker script are
  requested
- **THEN** the response SHALL direct the browser to revalidate rather than to
  reuse the file for a fixed period

#### Scenario: Genuinely static files keep their long cache

- **WHEN** an image shipped in the image, or artwork under the data volume, is
  requested
- **THEN** it SHALL keep its long-lived cache directive

#### Scenario: A cache from a previous scheme is discarded

- **WHEN** the service worker activates after the caching scheme has changed
- **THEN** caches belonging to the previous scheme SHALL be deleted

#### Scenario: Installing from the Actions tray

- **WHEN** installation is available and the user taps the install control
  inside the Actions tray
- **THEN** the installation prompt SHALL be shown
