#!/usr/bin/env python3

import requests
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

import snapshot_io

class PlexDataFetcher:
    def __init__(self, plex_url, plex_token, output_dir="data", page_size=100, excluded_libraries=None):
        self.plex_url = plex_url.rstrip('/')
        self.plex_token = plex_token
        self.output_dir = Path(output_dir)
        self.page_size = page_size  # Number of items per page
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
            'X-Plex-Token': self.plex_token,
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

    def publish_snapshots(self, movies_data, tvshows_data):
        """Publish both snapshots, or neither.

        There is deliberately no counterpart that removes them first. This used
        to open a run by deleting movies.json and tvshows.json, so the site
        reported "Failed to load movie data" for the whole import and a run that
        gave up part way left the library deleted until a later one succeeded.
        See scripts/snapshot_io.py.
        """
        movies_file = self.output_dir / "movies.json"
        tvshows_file = self.output_dir / "tvshows.json"

        print(f"\nSaving {len(movies_data)} movies to: {movies_file}")
        print(f"Saving {len(tvshows_data)} TV shows to: {tvshows_file}")

        snapshot_io.publish_json(
            [(movies_file, movies_data), (tvshows_file, tvshows_data)],
            prepare=self.set_permissions,
        )

    def is_library_excluded(self, library_name, library_id):
        """Check if a library should be excluded based on name or ID"""
        if not self.excluded_libraries:
            return False
        
        # Check both library name and ID against exclusion list
        return (library_name in self.excluded_libraries or 
                str(library_id) in self.excluded_libraries)

    def fetch_sections(self):
        """Get all library sections"""
        try:
            response = self.session.get(f"{self.plex_url}/library/sections")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching sections: {e}")
            return None

    def fetch_detailed_metadata(self, rating_key):
        """Fetch detailed metadata for a specific item including cast roles"""
        try:
            response = self.session.get(f"{self.plex_url}/library/metadata/{rating_key}")
            response.raise_for_status()
            data = response.json()
            
            if 'MediaContainer' in data and 'Metadata' in data['MediaContainer']:
                return data['MediaContainer']['Metadata'][0]
            return None
        except requests.RequestException as e:
            print(f"Error fetching detailed metadata for {rating_key}: {e}")
            return None

    def fetch_section_content(self, section_key):
        """Fetch all content from a specific section using pagination"""
        all_items = []
        offset = 0
        
        while True:
            try:
                # Fetch items with pagination
                response = self.session.get(
                    f"{self.plex_url}/library/sections/{section_key}/all",
                    params={"X-Plex-Container-Start": offset, "X-Plex-Container-Size": self.page_size}
                )
                response.raise_for_status()
                data = response.json()
                
                if 'MediaContainer' not in data:
                    break
                    
                items = data['MediaContainer'].get('Metadata', [])
                items_count = len(items)
                
                if not items:
                    break
                    
                all_items.extend(items)
                
                print(f"  Fetched {items_count} items (offset: {offset})")
                
                # If we got fewer items than requested, we've reached the end
                if items_count < self.page_size:
                    break
                    
                # Move to the next page
                offset += self.page_size
                
                # Small delay to reduce server stress
                time.sleep(0.5)
                
            except requests.RequestException as e:
                print(f"Error fetching section content (offset: {offset}): {e}")
                break
        
        # Return in the same format as the original function
        return {'MediaContainer': {'Metadata': all_items}} if all_items else None

    def calculate_remote_md5(self, image_url):
        """Calculate MD5 hash of remote image"""
        try:
            response = self.session.get(f"{self.plex_url}{image_url}", stream=True)
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
            response = self.session.get(f"{self.plex_url}{image_url}")
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

    def process_media_item(self, item, media_type):
        """Process a single media item and extract relevant metadata"""
        try:
            rating_key = item.get('ratingKey', '')
            
            # Fetch detailed metadata to get cast with roles
            detailed_item = self.fetch_detailed_metadata(rating_key)
            if detailed_item:
                # Use detailed metadata if available, otherwise fall back to basic item
                item = detailed_item
            
            # Extract common fields
            media_info = {
                'id': str(rating_key),
                'title': item.get('title', ''),
                'year': item.get('year', ''),
                'summary': item.get('summary', ''),
                'rating': item.get('rating', ''),
                'studio': item.get('studio', ''),
                'addedAt': item.get('addedAt', ''),
                'updatedAt': item.get('updatedAt', ''),
                'genres': [],
                'actors': []
            }
            
            # Extract genre information
            if 'Genre' in item:
                for genre in item['Genre']:
                    media_info['genres'].append(genre.get('tag', ''))
            
            # Extract actor information with improved role detection
            # Try multiple possible field names and approaches
            actors_found = False
            
            # First try 'Role' field (most common)
            if 'Role' in item and not actors_found:
                print(f"  Found Role field with {len(item['Role'])} actors")
                for role in item['Role']:
                    actor_info = {
                        'name': role.get('tag', ''),
                        'role': role.get('role', '')
                    }
                    media_info['actors'].append(actor_info)
                actors_found = True
            
            # If 'Role' doesn't exist or is empty, try 'Actor' field
            if 'Actor' in item and not actors_found:
                print(f"  Found Actor field with {len(item['Actor'])} actors")
                for actor in item['Actor']:
                    actor_info = {
                        'name': actor.get('tag', ''),
                        'role': actor.get('role', '')
                    }
                    media_info['actors'].append(actor_info)
                actors_found = True
            
            # Try 'Cast' field as a fallback
            if 'Cast' in item and not actors_found:
                print(f"  Found Cast field with {len(item['Cast'])} actors")
                for cast in item['Cast']:
                    actor_info = {
                        'name': cast.get('tag', ''),
                        'role': cast.get('role', '')
                    }
                    media_info['actors'].append(actor_info)
                actors_found = True
            
            # If we still don't have actors, try to get them from a different API endpoint
            if not actors_found and rating_key:
                print(f"  No actors found in standard fields, trying alternative approach...")
                try:
                    # Try fetching cast information separately
                    cast_response = self.session.get(f"{self.plex_url}/library/metadata/{rating_key}/cast")
                    if cast_response.status_code == 200:
                        cast_data = cast_response.json()
                        if 'MediaContainer' in cast_data and 'Metadata' in cast_data['MediaContainer']:
                            for cast_member in cast_data['MediaContainer']['Metadata']:
                                actor_info = {
                                    'name': cast_member.get('tag', ''),
                                    'role': cast_member.get('role', '')
                                }
                                media_info['actors'].append(actor_info)
                            actors_found = True
                            print(f"  Found {len(media_info['actors'])} actors from cast endpoint")
                except Exception as e:
                    print(f"  Error fetching cast from alternative endpoint: {e}")
            
            # Limit to first 3 actors to match Jellyfin behavior
            if len(media_info['actors']) > 3:
                media_info['actors'] = media_info['actors'][:3]
            
            print(f"  Final cast count: {len(media_info['actors'])}")
            for i, actor in enumerate(media_info['actors']):
                print(f"    {i+1}. {actor['name']} as '{actor['role']}'")
            
            if media_type == 'movie':
                media_info.update({
                    'duration': item.get('duration', ''),
                    'contentRating': item.get('contentRating', ''),
                    'originallyAvailableAt': item.get('originallyAvailableAt', ''),
                    'tagline': item.get('tagline', '')
                })
            elif media_type == 'tvshow':
                media_info.update({
                    'leafCount': item.get('leafCount', ''),  # episode count
                    'childCount': item.get('childCount', ''),  # season count
                    'contentRating': item.get('contentRating', ''),
                    'originallyAvailableAt': item.get('originallyAvailableAt', '')
                })
            
            return media_info
        except Exception as e:
            print(f"Error processing media item: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_and_save_data(self):
        """Fetch all data and save it. Returns True on success, False on failure.

        The return value is load-bearing: the entrypoint records a settings
        fingerprint only after a fetch that succeeded, so that a failed one is
        retried on the next start rather than skipped. Returning False here is
        what becomes a non-zero exit status in main().
        """
        print(f"Starting Plex data fetch at {datetime.now()}")

        if self.excluded_libraries:
            print(f"Excluded libraries: {', '.join(self.excluded_libraries)}")

        # Nothing is removed here. The previous snapshot stays published and
        # served until a complete new one is ready to replace it.

        # Get all sections
        sections_data = self.fetch_sections()
        if not sections_data or 'MediaContainer' not in sections_data:
            print("Failed to fetch sections")
            return False

        sections = sections_data['MediaContainer'].get('Directory', [])
        
        movies_data = []
        tvshows_data = []
        
        for section in sections:
            section_key = section.get('key')
            section_type = section.get('type')
            section_title = section.get('title')
            
            print(f"\nProcessing section: {section_title} (Type: {section_type})")
            
            # Check if this library should be excluded
            if self.is_library_excluded(section_title, section_key):
                print(f"Skipping excluded library: {section_title}")
                continue
            
            if section_type not in ['movie', 'show']:
                print(f"Skipping unsupported section type: {section_type}")
                continue
            
            # Fetch content for this section
            content_data = self.fetch_section_content(section_key)
            if not content_data or 'MediaContainer' not in content_data:
                continue
            
            items = content_data['MediaContainer'].get('Metadata', [])
            print(f"Found {len(items)} items in {section_title}")
            
            for i, item in enumerate(items):
                print(f"Processing item {i+1}/{len(items)}: {item.get('title', 'Unknown')}")
                media_type = 'movie' if section_type == 'movie' else 'tvshow'
                media_info = self.process_media_item(item, media_type)
                
                if media_info:
                    # Determine output paths
                    poster_dir = self.output_dir / "posters" / f"{media_type}s"
                    poster_path = poster_dir / f"{media_info['id']}.jpg"
                    
                    # Download poster
                    poster_url = item.get('thumb')
                    if poster_url:
                        success = self.download_image(poster_url, poster_path)
                        if success:
                            print(f"  ✓ Processed poster for: {media_info['title']}")
                        else:
                            print(f"  ✗ Failed to process poster for: {media_info['title']}")
                    
                    # Download backdrop/art image if available
                    backdrop_url = item.get('art')
                    if backdrop_url:
                        backdrop_dir = self.output_dir / "backdrops" / f"{media_type}s"
                        backdrop_path = backdrop_dir / f"{media_info['id']}.jpg"
                        success = self.download_image(backdrop_url, backdrop_path)
                        if success:
                            print(f"  ✓ Processed backdrop for: {media_info['title']}")
                        else:
                            print(f"  ✗ Failed to process backdrop for: {media_info['title']}")
                    
                    # Add to appropriate list
                    if media_type == 'movie':
                        movies_data.append(media_info)
                    else:
                        tvshows_data.append(media_info)
                
                # Add a small delay between items to reduce server load
                time.sleep(0.1)
        
        # Publish both snapshots together, replacing the previous pair
        self.publish_snapshots(movies_data, tvshows_data)

        # Save checksums
        self.save_checksums()

        print(f"\nData fetch completed at {datetime.now()}")
        print(f"Movies: {len(movies_data)}")
        print(f"TV Shows: {len(tvshows_data)}")
        print(f"Data saved to: {self.output_dir}")
        return True

def main():
    # Get values from environment variables first
    default_url = os.environ.get('PLEX_URL', '')
    default_token = os.environ.get('PLEX_TOKEN', '')
    default_output = os.environ.get('OUTPUT_DIR', 'data')
    default_page_size = int(os.environ.get('PAGE_SIZE', '100'))
    
    # Get excluded libraries from environment variable
    excluded_libraries_str = os.environ.get('PLEX_EXCLUDE_LIBRARIES', '')
    excluded_libraries = [lib.strip() for lib in excluded_libraries_str.split(',') if lib.strip()] if excluded_libraries_str else []
    
    parser = argparse.ArgumentParser(description='Fetch Plex media data and posters')
    
    # Use environment variables as defaults
    parser.add_argument('--url', default=default_url, help='Plex server URL (e.g., http://localhost:32400)')
    parser.add_argument('--token', default=default_token, help='Plex authentication token')
    parser.add_argument('--output', default=default_output, help='Output directory (default: data)')
    parser.add_argument('--page-size', type=int, default=default_page_size, help='Number of items per page (default: 100)')
    parser.add_argument('--exclude-libraries', nargs='*', default=excluded_libraries, 
                        help='Libraries to exclude (library names or IDs, space-separated)')
    
    # Handle special case for tokens with leading hyphens
    # This allows using "=" syntax for the token (--token=-abc123)
    for i, arg in enumerate(sys.argv):
        if arg == '--token' and i + 1 < len(sys.argv) and sys.argv[i + 1].startswith('-') and not sys.argv[i + 1].startswith('--'):
            sys.argv[i:i+2] = [f'--token={sys.argv[i+1]}']
            break
    
    args = parser.parse_args()
    
    # Validate required parameters
    if not args.url:
        print("Error: Plex URL is required. Set with --url or PLEX_URL environment variable.")
        sys.exit(1)
    if not args.token:
        print("Error: Plex token is required. Set with --token or PLEX_TOKEN environment variable.")
        sys.exit(1)
    
    fetcher = PlexDataFetcher(args.url, args.token, args.output, args.page_size, args.exclude_libraries)
    # Exit non-zero on failure. The caller has to be able to tell a fetch that
    # worked from one that did not: the entrypoint records a settings
    # fingerprint only after a success, and cron logs one that failed.
    if not fetcher.fetch_and_save_data():
        sys.exit(1)

if __name__ == "__main__":
    main()