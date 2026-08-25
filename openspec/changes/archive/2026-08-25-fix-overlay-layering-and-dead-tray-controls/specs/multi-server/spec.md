## ADDED Requirements

### Requirement: Every copy of the server switcher is labelled from configuration

The server switcher SHALL be labelled from `config.json` wherever it appears,
including copies inside an overlay that is relocated in the document when the
page initialises.

An unlabelled copy SHALL NOT be shown. The authored markup carries a placeholder
label, and a copy that never reaches the labelling pass presents that placeholder
as though it were a real choice — naming no server, and reading as a working
control that has simply been ignored.

Where exactly one other server is configured, every copy SHALL name that server.
Where more than one is configured, every copy SHALL open the switcher overlay.
Where none is configured, every copy SHALL be removed.

#### Scenario: The tray's switcher names the destination server

- **WHEN** two servers are configured and the user opens the Actions tray
- **THEN** the server control SHALL name the other configured server rather than
  a generic label

#### Scenario: The tray's switcher performs the switch

- **WHEN** two servers are configured and the user taps the server control in
  the Actions tray
- **THEN** the browser SHALL navigate to the other server's route

#### Scenario: The tray's switcher opens the chooser with three servers

- **WHEN** three servers are configured and the user taps the server control in
  the Actions tray
- **THEN** the server switcher overlay SHALL open listing both other servers

#### Scenario: A single server leaves no switcher in the tray

- **WHEN** one server is configured and the user opens the Actions tray
- **THEN** the tray SHALL hold no server control
