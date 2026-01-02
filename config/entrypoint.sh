#!/bin/bash
set -e

# Set default primary server
PRIMARY_SERVER=${PRIMARY_SERVER:-"plex"}

# Smart primary server detection based on available credentials
original_primary_server="$PRIMARY_SERVER"

# Auto-detect and correct PRIMARY_SERVER based on available credentials
if [ "$PRIMARY_SERVER" = "plex" ]; then
    if [ -z "$PLEX_URL" ] || [ -z "$PLEX_TOKEN" ]; then
        if [ -n "$JELLYFIN_URL" ] && [ -n "$JELLYFIN_TOKEN" ]; then
            echo "Warning: PRIMARY_SERVER set to 'plex' but only Jellyfin credentials provided"
            echo "Auto-switching PRIMARY_SERVER to 'jellyfin'"
            PRIMARY_SERVER="jellyfin"
        elif [ -n "$EMBY_URL" ] && [ -n "$EMBY_TOKEN" ]; then
            echo "Warning: PRIMARY_SERVER set to 'plex' but only Emby credentials provided"
            echo "Auto-switching PRIMARY_SERVER to 'emby'"
            PRIMARY_SERVER="emby"
        else
            echo "Error: PRIMARY_SERVER=plex but no valid credentials provided for any server"
            exit 1
        fi
    fi
elif [ "$PRIMARY_SERVER" = "jellyfin" ]; then
    if [ -z "$JELLYFIN_URL" ] || [ -z "$JELLYFIN_TOKEN" ]; then
        if [ -n "$PLEX_URL" ] && [ -n "$PLEX_TOKEN" ]; then
            echo "Warning: PRIMARY_SERVER set to 'jellyfin' but only Plex credentials provided"
            echo "Auto-switching PRIMARY_SERVER to 'plex'"
            PRIMARY_SERVER="plex"
        elif [ -n "$EMBY_URL" ] && [ -n "$EMBY_TOKEN" ]; then
            echo "Warning: PRIMARY_SERVER set to 'jellyfin' but only Emby credentials provided"
            echo "Auto-switching PRIMARY_SERVER to 'emby'"
            PRIMARY_SERVER="emby"
        else
            echo "Error: PRIMARY_SERVER=jellyfin but no valid credentials provided for any server"
            exit 1
        fi
    fi
elif [ "$PRIMARY_SERVER" = "emby" ]; then
    if [ -z "$EMBY_URL" ] || [ -z "$EMBY_TOKEN" ]; then
        if [ -n "$PLEX_URL" ] && [ -n "$PLEX_TOKEN" ]; then
            echo "Warning: PRIMARY_SERVER set to 'emby' but only Plex credentials provided"
            echo "Auto-switching PRIMARY_SERVER to 'plex'"
            PRIMARY_SERVER="plex"
        elif [ -n "$JELLYFIN_URL" ] && [ -n "$JELLYFIN_TOKEN" ]; then
            echo "Warning: PRIMARY_SERVER set to 'emby' but only Jellyfin credentials provided"
            echo "Auto-switching PRIMARY_SERVER to 'jellyfin'"
            PRIMARY_SERVER="jellyfin"
        else
            echo "Error: PRIMARY_SERVER=emby but no valid credentials provided for any server"
            exit 1
        fi
    fi
else
    # If PRIMARY_SERVER is not set or invalid, auto-detect
    if [ -n "$PLEX_URL" ] && [ -n "$PLEX_TOKEN" ]; then
        echo "PRIMARY_SERVER not set or invalid, defaulting to 'plex' based on available credentials"
        PRIMARY_SERVER="plex"
    elif [ -n "$JELLYFIN_URL" ] && [ -n "$JELLYFIN_TOKEN" ]; then
        echo "PRIMARY_SERVER not set or invalid, defaulting to 'jellyfin' based on available credentials"
        PRIMARY_SERVER="jellyfin"
    elif [ -n "$EMBY_URL" ] && [ -n "$EMBY_TOKEN" ]; then
        echo "PRIMARY_SERVER not set or invalid, defaulting to 'emby' based on available credentials"
        PRIMARY_SERVER="emby"
    else
        echo "Error: No valid credentials provided for any media server"
        echo "Please set PLEX_URL/PLEX_TOKEN, JELLYFIN_URL/JELLYFIN_TOKEN, or EMBY_URL/EMBY_TOKEN"
        exit 1
    fi
fi

# Log the final decision
if [ "$original_primary_server" != "$PRIMARY_SERVER" ]; then
    echo "PRIMARY_SERVER changed from '$original_primary_server' to '$PRIMARY_SERVER'"
fi
echo "Using PRIMARY_SERVER: $PRIMARY_SERVER"

# Set default app title if not provided
APP_TITLE=${APP_TITLE:-"Glimpse"}
echo "Using application title: $APP_TITLE"

# Set default cron schedule if not provided
CRON_SCHEDULE=${CRON_SCHEDULE:-"0 */6 * * *"}

# Set default sort method
SORT_BY_DATE_ADDED=${SORT_BY_DATE_ADDED:-"false"}
echo "Default sort by date added: $SORT_BY_DATE_ADDED"

# Find Python path
PYTHON_PATH=$(which python)
echo "Python path: $PYTHON_PATH"

# Create the cron job with PATH
echo "PATH=/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin" >/etc/cron.d/media-cron

# Add cron jobs for each configured server
if [ -n "$PLEX_URL" ] && [ -n "$PLEX_TOKEN" ]; then
    echo "$CRON_SCHEDULE root cd /app && PLEX_EXCLUDE_LIBRARIES=\"$PLEX_EXCLUDE_LIBRARIES\" $PYTHON_PATH /app/scripts/plex_data_fetcher.py --url \"$PLEX_URL\" --token \"$PLEX_TOKEN\" --output /app/data/plex >> /var/log/cron.log 2>&1" >>/etc/cron.d/media-cron
fi

if [ -n "$JELLYFIN_URL" ] && [ -n "$JELLYFIN_TOKEN" ]; then
    echo "$CRON_SCHEDULE root cd /app && JELLYFIN_EXCLUDE_LIBRARIES=\"$JELLYFIN_EXCLUDE_LIBRARIES\" $PYTHON_PATH /app/scripts/jellyfin_data_fetcher.py --url \"$JELLYFIN_URL\" --token \"$JELLYFIN_TOKEN\" --output /app/data/jellyfin >> /var/log/cron.log 2>&1" >>/etc/cron.d/media-cron
fi

if [ -n "$EMBY_URL" ] && [ -n "$EMBY_TOKEN" ]; then
    echo "$CRON_SCHEDULE root cd /app && EMBY_EXCLUDE_LIBRARIES=\"$EMBY_EXCLUDE_LIBRARIES\" $PYTHON_PATH /app/scripts/jellyfin_data_fetcher.py --url \"$EMBY_URL\" --token \"$EMBY_TOKEN\" --output /app/data/emby >> /var/log/cron.log 2>&1" >>/etc/cron.d/media-cron
fi

# Apply cron job
crontab /etc/cron.d/media-cron

# Migrate existing data to new structure for backward compatibility
migrate_existing_data() {
    echo "Checking for existing data to migrate..."

    # Check if there are files directly in /app/data that should be moved to /app/data/plex
    if [ -f "/app/data/movies.json" ] || [ -f "/app/data/tvshows.json" ] || [ -d "/app/data/posters" ] || [ -d "/app/data/backdrops" ]; then
        echo "Found existing Plex data in /app/data - migrating to /app/data/plex/"

        # Create plex directory if it doesn't exist
        mkdir -p /app/data/plex

        # Move JSON files
        if [ -f "/app/data/movies.json" ]; then
            echo "Moving movies.json to plex directory"
            mv /app/data/movies.json /app/data/plex/
        fi

        if [ -f "/app/data/tvshows.json" ]; then
            echo "Moving tvshows.json to plex directory"
            mv /app/data/tvshows.json /app/data/plex/
        fi

        # Move image directories
        if [ -d "/app/data/posters" ]; then
            echo "Moving posters directory to plex directory"
            mv /app/data/posters /app/data/plex/
        fi

        if [ -d "/app/data/backdrops" ]; then
            echo "Moving backdrops directory to plex directory"
            mv /app/data/backdrops /app/data/plex/
        fi

        # Move checksums file if it exists
        if [ -f "/app/data/checksums.pkl" ]; then
            echo "Moving checksums.pkl to plex directory"
            mv /app/data/checksums.pkl /app/data/plex/
        fi

        echo "Migration completed successfully"

        # Set permissions on moved files
        chown -R www-data:www-data /app/data/plex/ 2>/dev/null || echo "Note: Could not set permissions on migrated files"
    else
        echo "No existing data found to migrate"
    fi
}

# Run migration before setting up new structure
migrate_existing_data

# Create directory structure for all servers
mkdir -p /app/web/plex
mkdir -p /app/web/jellyfin
mkdir -p /app/web/emby

# Function to create themed offline.html
create_themed_offline() {
    local server_type=$1
    local app_title=$2

    echo "Creating $server_type themed offline.html"

    if [ "$server_type" = "jellyfin" ]; then
        # Jellyfin themed offline page
        cat >/app/web/offline.html <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Offline - REPLACE_APP_TITLE</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            background: linear-gradient(135deg, #101010 0%, #181818 50%, #1a1a2e 100%);
            background-attachment: fixed;
            color: #fff;
            text-align: center;
            padding: 40px 20px;
            margin: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .container {
            max-width: 500px;
        }
        h1 {
            color: #00a4dc;
            margin-bottom: 20px;
            font-size: 2.5rem;
            font-weight: 700;
        }
        p {
            font-size: 18px;
            line-height: 1.6;
            margin-bottom: 30px;
            color: rgba(255, 255, 255, 0.9);
        }
        .icon {
            font-size: 64px;
            margin-bottom: 30px;
            filter: hue-rotate(200deg);
        }
        button {
            background: linear-gradient(135deg, #00a4dc, #7b68ee);
            color: #fff;
            border: none;
            padding: 12px 20px;
            border-radius: 24px;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(0, 164, 220, 0.3);
        }
        button:hover {
            background: linear-gradient(135deg, #0288c2, #6a5acd);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 164, 220, 0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📶</div>
        <h1>You're Offline</h1>
        <p>It looks like you're not connected to the internet. REPLACE_APP_TITLE needs a connection to show your Jellyfin content.</p>
        <button onclick="window.location.reload()">Try Again</button>
    </div>
</body>
</html>
EOF
    elif [ "$server_type" = "emby" ]; then
        # Emby themed offline page
        cat >/app/web/offline.html <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Offline - REPLACE_APP_TITLE</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            background: linear-gradient(135deg, #0f1419 0%, #1a2332 50%, #0d1b2a 100%);
            background-attachment: fixed;
            color: #fff;
            text-align: center;
            padding: 40px 20px;
            margin: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .container {
            max-width: 500px;
        }
        h1 {
            color: #52c41a;
            margin-bottom: 20px;
            font-size: 2.5rem;
            font-weight: 700;
        }
        p {
            font-size: 18px;
            line-height: 1.6;
            margin-bottom: 30px;
            color: rgba(255, 255, 255, 0.9);
        }
        .icon {
            font-size: 64px;
            margin-bottom: 30px;
            filter: hue-rotate(100deg);
        }
        button {
            background: linear-gradient(135deg, #52c41a, #389e0d);
            color: #fff;
            border: none;
            padding: 12px 20px;
            border-radius: 24px;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(82, 196, 26, 0.3);
        }
        button:hover {
            background: linear-gradient(135deg, #389e0d, #237804);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(82, 196, 26, 0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📶</div>
        <h1>You're Offline</h1>
        <p>It looks like you're not connected to the internet. REPLACE_APP_TITLE needs a connection to show your Emby content.</p>
        <button onclick="window.location.reload()">Try Again</button>
    </div>
</body>
</html>
EOF
    else
        # Plex themed offline page (default)
        cat >/app/web/offline.html <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Offline - REPLACE_APP_TITLE</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            background-color: #1a1a1a;
            color: #fff;
            text-align: center;
            padding: 40px 20px;
            margin: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .container {
            max-width: 500px;
        }
        h1 {
            color: #e5a00d;
            margin-bottom: 20px;
            font-size: 2.5rem;
            font-weight: 700;
        }
        p {
            font-size: 18px;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .icon {
            font-size: 64px;
            margin-bottom: 30px;
        }
        button {
            background-color: #e5a00d;
            color: #000;
            border: none;
            padding: 12px 20px;
            border-radius: 24px;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
        }
        button:hover {
            background-color: #f1b020;
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📶</div>
        <h1>You're Offline</h1>
        <p>It looks like you're not connected to the internet. REPLACE_APP_TITLE needs a connection to show your Plex content.</p>
        <button onclick="window.location.reload()">Try Again</button>
    </div>
</body>
</html>
EOF
    fi

    # Replace the app title placeholder
    sed -i "s/REPLACE_APP_TITLE/$app_title/g" /app/web/offline.html

    # Set proper permissions
    chown www-data:www-data /app/web/offline.html 2>/dev/null || echo "Note: Could not set permissions on offline.html"
}

create_themed_manifest() {
    local server_type=$1
    local app_title=$2

    echo "Creating $server_type themed manifest.json"

    if [ "$server_type" = "jellyfin" ]; then
        # Jellyfin themed manifest
        cat >/app/web/manifest.json <<EOF
{
  "name": "Glimpse Media Viewer",
  "short_name": "Glimpse",
  "description": "A sleek, responsive web application for browsing your Plex/Jellyfin/Emby media server",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#101010",
  "theme_color": "#101010",
  "orientation": "any",
  "icons": [
    {
      "src": "/images/jellyfin/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/images/jellyfin/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
EOF
    elif [ "$server_type" = "emby" ]; then
        # Emby themed manifest
        cat >/app/web/manifest.json <<EOF
{
  "name": "Glimpse Media Viewer",
  "short_name": "Glimpse",
  "description": "A sleek, responsive web application for browsing your Plex/Jellyfin/Emby media server",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f1419",
  "theme_color": "#0f1419",
  "orientation": "any",
  "icons": [
    {
      "src": "/images/emby/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/images/emby/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
EOF
    else
        # Plex themed manifest (default)
        cat >/app/web/manifest.json <<EOF
{
  "name": "Glimpse Media Viewer",
  "short_name": "Glimpse",
  "description": "A sleek, responsive web application for browsing your Plex/Jellyfin/Emby media server",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#131313",
  "theme_color": "#131313",
  "orientation": "any",
  "icons": [
    {
      "src": "/images/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/images/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
EOF
    fi

    # Set proper permissions
    chown www-data:www-data /app/web/manifest.json 2>/dev/null || echo "Note: Could not set permissions on manifest.json"

    # Also update the HTML meta theme-color tag
    if [ -f /app/web/index.html ]; then
        if [ "$server_type" = "jellyfin" ]; then
            sed -i 's/<meta name="theme-color" content="[^"]*">/<meta name="theme-color" content="#101010">/' /app/web/index.html
        elif [ "$server_type" = "emby" ]; then
            sed -i 's/<meta name="theme-color" content="[^"]*">/<meta name="theme-color" content="#0f1419">/' /app/web/index.html
        else
            sed -i 's/<meta name="theme-color" content="[^"]*">/<meta name="theme-color" content="#131313">/' /app/web/index.html
        fi
    fi
}

apply_jellyfin_theme() {
    local index_file=$1
    echo "Applying Jellyfin theme to $index_file"

    # Update image paths to point to jellyfin directory
    echo "Updating image paths to use jellyfin directory"

    # Update logo image path - be specific to avoid double replacement
    sed -i 's|src="images/logo\.png"|src="images/jellyfin/logo.png"|g' "$index_file"
    sed -i 's|src="../images/logo\.png"|src="../images/jellyfin/logo.png"|g' "$index_file"

    # Update specific favicon and meta tag images
    sed -i 's|href="images/android-chrome-192x192\.png"|href="images/jellyfin/android-chrome-192x192.png"|g' "$index_file"
    sed -i 's|href="/images/android-chrome-192x192\.png"|href="/images/jellyfin/android-chrome-192x192.png"|g' "$index_file"
    sed -i 's|href="../images/android-chrome-192x192\.png"|href="../images/jellyfin/android-chrome-192x192.png"|g' "$index_file"

    sed -i 's|href="images/android-chrome-592x592\.png"|href="images/jellyfin/android-chrome-592x592.png"|g' "$index_file"
    sed -i 's|href="/images/android-chrome-592x592\.png"|href="/images/jellyfin/android-chrome-592x592.png"|g' "$index_file"
    sed -i 's|href="../images/android-chrome-592x592\.png"|href="../images/jellyfin/android-chrome-592x592.png"|g' "$index_file"

    sed -i 's|href="images/apple-touch-icon\.png"|href="images/jellyfin/apple-touch-icon.png"|g' "$index_file"
    sed -i 's|href="../images/apple-touch-icon\.png"|href="../images/jellyfin/apple-touch-icon.png"|g' "$index_file"

    sed -i 's|href="images/favicon-32x32\.png"|href="images/jellyfin/favicon-32x32.png"|g' "$index_file"
    sed -i 's|href="../images/favicon-32x32\.png"|href="../images/jellyfin/favicon-32x32.png"|g' "$index_file"

    sed -i 's|href="images/favicon-16x16\.png"|href="images/jellyfin/favicon-16x16.png"|g' "$index_file"
    sed -i 's|href="../images/favicon-16x16\.png"|href="../images/jellyfin/favicon-16x16.png"|g' "$index_file"

    # Update title for main index files (primary server gets indicator too)
    if [[ "$index_file" == "/app/web/index.html" ]]; then
        # This is the main index, add Jellyfin indicator
        current_title=$(grep -o '<title>[^<]*</title>' "$index_file" | sed 's/<title>\(.*\)<\/title>/\1/')
        clean_title=$(echo "$current_title" | sed 's/ - Jellyfin//g' | sed 's/ - Plex//g' | sed 's/ - Emby//g')
        sed -i "s|<title>.*</title>|<title>$clean_title - Jellyfin</title>|" "$index_file"
        echo "Updated main index title to: $clean_title - Jellyfin"
    fi

    # Create temporary file with Jellyfin CSS overrides
    cat >/tmp/jellyfin_theme.css <<'EOF'

        /* Jellyfin Theme Overrides */
        :root {
            --primary-color: #00a4dc !important;
            --primary-hover: #0288c2 !important;
            --primary-light: rgba(0, 164, 220, 0.1) !important;
            --bg-color: #101010 !important;
            --secondary-bg: #181818 !important;
            --header-bg: #141414 !important;
            --tab-bg: #252525 !important;
        }
        
        /* Ensure full screen coverage without affecting layout */
        html {
            min-height: 100vh;
        }
        
        /* Jellyfin gradient background */
        body {
            background: linear-gradient(135deg, #101010 0%, #181818 50%, #1a1a2e 100%) !important;
            background-attachment: fixed !important;
            background-size: cover !important;
            background-repeat: no-repeat !important;
            min-height: 100vh;
        }
        
        /* Jellyfin accent color for active elements */
        .tab.active,
        .sort-button.active,
        .genre-button.active {
            background: linear-gradient(135deg, #00a4dc, #7b68ee) !important;
            color: white !important;
        }
        
        /* Jellyfin hover effects */
        .tab:hover:not(.active),
        .sort-button:hover:not(.active),
        .genre-button:hover:not(.active),
        .server-toggle-button:hover,
        .roulette-button:hover,
        .modal-try-again-btn:hover {
            background-color: rgba(0, 164, 220, 0.2) !important;
        }
        
        /* Jellyfin search input focus styling */
        .search-input:focus {
            background-color: rgba(0, 0, 0, 0.35) !important;
            box-shadow: 0 0 0 2px rgba(0, 164, 220, 0.4) !important;
        }
        
        /* Jellyfin search clear button */
        .search-clear:hover {
            color: #00a4dc !important;
            background-color: rgba(0, 164, 220, 0.1) !important;
        }
        
        /* Jellyfin genre styling */
        .genre-tag {
            background-color: rgba(0, 164, 220, 0.2) !important;
            color: #00a4dc !important;
        }
        
        .genre-tag:hover {
            background-color: rgba(0, 164, 220, 0.3) !important;
        }
        
        .genre-item.active {
            background-color: rgba(0, 164, 220, 0.1) !important;
            color: #00a4dc !important;
        }
        
        .genre-badge {
            background-color: #00a4dc !important;
            color: #ffffff !important;
        }
        
        /* Jellyfin trailer loading spinner */
        .trailer-spinner,
        .trailer-loading .trailer-spinner {
            border: 4px solid rgba(0, 164, 220, 0.2) !important;
            border-top-color: #00a4dc !important;
        }
        
        /* Jellyfin roulette spinner */
        .spinner-item {
            background-color: #00a4dc !important;
        }
        
        /* Jellyfin loading spinner (main) */
        .loading-spinner {
            border: 3px solid rgba(0, 164, 220, 0.1) !important;
            border-top-color: #00a4dc !important;
        }
        
        /* Jellyfin watch trailer button */
        .watch-trailer-btn {
            background: linear-gradient(135deg, #00a4dc, #7b68ee) !important;
            color: #ffffff !important;
        }
        
        .watch-trailer-btn:hover {
            background: linear-gradient(135deg, #0288c2, #6a5acd) !important;
        }
        
        /* Jellyfin install button */
        .install-button {
            background: linear-gradient(135deg, #00a4dc, #7b68ee) !important;
            color: #ffffff !important;
        }
        
        .install-button:hover {
            background: linear-gradient(135deg, #0288c2, #6a5acd) !important;
        }
        
        /* Jellyfin media item hover - no glow, better contrast */
        .media-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
        }
        
        /* Jellyfin poster container - better contrast against dark background */
        .media-item {
            background-color: #252525 !important;
        }
        
        /* Jellyfin scroll indicators */
        .scroll-to-top {
            background: linear-gradient(135deg, #00a4dc, #7b68ee) !important;
            color: #ffffff !important;
        }
        
        .scroll-to-top:hover {
            background: linear-gradient(135deg, #0288c2, #6a5acd) !important;
        }
        
        /* Jellyfin text placeholders */
        .text-placeholder {
            border: 1px solid rgba(0, 164, 220, 0.2) !important;
            color: #00a4dc !important;
        }

EOF

    # Insert Jellyfin theme CSS after the existing styles but before closing </style>
    sed -i '/<\/style>/e cat /tmp/jellyfin_theme.css' "$index_file"

    # Clean up temporary file
    rm -f /tmp/jellyfin_theme.css
}

apply_emby_theme() {
    local index_file=$1
    echo "Applying Emby theme to $index_file"

    # Update image paths to point to emby directory
    echo "Updating image paths to use emby directory"

    # Update logo image path - be specific to avoid double replacement
    sed -i 's|src="images/logo\.png"|src="images/emby/logo.png"|g' "$index_file"
    sed -i 's|src="../images/logo\.png"|src="../images/emby/logo.png"|g' "$index_file"

    # Update specific favicon and meta tag images
    sed -i 's|href="images/android-chrome-192x192\.png"|href="images/emby/android-chrome-192x192.png"|g' "$index_file"
    sed -i 's|href="/images/android-chrome-192x192\.png"|href="/images/emby/android-chrome-192x192.png"|g' "$index_file"
    sed -i 's|href="../images/android-chrome-192x192\.png"|href="../images/emby/android-chrome-192x192.png"|g' "$index_file"

    sed -i 's|href="images/android-chrome-592x592\.png"|href="images/emby/android-chrome-592x592.png"|g' "$index_file"
    sed -i 's|href="/images/android-chrome-592x592\.png"|href="/images/emby/android-chrome-592x592.png"|g' "$index_file"
    sed -i 's|href="../images/android-chrome-592x592\.png"|href="../images/emby/android-chrome-592x592.png"|g' "$index_file"

    sed -i 's|href="images/apple-touch-icon\.png"|href="images/emby/apple-touch-icon.png"|g' "$index_file"
    sed -i 's|href="../images/apple-touch-icon\.png"|href="../images/emby/apple-touch-icon.png"|g' "$index_file"

    sed -i 's|href="images/favicon-32x32\.png"|href="images/emby/favicon-32x32.png"|g' "$index_file"
    sed -i 's|href="../images/favicon-32x32\.png"|href="../images/emby/favicon-32x32.png"|g' "$index_file"

    sed -i 's|href="images/favicon-16x16\.png"|href="images/emby/favicon-16x16.png"|g' "$index_file"
    sed -i 's|href="../images/favicon-16x16\.png"|href="../images/emby/favicon-16x16.png"|g' "$index_file"

    # Update title for main index files (primary server gets indicator too)
    if [[ "$index_file" == "/app/web/index.html" ]]; then
        # This is the main index, add Emby indicator
        current_title=$(grep -o '<title>[^<]*</title>' "$index_file" | sed 's/<title>\(.*\)<\/title>/\1/')
        clean_title=$(echo "$current_title" | sed 's/ - Jellyfin//g' | sed 's/ - Plex//g' | sed 's/ - Emby//g')
        sed -i "s|<title>.*</title>|<title>$clean_title - Emby</title>|" "$index_file"
        echo "Updated main index title to: $clean_title - Emby"
    fi

    # Create temporary file with Emby CSS overrides
    cat >/tmp/emby_theme.css <<'EOF'

        /* Emby Theme Overrides */
        :root {
            --primary-color: #52c41a !important;
            --primary-hover: #389e0d !important;
            --primary-light: rgba(82, 196, 26, 0.1) !important;
            --bg-color: #0f1419 !important;
            --secondary-bg: #1a2332 !important;
            --header-bg: #162029 !important;
            --tab-bg: #2a3441 !important;
        }
        
        /* Ensure full screen coverage without affecting layout */
        html {
            min-height: 100vh;
        }
        
        /* Emby gradient background */
        body {
            background: linear-gradient(135deg, #0f1419 0%, #1a2332 50%, #0d1b2a 100%) !important;
            background-attachment: fixed !important;
            background-size: cover !important;
            background-repeat: no-repeat !important;
            min-height: 100vh;
        }
        
        /* Emby accent color for active elements */
        .tab.active,
        .sort-button.active,
        .genre-button.active {
            background: linear-gradient(135deg, #52c41a, #389e0d) !important;
            color: white !important;
        }
        
        /* Emby hover effects */
        .tab:hover:not(.active),
        .sort-button:hover:not(.active),
        .genre-button:hover:not(.active),
        .server-toggle-button:hover,
        .roulette-button:hover,
        .modal-try-again-btn:hover {
            background-color: rgba(82, 196, 26, 0.2) !important;
        }
        
        /* Emby search input focus styling */
        .search-input:focus {
            background-color: rgba(0, 0, 0, 0.35) !important;
            box-shadow: 0 0 0 2px rgba(82, 196, 26, 0.4) !important;
        }
        
        /* Emby search clear button */
        .search-clear:hover {
            color: #52c41a !important;
            background-color: rgba(82, 196, 26, 0.1) !important;
        }
        
        /* Emby genre styling */
        .genre-tag {
            background-color: rgba(82, 196, 26, 0.2) !important;
            color: #52c41a !important;
        }
        
        .genre-tag:hover {
            background-color: rgba(82, 196, 26, 0.3) !important;
        }
        
        .genre-item.active {
            background-color: rgba(82, 196, 26, 0.1) !important;
            color: #52c41a !important;
        }
        
        .genre-badge {
            background-color: #52c41a !important;
            color: #ffffff !important;
        }
        
        /* Emby trailer loading spinner */
        .trailer-spinner,
        .trailer-loading .trailer-spinner {
            border: 4px solid rgba(82, 196, 26, 0.2) !important;
            border-top-color: #52c41a !important;
        }
        
        /* Emby roulette spinner */
        .spinner-item {
            background-color: #52c41a !important;
        }
        
        /* Emby loading spinner (main) */
        .loading-spinner {
            border: 3px solid rgba(82, 196, 26, 0.1) !important;
            border-top-color: #52c41a !important;
        }
        
        /* Emby watch trailer button */
        .watch-trailer-btn {
            background: linear-gradient(135deg, #52c41a, #389e0d) !important;
            color: #ffffff !important;
        }
        
        .watch-trailer-btn:hover {
            background: linear-gradient(135deg, #389e0d, #237804) !important;
        }
        
        /* Emby install button */
        .install-button {
            background: linear-gradient(135deg, #52c41a, #389e0d) !important;
            color: #ffffff !important;
        }
        
        .install-button:hover {
            background: linear-gradient(135deg, #389e0d, #237804) !important;
        }
        
        /* Emby media item hover - no glow, better contrast */
        .media-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
        }
        
        /* Emby poster container - better contrast against dark background */
        .media-item {
            background-color: #2a3441 !important;
        }
        
        /* Emby scroll indicators */
        .scroll-to-top {
            background: linear-gradient(135deg, #52c41a, #389e0d) !important;
            color: #ffffff !important;
        }
        
        .scroll-to-top:hover {
            background: linear-gradient(135deg, #389e0d, #237804) !important;
        }
        
        /* Emby text placeholders */
        .text-placeholder {
            border: 1px solid rgba(82, 196, 26, 0.2) !important;
            color: #52c41a !important;
        }

EOF

    # Insert Emby theme CSS after the existing styles but before closing </style>
    sed -i '/<\/style>/e cat /tmp/emby_theme.css' "$index_file"

    # Clean up temporary file
    rm -f /tmp/emby_theme.css
}

# Function to clean up any duplicate server dropdown content from HTML files
cleanup_duplicate_server_content() {
    local index_file=$1
    echo "Cleaning up duplicate server content from $index_file"

    # Create a temporary file for the cleaned content
    local temp_file=$(mktemp)

    # Use awk to remove duplicate sections
    awk '
    BEGIN {
        in_server_drawer = 0
        in_server_style = 0
        in_server_script = 0
        server_drawer_count = 0
        server_style_count = 0
        server_script_count = 0
        skip_until_tag = ""
    }
    
    # Track server drawer overlay sections
    /<!-- Server Drawer Overlay/ {
        server_drawer_count++
        if (server_drawer_count > 1) {
            in_server_drawer = 1
            skip_until_tag = "</div>"
            next
        }
    }
    
    # Track server dropdown styles
    /\/\* Server Dropdown Styles/ {
        server_style_count++
        if (server_style_count > 1) {
            in_server_style = 1
            skip_until_tag = "}"
            next
        }
    }
    
    # Track server JavaScript sections
    /\/\/ Replace existing server toggle functionality/ {
        server_script_count++
        if (server_script_count > 1) {
            in_server_script = 1
            skip_until_tag = "</script>"
            next
        }
    }
    
    # Skip content until we reach the end tag
    {
        if (in_server_drawer && $0 ~ skip_until_tag && $0 ~ /server-drawer/) {
            in_server_drawer = 0
            skip_until_tag = ""
            next
        }
        if (in_server_style && $0 ~ /^[[:space:]]*}[[:space:]]*$/ && prev_line ~ /mobile.*server/) {
            in_server_style = 0
            skip_until_tag = ""
            next
        }
        if (in_server_script && $0 ~ skip_until_tag) {
            in_server_script = 0
            skip_until_tag = ""
            next
        }
        
        if (!in_server_drawer && !in_server_style && !in_server_script) {
            print $0
        }
        prev_line = $0
    }
    ' "$index_file" >"$temp_file"

    # Replace the original file with the cleaned version
    mv "$temp_file" "$index_file"

    # Also remove any duplicate toggleServer function definitions
    sed -i '/window\.toggleServer = function()/,/^[[:space:]]*};[[:space:]]*$/{ 
        /window\.toggleServer = function()/!b skip
        N
        :loop
        /^[[:space:]]*};[[:space:]]*$/!{N; b loop}
        # Keep only the first occurrence
        s/.*//
        :skip
    }' "$index_file" 2>/dev/null || true

    echo "Cleanup completed for $index_file"
}

remove_server_toggle() {
    local index_file=$1
    echo "Hiding server toggle from $index_file (single server mode)"

    # Clean up any existing server dropdown content first
    cleanup_duplicate_server_content "$index_file"

    # Add CSS to hide server toggle elements
    cat >>"$index_file" <<'EOF'
<style>
/* Hide server toggle in single server mode */
.server-toggle,
.server-toggle-button,
.server-dropdown,
.server-drawer-overlay {
    display: none !important;
    visibility: hidden !important;
}
</style>

<script>
// Override toggleServer function to be safe in single server mode
if (typeof toggleServer !== 'undefined') {
    window.toggleServer = function() {
        console.log("Server toggle disabled - only one server configured");
        return false;
    };
} else {
    window.toggleServer = function() {
        console.log("Server toggle disabled - only one server configured");
        return false;
    };
}
</script>
EOF
}

# Function to create index.html for a specific server
create_server_index() {
    local server_type=$1
    local data_path=$2
    local output_file=$3

    echo "Creating server index for $server_type at $output_file"

    # Copy the main index.html as a template
    cp /app/web/index.html "$output_file"

    # Clean up any duplicate content from the copied file
    cleanup_duplicate_server_content "$output_file"

    # Set the title immediately based on the route type
    if [[ "$output_file" == *"/plex/index.html" ]]; then
        # This is a Plex secondary route
        current_title=$(grep -o '<title>[^<]*</title>' "$output_file" | sed 's/<title>\(.*\)<\/title>/\1/')
        clean_title=$(echo "$current_title" | sed 's/ - Jellyfin//g' | sed 's/ - Plex//g' | sed 's/ - Emby//g')
        sed -i "s|<title>.*</title>|<title>$clean_title - Plex</title>|" "$output_file"
        echo "Set Plex secondary route title: $clean_title - Plex"
    elif [[ "$output_file" == *"/jellyfin/index.html" ]]; then
        # This is a Jellyfin secondary route
        current_title=$(grep -o '<title>[^<]*</title>' "$output_file" | sed 's/<title>\(.*\)<\/title>/\1/')
        clean_title=$(echo "$current_title" | sed 's/ - Jellyfin//g' | sed 's/ - Plex//g' | sed 's/ - Emby//g')
        sed -i "s|<title>.*</title>|<title>$clean_title - Jellyfin</title>|" "$output_file"
        echo "Set Jellyfin secondary route title: $clean_title - Jellyfin"
    elif [[ "$output_file" == *"/emby/index.html" ]]; then
        # This is an Emby secondary route
        current_title=$(grep -o '<title>[^<]*</title>' "$output_file" | sed 's/<title>\(.*\)<\/title>/\1/')
        clean_title=$(echo "$current_title" | sed 's/ - Jellyfin//g' | sed 's/ - Plex//g' | sed 's/ - Emby//g')
        sed -i "s|<title>.*</title>|<title>$clean_title - Emby</title>|" "$output_file"
        echo "Set Emby secondary route title: $clean_title - Emby"
    fi

    # For sub-directory routes, we need to use relative paths from the sub-directory
    if [ "$output_file" != "/app/web/index.html" ]; then
        # Reset any existing server-specific paths first
        sed -i "s|data/jellyfin/movies\.json|data/movies.json|g" "$output_file"
        sed -i "s|data/jellyfin/tvshows\.json|data/tvshows.json|g" "$output_file"
        sed -i "s|data/jellyfin/posters/|data/posters/|g" "$output_file"
        sed -i "s|data/jellyfin/backdrops/|data/backdrops/|g" "$output_file"
        sed -i "s|data/plex/movies\.json|data/movies.json|g" "$output_file"
        sed -i "s|data/plex/tvshows\.json|data/tvshows.json|g" "$output_file"
        sed -i "s|data/plex/posters/|data/posters/|g" "$output_file"
        sed -i "s|data/plex/backdrops/|data/backdrops/|g" "$output_file"
        sed -i "s|data/emby/movies\.json|data/movies.json|g" "$output_file"
        sed -i "s|data/emby/tvshows\.json|data/tvshows.json|g" "$output_file"
        sed -i "s|data/emby/posters/|data/posters/|g" "$output_file"
        sed -i "s|data/emby/backdrops/|data/backdrops/|g" "$output_file"

        # Now apply the correct paths with ../
        sed -i "s|'data/movies\.json'|'../${data_path}/movies.json'|g" "$output_file"
        sed -i "s|\"data/movies\.json\"|\"../${data_path}/movies.json\"|g" "$output_file"
        sed -i "s|'data/tvshows\.json'|'../${data_path}/tvshows.json'|g" "$output_file"
        sed -i "s|\"data/tvshows\.json\"|\"../${data_path}/tvshows.json\"|g" "$output_file"
        sed -i "s|data/posters/|../${data_path}/posters/|g" "$output_file"
        sed -i "s|data/backdrops/|../${data_path}/backdrops/|g" "$output_file"

        # Fix asset paths that should remain relative to root
        sed -i 's|src="images/|src="../images/|g' "$output_file"
        sed -i 's|href="images/|href="../images/|g' "$output_file"
        sed -i 's|href="/manifest.json"|href="../manifest.json"|g' "$output_file"
        sed -i 's|href="/images/|href="../images/|g' "$output_file"
        sed -i 's|register("/sw.js")|register("../sw.js")|g' "$output_file"
    else
        # For main index.html, just update the data paths directly
        sed -i "s|'data/movies\.json'|'${data_path}/movies.json'|g" "$output_file"
        sed -i "s|\"data/movies\.json\"|\"${data_path}/movies.json\"|g" "$output_file"
        sed -i "s|'data/tvshows\.json'|'${data_path}/tvshows.json'|g" "$output_file"
        sed -i "s|\"data/tvshows\.json\"|\"${data_path}/tvshows.json\"|g" "$output_file"
        sed -i "s|data/posters/|${data_path}/posters/|g" "$output_file"
        sed -i "s|data/backdrops/|${data_path}/backdrops/|g" "$output_file"
    fi
}

# Function to count configured servers
count_configured_servers() {
    local count=0

    if [ -n "$PLEX_URL" ] && [ -n "$PLEX_TOKEN" ]; then
        count=$((count + 1))
    fi

    if [ -n "$JELLYFIN_URL" ] && [ -n "$JELLYFIN_TOKEN" ]; then
        count=$((count + 1))
    fi

    if [ -n "$EMBY_URL" ] && [ -n "$EMBY_TOKEN" ]; then
        count=$((count + 1))
    fi

    echo $count
}

# Function to configure multi-server dropdown (for 2+ servers)
configure_multi_server_dropdown() {
    echo "Configuring multi-server dropdown system for 2+ servers"

    # Create routes for all secondary servers
    if [ "$PRIMARY_SERVER" != "plex" ] && [ -n "$PLEX_URL" ] && [ -n "$PLEX_TOKEN" ]; then
        create_server_index "plex" "data/plex" "/app/web/plex/index.html"
    fi
    if [ "$PRIMARY_SERVER" != "jellyfin" ] && [ -n "$JELLYFIN_URL" ] && [ -n "$JELLYFIN_TOKEN" ]; then
        create_server_index "jellyfin" "data/jellyfin" "/app/web/jellyfin/index.html"
    fi
    if [ "$PRIMARY_SERVER" != "emby" ] && [ -n "$EMBY_URL" ] && [ -n "$EMBY_TOKEN" ]; then
        create_server_index "emby" "data/emby" "/app/web/emby/index.html"
    fi

    # Replace toggle button with dropdown for all routes
    replace_toggle_with_dropdown "/app/web/index.html" "$PRIMARY_SERVER"

    if [ -f "/app/web/plex/index.html" ]; then
        replace_toggle_with_dropdown "/app/web/plex/index.html" "plex"
    fi
    if [ -f "/app/web/jellyfin/index.html" ]; then
        replace_toggle_with_dropdown "/app/web/jellyfin/index.html" "jellyfin"
    fi
    if [ -f "/app/web/emby/index.html" ]; then
        replace_toggle_with_dropdown "/app/web/emby/index.html" "emby"
    fi
}

# Function to replace toggle button with dropdown
replace_toggle_with_dropdown() {
    local index_file=$1
    local current_server=$2

    echo "Replacing toggle button with dropdown in $index_file (current: $current_server)"

    # Clean up any existing dropdown content first
    cleanup_duplicate_server_content "$index_file"

    # Build dropdown options and current server display
    local dropdown_items=""
    local current_server_display=""
    local current_server_icon=""
    local icon_base_path=""

    # Determine current path and icon base path based on file location
    if [[ "$index_file" == "/app/web/index.html" ]]; then
        current_path="/"
        icon_base_path="images/icons/"
    elif [[ "$index_file" == *"/plex/index.html" ]]; then
        current_path="/plex/"
        icon_base_path="../images/icons/"
    elif [[ "$index_file" == *"/jellyfin/index.html" ]]; then
        current_path="/jellyfin/"
        icon_base_path="../images/icons/"
    elif [[ "$index_file" == *"/emby/index.html" ]]; then
        current_path="/emby/"
        icon_base_path="../images/icons/"
    fi

    # Add options for all configured servers
    if [ -n "$PLEX_URL" ] && [ -n "$PLEX_TOKEN" ]; then
        local plex_path="/"
        local plex_relative_path=""

        if [ "$PRIMARY_SERVER" = "plex" ]; then
            plex_path="/"
            if [[ "$index_file" == "/app/web/index.html" ]]; then
                plex_relative_path="/"
            else
                plex_relative_path="../"
            fi
        else
            plex_path="/plex/"
            if [[ "$index_file" == "/app/web/index.html" ]]; then
                plex_relative_path="plex/"
            else
                plex_relative_path="../plex/"
            fi
        fi

        local plex_active=""
        if [ "$current_server" = "plex" ]; then
            plex_active=" active"
            current_server_display="Plex"
            current_server_icon="<img src=\"${icon_base_path}plex.png\" alt=\"Plex\" class=\"server-icon-img\">"
        fi

        dropdown_items="$dropdown_items<div class=\"server-item$plex_active\" data-path=\"$plex_relative_path\"><img src=\"${icon_base_path}plex.png\" alt=\"Plex\" class=\"server-icon-img\"> Plex</div>"
    fi

    if [ -n "$JELLYFIN_URL" ] && [ -n "$JELLYFIN_TOKEN" ]; then
        local jellyfin_path="/"
        local jellyfin_relative_path=""

        if [ "$PRIMARY_SERVER" = "jellyfin" ]; then
            jellyfin_path="/"
            if [[ "$index_file" == "/app/web/index.html" ]]; then
                jellyfin_relative_path="/"
            else
                jellyfin_relative_path="../"
            fi
        else
            jellyfin_path="/jellyfin/"
            if [[ "$index_file" == "/app/web/index.html" ]]; then
                jellyfin_relative_path="jellyfin/"
            else
                jellyfin_relative_path="../jellyfin/"
            fi
        fi

        local jellyfin_active=""
        if [ "$current_server" = "jellyfin" ]; then
            jellyfin_active=" active"
            current_server_display="Jellyfin"
            current_server_icon="<img src=\"${icon_base_path}jellyfin.png\" alt=\"Jellyfin\" class=\"server-icon-img\">"
        fi

        dropdown_items="$dropdown_items<div class=\"server-item$jellyfin_active\" data-path=\"$jellyfin_relative_path\"><img src=\"${icon_base_path}jellyfin.png\" alt=\"Jellyfin\" class=\"server-icon-img\"> Jellyfin</div>"
    fi

    if [ -n "$EMBY_URL" ] && [ -n "$EMBY_TOKEN" ]; then
        local emby_path="/"
        local emby_relative_path=""

        if [ "$PRIMARY_SERVER" = "emby" ]; then
            emby_path="/"
            if [[ "$index_file" == "/app/web/index.html" ]]; then
                emby_relative_path="/"
            else
                emby_relative_path="../"
            fi
        else
            emby_path="/emby/"
            if [[ "$index_file" == "/app/web/index.html" ]]; then
                emby_relative_path="emby/"
            else
                emby_relative_path="../emby/"
            fi
        fi

        local emby_active=""
        if [ "$current_server" = "emby" ]; then
            emby_active=" active"
            current_server_display="Emby"
            current_server_icon="<img src=\"${icon_base_path}emby.png\" alt=\"Emby\" class=\"server-icon-img\">"
        fi

        dropdown_items="$dropdown_items<div class=\"server-item$emby_active\" data-path=\"$emby_relative_path\"><img src=\"${icon_base_path}emby.png\" alt=\"Emby\" class=\"server-icon-img\"> Emby</div>"
    fi

    # Create a temporary file with the server dropdown content
    cat >/tmp/server_dropdown_content.html <<EOF

<!-- Server Drawer Overlay for Mobile -->
<div class="server-drawer-overlay">
    <div class="server-drawer">
        <div class="server-drawer-header">
            <div class="server-drawer-title">Select Server</div>
            <button class="server-drawer-close">×</button>
        </div>
        <div class="server-drawer-content">
            $dropdown_items
        </div>
    </div>
</div>

<style>
/* Server Dropdown Styles - Matching Genre Dropdown */
.server-dropdown {
    position: relative;
    display: inline-block;
    margin-left: 8px;
}

.server-button {
    padding: 6px 12px;
    cursor: pointer;
    background-color: var(--tab-bg);
    border: none;
    border-radius: 20px;
    transition: all var(--transition-speed);
    white-space: nowrap;
    font-weight: 500;
    font-size: 0.9rem;
    color: var(--light-text);
    display: flex;
    align-items: center;
    gap: 5px;
}

.server-button:hover {
    background-color: rgba(255, 255, 255, 0.1);
}

.server-menu {
    display: none;
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 5px;
    background-color: var(--secondary-bg);
    border-radius: 8px;
    box-shadow: var(--shadow-md);
    overflow: hidden;
    z-index: 10;
    min-width: 140px;
    max-width: 200px;
    max-height: 300px;
    overflow-y: auto;
}

/* For dropdowns near the left edge of the screen */
.server-dropdown:first-child .server-menu {
    left: 0;
    right: auto;
}

.server-menu.show {
    display: block;
    animation: fadeIn 0.2s ease;
}

.server-item {
    padding: 10px 15px;
    cursor: pointer;
    transition: all var(--transition-speed);
    white-space: nowrap;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

.server-item:hover {
    background-color: rgba(255, 255, 255, 0.1);
}

.server-item.active {
    background-color: var(--primary-light);
    color: var(--primary-color);
    font-weight: 600;
    cursor: default;
}

/* Server Icon Image Styles */
.server-icon-img {
    width: 16px;
    height: 16px;
    object-fit: contain;
    vertical-align: middle;
    flex-shrink: 0;
    margin-right: 2px;
}

/* Server button icon sizing */
.server-button .server-icon-img {
    width: 18px;
    height: 18px;
}

/* Mobile server button icon sizing */
.mobile-menu .server-button .server-icon-img {
    width: 16px;
    height: 16px;
}

/* Server drawer icon sizing */
.server-drawer .server-item .server-icon-img {
    width: 20px;
    height: 20px;
}

/* Server Drawer Styles - Matching Genre Drawer */
.server-drawer-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.7);
    z-index: 1001;
    display: none;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.server-drawer-overlay.open {
    display: block;
    opacity: 1;
}

.server-drawer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: var(--secondary-bg);
    border-radius: 16px 16px 0 0;
    z-index: 1002;
    transform: translateY(100%);
    transition: transform 0.3s ease;
    box-shadow: 0 -5px 20px rgba(0, 0, 0, 0.3);
    max-height: 70vh;
    display: flex;
    flex-direction: column;
}

.server-drawer.open {
    transform: translateY(0);
}

.server-drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid var(--border-color);
    position: relative;
}

.server-drawer-title {
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--light-text);
    flex: 1;
    text-align: center;
}

.server-drawer-close {
    position: absolute;
    right: 15px;
    top: 15px;
    width: 30px;
    height: 30px;
    background-color: rgba(0, 0, 0, 0.3);
    border: none;
    border-radius: 50%;
    color: var(--light-text);
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
}

.server-drawer-content {
    overflow-y: auto;
    padding: 10px 0;
    max-height: calc(70vh - 70px);
}

.server-drawer .server-item {
    padding: 15px 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: 12px;
}

.server-drawer .server-item:last-child {
    border-bottom: none;
}

.server-drawer .server-item.active {
    background-color: var(--primary-light);
}

/* Mobile styles */
@media screen and (max-width: 768px) {
    .server-dropdown {
        margin-left: 10px;
    }
    
    .server-button {
        font-size: 0.85rem;
        padding: 6px 10px;
    }
    
    /* Hide server dropdown on mobile in favor of mobile menu */
    .server-dropdown {
        display: none;
    }
    
    /* Mobile menu server button */
    .mobile-menu .server-dropdown {
        display: block;
        width: 100%;
        margin-left: 0;
        margin-top: 10px;
    }
    
    .mobile-menu .server-button {
        width: 100%;
        justify-content: center;
        padding: 10px;
        font-size: 0.9rem;
    }
    
    /* Never show dropdown menu on mobile */
    .mobile-menu .server-menu {
        display: none !important;
    }
}

/* Apply drawer to mobile server buttons */
@media screen and (max-width: 992px) {
    .server-dropdown .server-menu {
        display: none !important;
        /* Never show dropdown menu on mobile */
    }
}
</style>

<script>
// Replace existing server toggle functionality with dropdown
document.addEventListener('DOMContentLoaded', function() {
    // Get server drawer elements
    const serverDrawerOverlay = document.querySelector('.server-drawer-overlay');
    const serverDrawer = document.querySelector('.server-drawer');
    const serverDrawerClose = document.querySelector('.server-drawer-close');
    
    // Hide existing toggle buttons
    const toggleButtons = document.querySelectorAll('.server-toggle-button');
    toggleButtons.forEach(button => {
        button.style.display = 'none';
    });
    
    // Create dropdown for desktop
    const serverToggle = document.querySelector('.server-toggle');
    if (serverToggle) {
        serverToggle.innerHTML = \`
            <div class="server-dropdown">
                <button class="server-button">
                    <span class="server-icon">$current_server_icon</span>
                    <span class="server-text">$current_server_display</span>
                </button>
                <div class="server-menu">
                    $dropdown_items
                </div>
            </div>
        \`;
    }
    
    // Create button for mobile menu (drawer trigger)
    const mobileMenu = document.querySelector('.mobile-menu');
    if (mobileMenu) {
        // Find the server toggle button in mobile menu and replace it
        const mobileToggleButton = mobileMenu.querySelector('.server-toggle-button');
        if (mobileToggleButton) {
            mobileToggleButton.style.display = 'none';
            
            // Add button after the genre button
            const genreButton = mobileMenu.querySelector('#mobile-genre-button');
            if (genreButton) {
                const mobileButtonHtml = \`
                    <button class="sort-button server-button" id="mobile-server-button">
                        <span class="sort-icon">$current_server_icon $current_server_display</span>
                    </button>
                \`;
                genreButton.insertAdjacentHTML('afterend', mobileButtonHtml);
            }
        }
    }
    
    // Function to open the server drawer
    function openServerDrawer() {
        serverDrawerOverlay.classList.add('open');
        serverDrawer.classList.add('open');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }
    
    // Function to close the server drawer
    function closeServerDrawer() {
        serverDrawerOverlay.classList.remove('open');
        serverDrawer.classList.remove('open');
        document.body.style.overflow = ''; // Restore scrolling
    }
    
    // Mobile server button click handler - open drawer
    const mobileServerButton = document.querySelector('#mobile-server-button');
    if (mobileServerButton) {
        mobileServerButton.addEventListener('click', () => {
            openServerDrawer();
            
            // Close mobile menu if open
            const mobileMenu = document.querySelector('.mobile-menu');
            if (mobileMenu) {
                mobileMenu.classList.remove('open');
            }
        });
    }
    
    // Close server drawer when clicking the close button
    if (serverDrawerClose) {
        serverDrawerClose.addEventListener('click', closeServerDrawer);
    }
    
    // Close server drawer when clicking the overlay
    if (serverDrawerOverlay) {
        serverDrawerOverlay.addEventListener('click', (e) => {
            if (e.target === serverDrawerOverlay) {
                closeServerDrawer();
            }
        });
    }
    
    // Add click event listeners to desktop server dropdown buttons
    document.querySelectorAll('.server-dropdown .server-button').forEach(button => {
        button.addEventListener('click', (e) => {
            // Check if we're on mobile/tablet
            if (window.innerWidth <= 992) {
                openServerDrawer();
                return;
            }
            
            e.stopPropagation();
            
            const dropdown = button.closest('.server-dropdown');
            const menu = dropdown.querySelector('.server-menu');
            
            // Close other dropdowns first
            document.querySelectorAll('.server-menu.show').forEach(m => {
                if (m !== menu) {
                    m.classList.remove('show');
                }
            });
            
            // Toggle current dropdown
            menu.classList.toggle('show');
        });
    });
    
    // Add click event listeners to server menu items (both desktop and drawer)
    document.querySelectorAll('.server-item').forEach(item => {
        item.addEventListener('click', () => {
            const path = item.dataset.path;
            if (!item.classList.contains('active') && path) {
                switchServer(path);
            }
            
            // Close desktop menu
            document.querySelectorAll('.server-menu').forEach(menu => {
                menu.classList.remove('show');
            });
            
            // Close mobile drawer
            closeServerDrawer();
        });
    });
    
    // Close server dropdown when clicking outside (desktop only)
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.server-dropdown')) {
            document.querySelectorAll('.server-menu').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });
});

// Function to handle server switching
function switchServer(path) {
    if (path && path !== '/' && path !== window.location.pathname) {
        // Clear themed cache before switching
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            try {
                const messageChannel = new MessageChannel();
                navigator.serviceWorker.controller.postMessage(
                    { type: 'CLEAR_THEMED_CACHE' },
                    [messageChannel.port2]
                );
            } catch (error) {
                console.log('Could not clear service worker cache:', error);
            }
        }
        
        window.location.href = path;
    }
}

// Override the old toggleServer function to prevent errors
window.toggleServer = function() {
    console.log("Using dropdown instead of toggle");
    return false;
};
</script>
EOF

    # Append the content to the index file
    cat /tmp/server_dropdown_content.html >>"$index_file"

    # Clean up temporary file
    rm -f /tmp/server_dropdown_content.html

    echo "Successfully added server dropdown to $index_file"
}

# Function to fix files that may have corrupted content
fix_corrupted_files() {
    echo "Checking for and fixing any files with duplicate server content..."

    # Check all HTML files for multiple server dropdown sections
    for file in /app/web/index.html /app/web/plex/index.html /app/web/jellyfin/index.html /app/web/emby/index.html; do
        if [ -f "$file" ]; then
            # Count how many server drawer overlays exist
            drawer_count=$(grep -c "<!-- Server Drawer Overlay" "$file" 2>/dev/null || echo "0")

            if [ "$drawer_count" -gt 1 ]; then
                echo "Found $drawer_count server drawer overlays in $file, cleaning up..."
                cleanup_duplicate_server_content "$file"
            fi
        fi
    done

    echo "Corruption check and cleanup completed"
}

# Update the main index.html based on primary server
if [ -f /app/web/index.html ]; then
    echo "Updating app title to: $APP_TITLE"

    # Clean up any existing duplicate content first
    cleanup_duplicate_server_content "/app/web/index.html"

    # Replace title tag content
    sed -i "s/<title>.*<\/title>/<title>$APP_TITLE<\/title>/" /app/web/index.html
    # Replace h1 content (preserve the logo icon span)
    sed -i "s/<h1>.*<\/h1>/<h1><span class=\"logo-icon\"><img src=\"images\/logo.png\" \/><\/span>$APP_TITLE<\/h1>/" /app/web/index.html

    # Update the default sort method in the JavaScript
    if [ "$SORT_BY_DATE_ADDED" = "true" ]; then
        echo "Setting default sort method to date added"
        sed -i "s/let currentSortMethod = 'alpha';/let currentSortMethod = 'date';/" /app/web/index.html
    fi

    # Update data paths based on primary server
    if [ "$PRIMARY_SERVER" = "plex" ]; then
        echo "Setting up primary server as Plex"
        # Main index.html points to plex data
        sed -i "s|'data/movies\.json'|'data/plex/movies.json'|g" /app/web/index.html
        sed -i "s|\"data/movies\.json\"|\"data/plex/movies.json\"|g" /app/web/index.html
        sed -i "s|'data/tvshows\.json'|'data/plex/tvshows.json'|g" /app/web/index.html
        sed -i "s|\"data/tvshows\.json\"|\"data/plex/tvshows.json\"|g" /app/web/index.html
        sed -i "s|data/posters/|data/plex/posters/|g" /app/web/index.html
        sed -i "s|data/backdrops/|data/plex/backdrops/|g" /app/web/index.html

        # Update title to include Plex indicator
        sed -i "s/<title>$APP_TITLE<\/title>/<title>$APP_TITLE - Plex<\/title>/" /app/web/index.html
        echo "Updated primary index title to: $APP_TITLE - Plex"

    elif [ "$PRIMARY_SERVER" = "jellyfin" ]; then
        echo "Setting up primary server as Jellyfin"
        # Main index.html points to jellyfin data
        sed -i "s|'data/movies\.json'|'data/jellyfin/movies.json'|g" /app/web/index.html
        sed -i "s|\"data/movies\.json\"|\"data/jellyfin/movies.json\"|g" /app/web/index.html
        sed -i "s|'data/tvshows\.json'|'data/jellyfin/tvshows.json'|g" /app/web/index.html
        sed -i "s|\"data/tvshows\.json\"|\"data/jellyfin/tvshows.json\"|g" /app/web/index.html
        sed -i "s|data/posters/|data/jellyfin/posters/|g" /app/web/index.html
        sed -i "s|data/backdrops/|data/jellyfin/backdrops/|g" /app/web/index.html

        # Update title to include Jellyfin indicator
        sed -i "s/<title>$APP_TITLE<\/title>/<title>$APP_TITLE - Jellyfin<\/title>/" /app/web/index.html
        echo "Updated primary index title to: $APP_TITLE - Jellyfin"

    else # emby
        echo "Setting up primary server as Emby"
        # Main index.html points to emby data
        sed -i "s|'data/movies\.json'|'data/emby/movies.json'|g" /app/web/index.html
        sed -i "s|\"data/movies\.json\"|\"data/emby/movies.json\"|g" /app/web/index.html
        sed -i "s|'data/tvshows\.json'|'data/emby/tvshows.json'|g" /app/web/index.html
        sed -i "s|\"data/tvshows\.json\"|\"data/emby/tvshows.json\"|g" /app/web/index.html
        sed -i "s|data/posters/|data/emby/posters/|g" /app/web/index.html
        sed -i "s|data/backdrops/|data/emby/backdrops/|g" /app/web/index.html

        # Update title to include Emby indicator
        sed -i "s/<title>$APP_TITLE<\/title>/<title>$APP_TITLE - Emby<\/title>/" /app/web/index.html
        echo "Updated primary index title to: $APP_TITLE - Emby"
    fi

    # Handle server toggle based on configuration
    server_count=$(count_configured_servers)
    echo "Number of configured servers: $server_count"

    if [ "$server_count" -eq 1 ]; then
        echo "Only one server configured - removing server toggle functionality"
        remove_server_toggle "/app/web/index.html"

        # Add server name to title for single server mode too
        current_title=$(grep -o '<title>[^<]*</title>' /app/web/index.html | sed 's/<title>\(.*\)<\/title>/\1/')
        if [[ "$current_title" != *" - "* ]]; then
            # Only add server name if it's not already there
            if [ "$PRIMARY_SERVER" = "plex" ]; then
                sed -i "s/<title>$current_title<\/title>/<title>$current_title - Plex<\/title>/" /app/web/index.html
                echo "Updated single server title to: $current_title - Plex"
            elif [ "$PRIMARY_SERVER" = "jellyfin" ]; then
                sed -i "s/<title>$current_title<\/title>/<title>$current_title - Jellyfin<\/title>/" /app/web/index.html
                echo "Updated single server title to: $current_title - Jellyfin"
            elif [ "$PRIMARY_SERVER" = "emby" ]; then
                sed -i "s/<title>$current_title<\/title>/<title>$current_title - Emby<\/title>/" /app/web/index.html
                echo "Updated single server title to: $current_title - Emby"
            fi
        fi

        # Create themed manifest and offline page based on single server type
        create_themed_manifest "$PRIMARY_SERVER" "$APP_TITLE"
        create_themed_offline "$PRIMARY_SERVER" "$APP_TITLE"

        # Apply theme based on single server type
        if [ "$PRIMARY_SERVER" = "jellyfin" ]; then
            apply_jellyfin_theme "/app/web/index.html"
        elif [ "$PRIMARY_SERVER" = "emby" ]; then
            apply_emby_theme "/app/web/index.html"
        else
            # No theme application needed - index.html is already Plex-themed
            echo "Plex is primary server - using default index.html styling"
        fi
    else
        echo "Multiple servers configured - setting up server dropdown functionality"

        # Create themed manifest and offline page based on primary server
        create_themed_manifest "$PRIMARY_SERVER" "$APP_TITLE"
        create_themed_offline "$PRIMARY_SERVER" "$APP_TITLE"

        # Use dropdown for 2+ servers (simplified logic)
        echo "Using dropdown menu for $server_count servers"
        configure_multi_server_dropdown

        # NOW apply themes after routes are created
        echo "Applying themes to all routes..."

        # Apply theme to main index based on primary server
        if [ "$PRIMARY_SERVER" = "jellyfin" ]; then
            apply_jellyfin_theme "/app/web/index.html"
        elif [ "$PRIMARY_SERVER" = "emby" ]; then
            apply_emby_theme "/app/web/index.html"
        fi
        # Plex primary needs no theme - it's the default

        # Apply themes to all secondary routes
        if [ -f "/app/web/plex/index.html" ]; then
            echo "Plex secondary route uses default styling"
        fi

        if [ -f "/app/web/jellyfin/index.html" ]; then
            apply_jellyfin_theme "/app/web/jellyfin/index.html"
        fi

        if [ -f "/app/web/emby/index.html" ]; then
            apply_emby_theme "/app/web/emby/index.html"
        fi
    fi

    echo "Configuration updated successfully"
else
    echo "Warning: index.html not found in /app/web/"
fi

# Run the corruption fix at the end to ensure all files are clean
fix_corrupted_files

# Create symlinks for data directories
# Remove existing symlink if it exists
rm -f /app/web/data

# Always create the main data symlink pointing to /app/data
ln -sf /app/data /app/web/data

# Ensure nginx configuration is correct
echo "<!DOCTYPE html><html><head><title>Nginx Test</title></head><body><h1>Nginx is working from /app/web!</h1></body></html>" >/app/web/test.html

# Run the initial data fetch - each server goes to its own directory
echo "Running initial data fetch"

# Fetch Plex data if configured
if [ -n "$PLEX_URL" ] && [ -n "$PLEX_TOKEN" ]; then
    echo "Fetching Plex data"
    PLEX_EXCLUDE_LIBRARIES="$PLEX_EXCLUDE_LIBRARIES" $PYTHON_PATH /app/scripts/plex_data_fetcher.py --url "$PLEX_URL" --token "$PLEX_TOKEN" --output /app/data/plex
fi

# Fetch Jellyfin data if configured
if [ -n "$JELLYFIN_URL" ] && [ -n "$JELLYFIN_TOKEN" ]; then
    echo "Fetching Jellyfin data"
    JELLYFIN_EXCLUDE_LIBRARIES="$JELLYFIN_EXCLUDE_LIBRARIES" $PYTHON_PATH /app/scripts/jellyfin_data_fetcher.py --url "$JELLYFIN_URL" --token "$JELLYFIN_TOKEN" --output /app/data/jellyfin
fi

# Fetch Emby data if configured (using jellyfin fetcher since APIs are compatible)
if [ -n "$EMBY_URL" ] && [ -n "$EMBY_TOKEN" ]; then
    echo "Fetching Emby data using Jellyfin API compatibility"
    EMBY_EXCLUDE_LIBRARIES="$EMBY_EXCLUDE_LIBRARIES" $PYTHON_PATH /app/scripts/jellyfin_data_fetcher.py --url "$EMBY_URL" --token "$EMBY_TOKEN" --output /app/data/emby
fi

# Make sure the data directory is accessible by nginx
chown -R www-data:www-data /app/data
chown -R www-data:www-data /app/web

# Print debugging info
echo "Checking Nginx configurations:"
ls -la /etc/nginx/conf.d/
ls -la /etc/nginx/sites-enabled/ || echo "No sites-enabled directory"
echo "Checking web directory:"
ls -la /app/web/
echo "Primary server: $PRIMARY_SERVER"
echo "Configured servers: $(count_configured_servers)"

# Start supervisor (which will start both nginx and cron)
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
