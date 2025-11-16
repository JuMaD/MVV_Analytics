"""
GTFS Data Downloader and Update Checker
"""
import hashlib
import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None

from backend.config import settings


class GTFSDownloader:
    """Handles downloading and updating GTFS data"""

    def __init__(self, use_gcs: bool = False):
        """
        Initialize downloader

        Args:
            use_gcs: If True, use Google Cloud Storage. If False, use local storage.
        """
        self.use_gcs = use_gcs and GCS_AVAILABLE
        self.gcs_client = None
        self.bucket = None

        if self.use_gcs and settings.GCS_BUCKET_NAME and storage:
            self.gcs_client = storage.Client(project=settings.GCP_PROJECT_ID)
            self.bucket = self.gcs_client.bucket(settings.GCS_BUCKET_NAME)

    def download_gtfs(self, url: str = None) -> Path:
        """
        Download GTFS zip file

        Args:
            url: URL to download from (defaults to MVV GTFS URL)

        Returns:
            Path to downloaded zip file
        """
        url = url or settings.GTFS_URL
        zip_path = Path(settings.GTFS_ZIP_PATH)

        print(f"Downloading GTFS data from {url}...")

        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        # Download with progress
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0

        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"Downloaded: {percent:.1f}%", end='\r')

        print(f"\nDownload complete: {zip_path}")
        return zip_path

    def compute_checksum(self, file_path: Path) -> str:
        """
        Compute SHA-256 checksum of a file

        Args:
            file_path: Path to file

        Returns:
            SHA-256 hex digest
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def extract_gtfs(self, zip_path: Path, extract_dir: Path = None) -> Path:
        """
        Extract GTFS zip file

        Args:
            zip_path: Path to zip file
            extract_dir: Directory to extract to (defaults to settings.GTFS_EXTRACT_DIR)

        Returns:
            Path to extracted directory
        """
        extract_dir = extract_dir or Path(settings.GTFS_EXTRACT_DIR)

        print(f"Extracting GTFS data to {extract_dir}...")

        # Remove existing directory
        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        print(f"Extraction complete")
        return extract_dir

    def validate_gtfs(self, gtfs_dir: Path) -> bool:
        """
        Validate GTFS data structure

        Args:
            gtfs_dir: Path to GTFS directory

        Returns:
            True if valid, False otherwise
        """
        required_files = [
            'agency.txt',
            'stops.txt',
            'routes.txt',
            'trips.txt',
            'stop_times.txt',
            'calendar.txt'
        ]

        print("Validating GTFS data...")

        for filename in required_files:
            file_path = gtfs_dir / filename
            if not file_path.exists():
                print(f"ERROR: Required file missing: {filename}")
                return False
            print(f"  ✓ {filename}")

        # Check for optional files
        optional_files = ['calendar_dates.txt', 'transfers.txt', 'feed_info.txt']
        for filename in optional_files:
            file_path = gtfs_dir / filename
            if file_path.exists():
                print(f"  ✓ {filename} (optional)")

        print("GTFS validation successful")
        return True

    def extract_feed_version(self, gtfs_dir: Path) -> Optional[str]:
        """
        Extract feed version from feed_info.txt if available

        Args:
            gtfs_dir: Path to GTFS directory

        Returns:
            Feed version string or None
        """
        feed_info_path = gtfs_dir / 'feed_info.txt'

        if not feed_info_path.exists():
            return None

        try:
            import pandas as pd
            df = pd.read_csv(feed_info_path)

            if 'feed_version' in df.columns and len(df) > 0:
                return str(df['feed_version'].iloc[0])
        except Exception as e:
            print(f"Warning: Could not read feed_info.txt: {e}")

        return None

    def load_metadata(self) -> Dict:
        """
        Load metadata from storage

        Returns:
            Metadata dictionary
        """
        if self.use_gcs and self.bucket:
            # Load from GCS
            blob = self.bucket.blob(settings.GCS_METADATA_PATH)
            if blob.exists():
                return json.loads(blob.download_as_text())
        else:
            # Load from local file
            metadata_path = Path(settings.METADATA_PATH)
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    return json.load(f)

        # Return empty metadata if doesn't exist
        return {
            'checksum': None,
            'download_date': None,
            'feed_version': None,
            'last_updated': None
        }

    def save_metadata(self, metadata: Dict):
        """
        Save metadata to storage

        Args:
            metadata: Metadata dictionary
        """
        metadata_json = json.dumps(metadata, indent=2)

        if self.use_gcs and self.bucket:
            # Save to GCS
            blob = self.bucket.blob(settings.GCS_METADATA_PATH)
            blob.upload_from_string(metadata_json, content_type='application/json')
        else:
            # Save to local file
            metadata_path = Path(settings.METADATA_PATH)
            with open(metadata_path, 'w') as f:
                f.write(metadata_json)

        print(f"Metadata saved: {metadata}")

    def check_and_update(self) -> bool:
        """
        Check for GTFS updates and download if new version available

        Returns:
            True if updated, False if no update needed
        """
        print("Checking for GTFS updates...")

        # Download new zip
        zip_path = self.download_gtfs()

        # Compute checksum
        new_checksum = self.compute_checksum(zip_path)
        print(f"New checksum: {new_checksum}")

        # Load current metadata
        metadata = self.load_metadata()
        current_checksum = metadata.get('checksum')
        print(f"Current checksum: {current_checksum}")

        if new_checksum == current_checksum:
            print("No update needed - checksums match")
            return False

        print("New version detected - updating...")

        # Extract
        extract_dir = self.extract_gtfs(zip_path)

        # Validate
        if not self.validate_gtfs(extract_dir):
            print("ERROR: GTFS validation failed - keeping old version")
            return False

        # Extract feed version
        feed_version = self.extract_feed_version(extract_dir)

        # Update metadata
        new_metadata = {
            'checksum': new_checksum,
            'download_date': datetime.now().strftime('%Y-%m-%d'),
            'feed_version': feed_version,
            'last_updated': datetime.now().isoformat()
        }

        self.save_metadata(new_metadata)

        print("GTFS update complete!")
        return True

    def force_download(self):
        """Force download and extraction of GTFS data"""
        print("Force downloading GTFS data...")

        # Download
        zip_path = self.download_gtfs()

        # Extract
        extract_dir = self.extract_gtfs(zip_path)

        # Validate
        if not self.validate_gtfs(extract_dir):
            raise ValueError("GTFS validation failed")

        # Compute checksum and save metadata
        checksum = self.compute_checksum(zip_path)
        feed_version = self.extract_feed_version(extract_dir)

        metadata = {
            'checksum': checksum,
            'download_date': datetime.now().strftime('%Y-%m-%d'),
            'feed_version': feed_version,
            'last_updated': datetime.now().isoformat()
        }

        self.save_metadata(metadata)

        print("Force download complete!")


if __name__ == "__main__":
    # Test the downloader
    downloader = GTFSDownloader(use_gcs=False)
    downloader.force_download()
