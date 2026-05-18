 d# 🎬 Glimpse Media Viewer

A sleek, responsive web application for browsing and viewing your Plex, Jellyfin, or Emby media library content. This dockerized solution fetches metadata and artwork from your media server and presents it in an elegant, user-friendly interface with support for multiple media servers.

![Glimpse Media Viewer Plex Main](https://raw.githubusercontent.com/jeremehancock/Glimpse/main/assets/screenshot-main-plex-2.png)

![Glimpse Media Viewer Plex Details](https://raw.githubusercontent.com/jeremehancock/Glimpse/main/assets/screenshot-details-plex-2.png)

![Glimpse Media Viewer Jellyfin Main](https://raw.githubusercontent.com/jeremehancock/Glimpse/main/assets/screenshot-main-jellyfin-2.png)

![Glimpse Media Viewer Jellyfin Details](https://raw.githubusercontent.com/jeremehancock/Glimpse/main/assets/screenshot-details-jellyfin-2.png)

![Glimpse Media Viewer Emby Main](https://raw.githubusercontent.com/jeremehancock/Glimpse/main/assets/screenshot-main-emby-2.png)

![Glimpse Media Viewer Emby Details](https://raw.githubusercontent.com/jeremehancock/Glimpse/main/assets/screenshot-details-emby-2.png)

## ✨ Features

- **Modern Interface**: Clean, responsive design that works on mobile and desktop
- **Multi-Server Support**: Connect to Plex, Jellyfin, Emby, or multiple servers simultaneously
- **Media Browsing**: View your Movies and TV Shows with poster art
- **Search Capability**: Quickly find content across your libraries
- **Detailed View**: See cast information, genres, and descriptions
- **Watch Movie Trailers**: Preview content directly from the interface
- **Random Content Selection**: "Roll the Dice" feature for discovering random Movies or TV Shows
- **Genre Filters**: Easily filter media by genre
- **Sort A–Z / Z–A**: Alphabetical sorting
- **Sort by Date Added (Ascending / Descending)**: Sort media by when it was added
- **Server Toggle**: Switch between multiple configured servers with one click
- **Automatic Theme Adaptation**: Interface automatically adapts to match your primary server
- **Library Exclusion**: Selectively exclude specific libraries from being displayed
- **MD5 Checksum Verification**: Only downloads images when they've changed
- **Dockerized**: Easy deployment with Docker and Docker Compose
- **Customizable**: Configure update schedule, app title, and more
- **Installable as PWA**: Access your media library like a native app on any device

## ❤️ Support this project

[![Donate](https://raw.githubusercontent.com/jeremehancock/Glimpse/main/assets/donate-button.png)](https://www.buymeacoffee.com/jeremehancock)

## 🔧 Prerequisites

- Docker and Docker Compose installed on your host system
- A running Plex Media Server, Jellyfin Media Server, and/or Emby Media Server
- Authentication tokens for your media server(s)
- Basic knowledge of Docker and containerization

## 🚀 Installation

### 1: Grab Docker Compose

Create a directory for your data

```bash
mkdir -p Glimpse/data
```

Create a docker-compose.yml file

```bash
curl -o Glimpse/docker-compose.yml https://raw.githubusercontent.com/jeremehancock/Glimpse/main/docker-compose.yml
```

Change to Glimpse directory

```bash
cd Glimpse
```

### 2. Configure Docker Compose

Edit `docker-compose.yml` to set your media server details. You can configure any combination of Plex, Jellyfin, and/or Emby servers:

#### Plex Server Configuration

```yaml
environment:
  - PRIMARY_SERVER=plex
  - PLEX_URL=http://your-plex-server:32400
  - PLEX_TOKEN=your-plex-token
  - PLEX_EXCLUDE_LIBRARIES= # Optional: Comma-separated list of library names or IDs to exclude
  - CRON_SCHEDULE=0 */6 * * * # Update every 6 hours
  - TZ=UTC # Your timezone
  - APP_TITLE=Glimpse # Set app title
  - SORT_BY_DATE_ADDED=false # Sort by date instead of title
```

#### Jellyfin Server Configuration

```yaml
environment:
  - PRIMARY_SERVER=jellyfin
  - JELLYFIN_URL=http://your-jellyfin-server:8096
  - JELLYFIN_TOKEN=your-jellyfin-api-token
  - JELLYFIN_EXCLUDE_LIBRARIES= # Optional: Comma-separated list of library names or IDs to exclude
  - CRON_SCHEDULE=0 */6 * * * # Update every 6 hours
  - TZ=UTC # Your timezone
  - APP_TITLE=Glimpse # Set app title
  - SORT_BY_DATE_ADDED=false # Sort by date instead of title
```

#### Emby Server Configuration

```yaml
environment:
  - PRIMARY_SERVER=emby
  - EMBY_URL=http://your-emby-server:8096
  - EMBY_TOKEN=your-emby-api-token
  - EMBY_EXCLUDE_LIBRARIES= # Optional: Comma-separated list of library names or IDs to exclude
  - CRON_SCHEDULE=0 */6 * * * # Update every 6 hours
  - TZ=UTC # Your timezone
  - APP_TITLE=Glimpse # Set app title
  - SORT_BY_DATE_ADDED=false # Sort by date instead of title
```

#### Multi-Server Configuration

To configure multiple servers, simply include the environment variables for each server you want to use. For example, to use both Plex and Jellyfin:

```yaml
environment:
  - PRIMARY_SERVER=plex # Which server to show by default
  - PLEX_URL=http://your-plex-server:32400
  - PLEX_TOKEN=your-plex-token
  - PLEX_EXCLUDE_LIBRARIES=Adult Movies,Personal Collection
  - JELLYFIN_URL=http://your-jellyfin-server:8096
  - JELLYFIN_TOKEN=your-jellyfin-api-token
  - JELLYFIN_EXCLUDE_LIBRARIES=XXX Content,Private Shows
  - CRON_SCHEDULE=0 */6 * * * # Update every 6 hours
  - TZ=UTC # Your timezone
  - APP_TITLE=Glimpse # Set app title
  - SORT_BY_DATE_ADDED=false # Sort by date instead of title
```

### 3. Start the Container

```bash
docker-compose up -d
```

### 4. Access the Web Interface

Open your browser and navigate to:

```
http://your-server:9090
```

## ⚙️ Configuration Options

### Environment Variables

| Variable                     | Description                               | Default                       | Required          |
| ---------------------------- | ----------------------------------------- | ----------------------------- | ----------------- |
| `PRIMARY_SERVER`             | Which server to show by default           | `plex`                        | No                |
| `PLEX_URL`                   | URL of your Plex server                   | _None_                        | If using Plex     |
| `PLEX_TOKEN`                 | Authentication token for Plex             | _None_                        | If using Plex     |
| `PLEX_EXCLUDE_LIBRARIES`     | Libraries to exclude from Plex            | _None_                        | No                |
| `JELLYFIN_URL`               | URL of your Jellyfin server               | _None_                        | If using Jellyfin |
| `JELLYFIN_TOKEN`             | API token for Jellyfin                    | _None_                        | If using Jellyfin |
| `JELLYFIN_EXCLUDE_LIBRARIES` | Libraries to exclude from Jellyfin        | _None_                        | No                |
| `EMBY_URL`                   | URL of your Emby server                   | _None_                        | If using Emby     |
| `EMBY_TOKEN`                 | API token for Emby                        | _None_                        | If using Emby     |
| `EMBY_EXCLUDE_LIBRARIES`     | Libraries to exclude from Emby            | _None_                        | No                |
| `CRON_SCHEDULE`              | When to update data (cron format)         | `0 */6 * * *` (every 6 hours) | No                |
| `TZ`                         | Timezone for scheduled tasks              | `UTC`                         | No                |
| `APP_TITLE`                  | Custom title for the application          | `Glimpse`                     | No                |
| `SORT_BY_DATE_ADDED`         | Sort items by date added instead of title | `false`                       | No                |

### Library Exclusion

You can exclude specific libraries from being displayed in Glimpse. This is useful for:

- Adult content libraries
- Test or development libraries
- Personal or private collections
- Music libraries (if not supported)
- Any content you don't want visible in the interface

#### Configuration Format

Exclusion lists are comma-separated and can include library names or IDs:

```yaml
# Exclude by library name (case-sensitive)
- PLEX_EXCLUDE_LIBRARIES=Adult Movies,Personal Collection,Test Library

# Exclude by library ID
- JELLYFIN_EXCLUDE_LIBRARIES=1,5,12

# Mixed names and IDs
- EMBY_EXCLUDE_LIBRARIES=Adult Movies,5,Personal Collection
```

#### Finding Library Names

**Plex:**

1. Open Plex Web interface
2. Go to Settings > Libraries
3. Library names are displayed in the list

**Jellyfin:**

1. Open Jellyfin Web interface
2. Go to Dashboard > Libraries
3. Library names are shown in the list

**Emby:**

1. Open Emby Web interface
2. Go to Dashboard > Libraries
3. Library names are visible in the management interface

### Server Configuration Notes

- **Single Server**: Configure only one server's credentials. The app will automatically detect and use the available server.
- **Multi-Server**: Configure credentials for any combination of servers. The app will show a dropdown to switch between servers.
- **Primary Server**: When multiple servers are configured, `PRIMARY_SERVER` determines which one is shown by default and affects the app's theme.
- **Automatic Detection**: If `PRIMARY_SERVER` is set incorrectly or credentials are missing, the app will automatically detect and switch to an available server.
- **Clean Data Updates**: When libraries are excluded, the fetchers automatically clean existing data files to ensure excluded content doesn't persist.

### Finding Your Plex Token

You can find your Plex authentication token (X-Plex-Token) by following these steps:

1. Log in to your Plex Web App
2. Browse to any media item
3. Click the 3 dots menu and select "Get Info"
4. In the info dialog, click "View XML"
5. In the URL of the new tab, find the "X-Plex-Token=" parameter

For more detailed instructions, visit the [Plex support article](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

### Finding Your Jellyfin API Token

To get your Jellyfin API token:

1. Log in to your Jellyfin Web Interface
2. Go to **Administration** → **Dashboard**
3. Navigate to **Advanced** → **API Keys**
4. Click **+** to create a new API key
5. Give it a name (e.g., "Glimpse Media Viewer")
6. Copy the generated API key

Alternatively, you can find your API token in the Jellyfin server logs when you first authenticate, or use the Jellyfin API documentation to generate one programmatically.

### Finding Your Emby API Token

To get your Emby API token:

1. Log in to your Emby Web Interface
2. Go to **Settings** → **Advanced** → **API Keys**
3. Click **New API Key**
4. Give it a name (e.g., "Glimpse Media Viewer")
5. Copy the generated API key

Alternatively, you can create an API key through the Emby server settings or by using the Emby API documentation.

## 🏗️ Project Structure

```
Glimpse/
│
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Docker build configuration
│
├── scripts/
│   ├── plex_data_fetcher.py  # Python script to fetch Plex data
│   └── jellyfin_data_fetcher.py # Python script to fetch Jellyfin/Emby data
│
├── web/
│   ├── index.html            # Frontend web interface
│   ├── manifest.json         # PWA manifest file
│   ├── sw.js                 # Service worker for PWA functionality
│   ├── offline.html          # Offline fallback page
│   └── images/               # Icons and images
│       ├── icon.png          # Original app icon
│       ├── android-chrome-192x192.png  # App icon (192×192)
│       ├── android-chrome-512x512.png  # App icon (512×512)
│       ├── apple-touch-icon.png        # Apple Touch icon (180x180)
│       ├── favicon.ico                 # Favicon
│       ├── favicon-16x16.png           # Favicon (16x16)
│       ├── favicon-32x32.png           # Favicon (32x32)
│       ├── icons/                      # Server icons for dropdown menus
│       │   ├── plex.png                # Plex server icon
│       │   ├── jellyfin.png            # Jellyfin server icon
│       │   └── emby.png                # Emby server icon
│       ├── jellyfin/                   # Jellyfin-specific themed icons
│       │   ├── android-chrome-192x192.png
│       │   ├── android-chrome-512x512.png
│       │   └── apple-touch-icon.png
│       └── emby/                       # Emby-specific themed icons
│           ├── android-chrome-192x192.png
│           ├── android-chrome-512x512.png
│           └── apple-touch-icon.png
│
├── config/
│   ├── entrypoint.sh         # Container entrypoint script
│   ├── nginx.conf            # Nginx configuration
│   └── supervisord.conf      # Supervisor configuration
│
└── data/                     # Persistent data directory
    ├── plex/                 # Plex server data
    │   ├── movies.json       # Plex movie metadata
    │   ├── tvshows.json      # Plex TV show metadata
    │   ├── checksums.pkl     # MD5 checksums for Plex artwork
    │   ├── posters/          # Plex movie and TV show posters
    │   └── backdrops/        # Plex movie and TV show backgrounds
    ├── jellyfin/             # Jellyfin server data
    │   ├── movies.json       # Jellyfin movie metadata
    │   ├── tvshows.json      # Jellyfin TV show metadata
    │   ├── checksums.pkl     # MD5 checksums for Jellyfin artwork
    │   ├── posters/          # Jellyfin movie and TV show posters
    │   └── backdrops/        # Jellyfin movie and TV show backgrounds
    └── emby/                 # Emby server data
        ├── movies.json       # Emby movie metadata
        ├── tvshows.json      # Emby TV show metadata
        ├── checksums.pkl     # MD5 checksums for Emby artwork
        ├── posters/          # Emby movie and TV show posters
        └── backdrops/        # Emby movie and TV show backgrounds
```

## 🔄 How It Works

1. **Data Fetching**: Python scripts connect to your media server(s) using the provided tokens and fetch metadata for all movies and TV shows.
2. **Library Filtering**: Excluded libraries are automatically skipped during data fetching, and existing data files are cleaned to ensure consistency.
3. **Multi-Server Support**: When multiple servers are configured, data is fetched separately and stored in server-specific directories.
4. **Image Processing**: Media posters and backdrops are downloaded, with MD5 checksums to avoid re-downloading unchanged files.
5. **Theming**: The interface automatically adapts its theme based on your primary server (Plex orange/yellow, Jellyfin blue, or Emby green).
6. **Server Switching**: If multiple servers are configured, users can switch between them with a dropdown menu.
7. **Web Server**: Nginx serves the static web interface and the downloaded data.
8. **Scheduled Updates**: Cron runs the data fetchers on the configured schedule to keep content up-to-date.
9. **Persistence**: All data is stored in volumes mapped to your host, ensuring it persists between container restarts.

## 🌐 Customization

### Changing the Update Schedule

Modify the `CRON_SCHEDULE` environment variable in your `docker-compose.yml`:

```yaml
- CRON_SCHEDULE=0 0 * * * # Once a day at midnight
```

Common cron patterns:

- `0 */6 * * *` - Every 6 hours
- `0 0 * * *` - Daily at midnight
- `0 0 * * 0` - Weekly on Sunday
- `*/30 * * * *` - Every 30 minutes

### Changing the Port

Modify the `ports` section in `docker-compose.yml`:

```yaml
ports:
  - "9090:80" # Change to your desired port
```

### Customizing the App Title

Set the `APP_TITLE` environment variable:

```yaml
- APP_TITLE=My Movie Collection
```

### Setting the Primary Server

When multiple servers are configured, set which one appears by default:

```yaml
- PRIMARY_SERVER=jellyfin # Options: plex, jellyfin, emby
```

This affects:

- Which server's content is shown when the app first loads
- The app's color theme (Plex = orange/yellow, Jellyfin = blue, Emby = green)
- The default offline page styling

## 🔍 Troubleshooting

### Viewing Logs

View all container logs

```bash
docker-compose logs
```

Follow logs in real-time

```bash
docker-compose logs -f
```

View specific service logs

```bash
docker-compose logs glimpse-media-viewer
```

### Manual Data Update

To trigger a data update manually (using your configured exclusions):

**Plex:**

```bash
docker exec glimpse-media-viewer bash -c 'python /app/scripts/plex_data_fetcher.py --url "$PLEX_URL" --token "$PLEX_TOKEN" --output /app/data/plex'
```

**Jellyfin:**

```bash
docker exec glimpse-media-viewer bash -c 'python /app/scripts/jellyfin_data_fetcher.py --url "$JELLYFIN_URL" --token "$JELLYFIN_TOKEN" --output /app/data/jellyfin'
```

**Emby:**

```bash
docker exec glimpse-media-viewer bash -c 'python /app/scripts/jellyfin_data_fetcher.py --url "$EMBY_URL" --token "$EMBY_TOKEN" --output /app/data/emby'
```

To manually specify different exclusions for testing:

**Plex with custom exclusions:**

```bash
docker exec glimpse-media-viewer bash -c 'python /app/scripts/plex_data_fetcher.py --url "$PLEX_URL" --token "$PLEX_TOKEN" --exclude-libraries "Adult Content" "Personal Files" --output /app/data/plex'
```

**Jellyfin with custom exclusions:**

```bash
docker exec glimpse-media-viewer bash -c 'python /app/scripts/jellyfin_data_fetcher.py --url "$JELLYFIN_URL" --token "$JELLYFIN_TOKEN" --exclude-libraries "Adult Content" "Personal Files" --output /app/data/jellyfin'
```

**Emby with custom exclusions:**

```bash
docker exec glimpse-media-viewer bash -c 'python /app/scripts/jellyfin_data_fetcher.py --url "$EMBY_URL" --token "$EMBY_TOKEN" --exclude-libraries "Adult Content" "Personal Files" --output /app/data/emby'
```

### Common Issues

#### Default Nginx Page Shows Instead of the App

If you see the default Nginx welcome page, there might be an issue with the configuration:

Check if the app files are present

```bash
docker exec glimpse-media-viewer ls -la /app/web
```

Check Nginx configuration

```bash
docker exec glimpse-media-viewer cat /etc/nginx/conf.d/default.conf
```

Restart Nginx

```bash
docker exec glimpse-media-viewer nginx -s reload
```

#### Missing Images

If media images aren't displaying:

1. Check permissions on the data directory
2. Ensure the media server is accessible from the container
3. Verify your server token is valid
4. Check the container logs for fetch errors

#### Server Toggle Not Appearing

If you configured multiple servers but don't see the server dropdown:

1. Verify all server URLs and tokens are correct
2. Check the container logs for authentication errors
3. Ensure all servers are accessible from the container
4. Try restarting the container after fixing configuration

#### Wrong Theme Colors

If the app shows the wrong theme:

1. Check your `PRIMARY_SERVER` setting
2. Clear your browser cache and reload
3. Un-install and Re-install PWA

#### Library Exclusion Issues

If excluded libraries are still appearing:

1. **Check library names**: Ensure the library names match exactly (case-sensitive)
2. **Verify environment variables**: Check that the exclusion variables are set correctly
3. **Restart container**: Library exclusions are applied during data fetching, so restart after configuration changes
4. **Check logs**: Look for exclusion messages in the container logs:
   ```bash
   docker-compose logs | grep -i "excluded\|skipping"
   ```
5. **Manual data update**: Force a data refresh to apply exclusions immediately
6. **Try library IDs**: If names don't work, try using library IDs instead

#### Finding Library Information

To get detailed library information for troubleshooting exclusions, check the logs during a manual data update. The fetchers will display library names and IDs as they process each one.

## 🛠️ Advanced Usage

### Using Behind a Reverse Proxy

This application works well behind a reverse proxy like Traefik or Nginx Proxy Manager. Just expose the container port and configure your proxy accordingly.

## 🔐 Security Considerations

- Media server tokens provide access to your media servers. Keep them secure.
- All data access is read-only, so there's no risk of modifying your media libraries.
- Consider using a dedicated API token for Glimpse rather than your main user token.
- Library exclusions help keep sensitive content private and separate from your main viewing interface.

## 📝 License

This project is released under the MIT License. See the `LICENSE` file for details.

## 🤖 AI Disclosure

This project was created with the help of AI.
