#!/usr/bin/env python3

import requests
import json
import os
import sys
from pathlib import Path
import argparse
from datetime import datetime
import time
import pwd
import grp
import hashlib
import pickle

class JellyfinDataFetcher:
    def __init__(self, jellyfin_url, jellyfin_token, output_dir="data/jellyfin", page_size=100, excluded_libraries=None):
        self.jellyfin_url = jellyfin_url.rstrip('/')
        self.jellyfin_token = jellyfin_token
        self.output_dir = Path(output_dir)
        self.page_size = page_size
        self.excluded_libraries = set(excluded_libraries or [])
        self.checksums_file = self.output_dir / "checksums.pkl"
        self.checksums = self.load_checksums()
        
        # Get www-data UID and GID
        try:
            self.www_data_uid = pwd.getpwnam('www-data').pw_uid
            self.www_data_gid = grp.getgrnam('www-data').gr_gid
        except KeyError:
            print("Warning: www-data user/group not found. File permissions will not be changed.")
            self.www_data_uid = self.www_data_gid = None
        
        # Setup directories after initializing UID/GID
        self.setup_directories()
        
        self.session = requests.Session()
        self.session.headers.update({
            'X-Emby-Token': self.jellyfin_token,
            'Accept': 'application/json'
        })

    def load_checksums(self):
        """Load existing checksums from file"""
        if os.path.exists(self.checksums_file):
            try:
                with open(self.checksums_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading checksums: {e}")
        return {}

    def save_checksums(self):
        """Save checksums to file"""
        try:
            with open(self.checksums_file, 'wb') as f:
                pickle.dump(self.checksums, f)
            self.set_permissions(self.checksums_file)
        except Exception as e:
            print(f"Error saving checksums: {e}")

    def set_permissions(self, path):
        """Set permissions to www-data:www-data"""
        if self.www_data_uid is not None and self.www_data_gid is not None:
            try:
                os.chown(path, self.www_data_uid, self.www_data_gid)
            except PermissionError:
                print(f"Warning: Insufficient permissions to change ownership of {path}. Run as root/sudo.")
            except Exception as e:
                print(f"Error setting permissions for {path}: {e}")

    def setup_directories(self):
        """Create necessary directory structure"""
        directories = [
            self.output_dir,
            self.output_dir / "posters" / "movies",
            self.output_dir / "posters" / "tvshows",
            self.output_dir / "backdrops" / "movies",
            self.output_dir / "backdrops" / "tvshows"
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.set_permissions(directory)

    def clean_existing_data(self):
        """Remove existing JSON files to ensure clean data"""
        movies_file = self.output_dir / "movies.json"
        tvshows_file = self.output_dir / "tvshows.json"
        
        for file_path in [movies_file, tvshows_file]:
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"Removed existing file: {file_path}")
                except Exception as e:
                    print(f"Warning: Could not remove {file_path}: {e}")

    def is_library_excluded(self, library_name, library_id):
        """Check if a library should be excluded based on name or ID"""
        if not self.excluded_libraries:
            return False
        
        # Check both library name and ID against exclusion list
        return (library_name in self.excluded_libraries or 
                str(library_id) in self.excluded_libraries)

    def get_user_id(self):
        """Get the first user's ID for API calls"""
        try:
            response = self.session.get(f"{self.jellyfin_url}/Users")
            response.raise_for_status()
            users = response.json()
            if users:
                return users[0]['Id']
            else:
                print("Error: No users found")
                return None
        except requests.RequestException as e:
            print(f"Error fetching users: {e}")
            return None

    def fetch_libraries(self, user_id):
        """Get all library collections using VirtualFolders endpoint

        Note: We use /Library/VirtualFolders instead of /Users/{user_id}/Views
        because Views returns combined/aggregate views (e.g., one "Movies" view for all
        movie libraries), while VirtualFolders returns each individual library separately.
        This allows importing from multiple libraries of the same type (e.g., "Movies"
        and "Private Movies").
        """
        try:
            response = self.session.get(f"{self.jellyfin_url}/Library/VirtualFolders")
            response.raise_for_status()
            # VirtualFolders returns a list directly, wrap it to match expected format
            libraries = response.json()
            return {'Items': libraries}
        except requests.RequestException as e:
            print(f"Error fetching libraries: {e}")
            return None

    def fetch_library_content(self, user_id, library_id, media_type):
        """Fetch all content from a specific library using pagination"""
        all_items = []
        start_index = 0
        
        while True:
            try:
                params = {
                    "ParentId": library_id,
                    "StartIndex": start_index,
                    "Limit": self.page_size,
                    "Recursive": "true",
                    "Fields": "Overview,Genres,People,Studios,DateCreated,RunTimeTicks,ProviderIds,ImageTags,BackdropImageTags",
                    "IncludeItemTypes": "Movie" if media_type == "movie" else "Series"
                }
                
                response = self.session.get(
                    f"{self.jellyfin_url}/Users/{user_id}/Items",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                print(f"API Response status: {response.status_code}")
                print(f"API Response data keys: {list(data.keys()) if data else 'No data'}")
                
                items = data.get('Items', [])
                items_count = len(items)
                
                if not items:
                    print(f"No items found for library {library_id}")
                    break
                    
                all_items.extend(items)
                
                print(f"  Fetched {items_count} items (offset: {start_index})")
                
                # If we got fewer items than requested, we've reached the end
                if items_count < self.page_size:
                    break
                    
                # Move to the next page
                start_index += self.page_size
                
                # Small delay to reduce server stress
                time.sleep(0.5)
                
            except requests.RequestException as e:
                print(f"Error fetching library content (offset: {start_index}): {e}")
                print(f"Response status: {getattr(e.response, 'status_code', 'No response')}")
                print(f"Response text: {getattr(e.response, 'text', 'No response text')}")
                break
        
        return all_items

    def get_series_info(self, user_id, series_id):
        """Get additional series information like episode and season count"""
        try:
            # Get seasons
            seasons_response = self.session.get(
                f"{self.jellyfin_url}/Shows/{series_id}/Seasons",
                params={"UserId": user_id}
            )
            seasons_response.raise_for_status()
            seasons_data = seasons_response.json()
            
            # Get episodes
            episodes_response = self.session.get(
                f"{self.jellyfin_url}/Shows/{series_id}/Episodes",
                params={"UserId": user_id}
            )
            episodes_response.raise_for_status()
            episodes_data = episodes_response.json()
            
            return {
                "season_count": len(seasons_data.get('Items', [])),
                "episode_count": len(episodes_data.get('Items', []))
            }
            
        except requests.RequestException as e:
            print(f"Error fetching series info for {series_id}: {e}")
            return {"season_count": 0, "episode_count": 0}

    def calculate_remote_md5(self, image_url):
        """Calculate MD5 hash of remote image"""
        try:
            response = self.session.get(image_url, stream=True)
            response.raise_for_status()
            
            md5_hash = hashlib.md5()
            for chunk in response.iter_content(chunk_size=4096):
                md5_hash.update(chunk)
            
            return md5_hash.hexdigest()
        except requests.RequestException as e:
            print(f"Error calculating MD5 for {image_url}: {e}")
            return None

    def download_image(self, image_url, output_path):
        """Download an image to the specified path if it has changed"""
        if not image_url:
            return False
        
        try:
            # Generate a key for the checksums dictionary
            checksum_key = f"{image_url}|{output_path}"
            
            # Calculate new MD5 checksum
            new_md5 = self.calculate_remote_md5(image_url)
            if not new_md5:
                return False
            
            # Check if file exists and compare checksums
            if output_path.exists():
                # Get the old checksum
                old_md5 = self.checksums.get(checksum_key)
                
                # If checksums match, file hasn't changed
                if old_md5 and old_md5 == new_md5:
                    print(f"Image unchanged, skipping: {output_path.name}")
                    return True
                else:
                    print(f"Image changed, downloading: {output_path.name}")
            else:
                print(f"New image, downloading: {output_path.name}")
            
            # Download the image
            response = self.session.get(image_url)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # Set permissions after creating the file
            self.set_permissions(output_path)
            
            # Update checksum in dictionary
            self.checksums[checksum_key] = new_md5
            
            return True
        except requests.RequestException as e:
            print(f"Error downloading image {image_url}: {e}")
            return False

    def process_media_item(self, item, media_type, user_id):
        """Process a single media item and extract relevant metadata"""
        try:
            print(f"Processing item: {item.get('Name', 'Unknown')} (Type: {item.get('Type', 'Unknown')})")
            
            # Convert Jellyfin timestamp to Unix timestamp (like Plex uses)
            added_at = 0
            if 'DateCreated' in item:
                try:
                    # Parse Jellyfin's ISO datetime format
                    dt = datetime.fromisoformat(item['DateCreated'].replace('Z', '+00:00'))
                    added_at = int(dt.timestamp())
                    print(f"  Parsed date: {item['DateCreated']} -> {added_at}")
                except Exception as e:
                    print(f"  Error parsing date {item['DateCreated']}: {e}")
                    added_at = 0

            # Extract common fields
            media_info = {
                'id': str(item.get('Id', '')),
                'title': item.get('Name', ''),
                'year': item.get('ProductionYear', ''),
                'summary': item.get('Overview', ''),
                'rating': item.get('CommunityRating', ''),
                'studio': '',
                'addedAt': added_at,
                'updatedAt': added_at,
                'genres': [],
                'actors': []
            }
            
            print(f"  Basic info: ID={media_info['id']}, Title={media_info['title']}, Year={media_info['year']}")
            
            # Extract studio information
            if 'Studios' in item and item['Studios']:
                media_info['studio'] = item['Studios'][0].get('Name', '')
                print(f"  Studio: {media_info['studio']}")
            
            # Extract genre information
            if 'Genres' in item:
                media_info['genres'] = item['Genres']
                print(f"  Genres: {media_info['genres']}")
            
            # Extract actor information (limit to main 3 cast members)
            if 'People' in item:
                actors_count = 0
                for person in item['People']:
                    if person.get('Type') == 'Actor' and actors_count < 3:
                        actor_info = {
                            'name': person.get('Name', ''),
                            'role': person.get('Role', '')
                        }
                        media_info['actors'].append(actor_info)
                        actors_count += 1
                print(f"  Cast: {len(media_info['actors'])} actors")
            
            if media_type == 'movie':
                # Convert runtime from ticks to milliseconds (like Plex format)
                duration_ms = 0
                if 'RunTimeTicks' in item:
                    # Jellyfin uses ticks (100 nanoseconds), convert to milliseconds
                    duration_ms = item['RunTimeTicks'] // 10000
                    print(f"  Runtime: {item['RunTimeTicks']} ticks -> {duration_ms} ms")
                
                media_info.update({
                    'duration': duration_ms,
                    'contentRating': item.get('OfficialRating', ''),
                    'originallyAvailableAt': item.get('PremiereDate', ''),
                    'tagline': item.get('Taglines', [''])[0] if item.get('Taglines') else ''
                })
            elif media_type == 'tvshow':
                # Get series info for episode and season counts
                series_info = self.get_series_info(user_id, item['Id'])
                print(f"  Series info: {series_info['season_count']} seasons, {series_info['episode_count']} episodes")
                
                media_info.update({
                    'leafCount': series_info['episode_count'],  # episode count
                    'childCount': series_info['season_count'],  # season count
                    'contentRating': item.get('OfficialRating', ''),
                    'originallyAvailableAt': item.get('PremiereDate', '')
                })
            
            print(f"  ✓ Successfully processed: {media_info['title']}")
            return media_info
        except Exception as e:
            print(f"  ✗ Error processing media item {item.get('Name', 'Unknown')}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_and_save_data(self):
        """Main method to fetch all data and save it"""
        print(f"Starting Jellyfin data fetch at {datetime.now()}")
        print(f"Jellyfin URL: {self.jellyfin_url}")
        
        if self.excluded_libraries:
            print(f"Excluded libraries: {', '.join(self.excluded_libraries)}")
        
        # Clean existing data files
        self.clean_existing_data()
        
        # Get user ID
        user_id = self.get_user_id()
        if not user_id:
            print("Failed to get user ID")
            return
        
        print(f"Using user ID: {user_id}")
        
        # Get all libraries
        libraries_data = self.fetch_libraries(user_id)
        if not libraries_data or 'Items' not in libraries_data:
            print("Failed to fetch libraries")
            print(f"Libraries response: {libraries_data}")
            return
        
        libraries = libraries_data['Items']
        print(f"Found {len(libraries)} libraries")
        
        movies_data = []
        tvshows_data = []
        
        for library in libraries:
            # VirtualFolders uses 'ItemId', Views uses 'Id' - support both
            library_id = library.get('ItemId') or library.get('Id')
            library_type = library.get('CollectionType')
            library_name = library.get('Name')

            print(f"\nProcessing library: {library_name} (Type: {library_type}, ID: {library_id})")
            
            # Check if this library should be excluded
            if self.is_library_excluded(library_name, library_id):
                print(f"Skipping excluded library: {library_name}")
                continue
            
            if library_type not in ['movies', 'tvshows']:
                print(f"Skipping unsupported library type: {library_type}")
                continue
            
            # Fetch content for this library
            media_type = 'movie' if library_type == 'movies' else 'tvshow'
            items = self.fetch_library_content(user_id, library_id, media_type)
            
            print(f"Found {len(items)} items in {library_name}")
            
            for i, item in enumerate(items):
                print(f"Processing item {i+1}/{len(items)}: {item.get('Name', 'Unknown')}")
                media_info = self.process_media_item(item, media_type, user_id)
                
                if media_info:
                    # Determine output paths
                    poster_dir = self.output_dir / "posters" / f"{media_type}s"
                    poster_path = poster_dir / f"{media_info['id']}.jpg"
                    
                    # Download poster (Primary image)
                    if 'ImageTags' in item and 'Primary' in item['ImageTags']:
                        poster_url = f"{self.jellyfin_url}/Items/{item['Id']}/Images/Primary"
                        print(f"Downloading poster from: {poster_url}")
                        success = self.download_image(poster_url, poster_path)
                        if success:
                            print(f"✓ Processed poster for: {media_info['title']}")
                        else:
                            print(f"✗ Failed to process poster for: {media_info['title']}")
                    else:
                        print(f"No poster available for: {media_info['title']}")
                    
                    # Download backdrop (Backdrop image)
                    if 'BackdropImageTags' in item and item['BackdropImageTags']:
                        backdrop_dir = self.output_dir / "backdrops" / f"{media_type}s"
                        backdrop_path = backdrop_dir / f"{media_info['id']}.jpg"
                        backdrop_url = f"{self.jellyfin_url}/Items/{item['Id']}/Images/Backdrop/0"
                        print(f"Downloading backdrop from: {backdrop_url}")
                        success = self.download_image(backdrop_url, backdrop_path)
                        if success:
                            print(f"✓ Processed backdrop for: {media_info['title']}")
                        else:
                            print(f"✗ Failed to process backdrop for: {media_info['title']}")
                    else:
                        print(f"No backdrop available for: {media_info['title']}")
                    
                    # Add to appropriate list
                    if media_type == 'movie':
                        movies_data.append(media_info)
                    else:
                        tvshows_data.append(media_info)
                else:
                    print(f"Failed to process media info for: {item.get('Name', 'Unknown')}")
        
        # Save JSON files
        movies_file = self.output_dir / "movies.json"
        tvshows_file = self.output_dir / "tvshows.json"
        
        print(f"\nSaving {len(movies_data)} movies to: {movies_file}")
        with open(movies_file, 'w') as f:
            json.dump(movies_data, f, indent=2)
        self.set_permissions(movies_file)
        
        print(f"Saving {len(tvshows_data)} TV shows to: {tvshows_file}")
        with open(tvshows_file, 'w') as f:
            json.dump(tvshows_data, f, indent=2)
        self.set_permissions(tvshows_file)
        
        # Save checksums
        self.save_checksums()
        
        print(f"\nData fetch completed at {datetime.now()}")
        print(f"Movies: {len(movies_data)}")
        print(f"TV Shows: {len(tvshows_data)}")
        print(f"Data saved to: {self.output_dir}")
        
        # List the files that were created
        print(f"\nFiles created:")
        if movies_file.exists():
            print(f"✓ {movies_file} ({movies_file.stat().st_size} bytes)")
        if tvshows_file.exists():
            print(f"✓ {tvshows_file} ({tvshows_file.stat().st_size} bytes)")
        
        print(f"\nDirectory contents: {list(self.output_dir.iterdir())}")

def main():
    # Get values from environment variables first
    default_url = os.environ.get('JELLYFIN_URL', '')
    default_token = os.environ.get('JELLYFIN_TOKEN', '')
    default_output = os.environ.get('OUTPUT_DIR', 'data/jellyfin')
    default_page_size = int(os.environ.get('PAGE_SIZE', '100'))
    
    # Get excluded libraries from environment variable
    # Check for EMBY_EXCLUDE_LIBRARIES first (for Emby), fall back to JELLYFIN_EXCLUDE_LIBRARIES
    excluded_libraries_str = os.environ.get('EMBY_EXCLUDE_LIBRARIES') or os.environ.get('JELLYFIN_EXCLUDE_LIBRARIES', '')
    excluded_libraries = [lib.strip() for lib in excluded_libraries_str.split(',') if lib.strip()] if excluded_libraries_str else []
    
    parser = argparse.ArgumentParser(description='Fetch Jellyfin media data and posters')
    
    # Use environment variables as defaults
    parser.add_argument('--url', default=default_url, help='Jellyfin server URL (e.g., http://localhost:8096)')
    parser.add_argument('--token', default=default_token, help='Jellyfin API token')
    parser.add_argument('--output', default=default_output, help='Output directory (default: data/jellyfin)')
    parser.add_argument('--page-size', type=int, default=default_page_size, help='Number of items per page (default: 100)')
    parser.add_argument('--exclude-libraries', nargs='*', default=excluded_libraries, 
                        help='Libraries to exclude (library names or IDs, space-separated)')
    
    # Handle special case for tokens with leading hyphens
    for i, arg in enumerate(sys.argv):
        if arg == '--token' and i + 1 < len(sys.argv) and sys.argv[i + 1].startswith('-') and not sys.argv[i + 1].startswith('--'):
            sys.argv[i:i+2] = [f'--token={sys.argv[i+1]}']
            break
    
    args = parser.parse_args()
    
    # Validate required parameters
    if not args.url:
        print("Error: Jellyfin URL is required. Set with --url or JELLYFIN_URL environment variable.")
        sys.exit(1)
    if not args.token:
        print("Error: Jellyfin token is required. Set with --token or JELLYFIN_TOKEN environment variable.")
        sys.exit(1)
    
    fetcher = JellyfinDataFetcher(args.url, args.token, args.output, args.page_size, args.exclude_libraries)
    fetcher.fetch_and_save_data()

if __name__ == "__main__":
    main()