#!/usr/bin/env python3
"""
Cloud Scheduler handler for GTFS updates

This script is designed to be run as a Cloud Scheduler job.
It checks for GTFS updates and rebuilds graphs if needed.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.data.gtfs_downloader import GTFSDownloader
from backend.graph.graph_builder import TransitGraphBuilder
from backend.config import settings


def main():
    print("=" * 70)
    print("Munich Transit Reachability Map - Update Check")
    print("=" * 70)
    print()

    # Determine if we should use GCS
    use_gcs = bool(settings.GCS_BUCKET_NAME and settings.GCP_PROJECT_ID)

    print(f"Storage mode: {'GCS' if use_gcs else 'Local'}")
    if use_gcs:
        print(f"GCS Bucket: {settings.GCS_BUCKET_NAME}")
    print()

    # Check for updates
    downloader = GTFSDownloader(use_gcs=use_gcs)

    try:
        updated = downloader.check_and_update()

        if updated:
            print()
            print("New GTFS data detected - rebuilding graphs...")
            print("-" * 70)

            builder = TransitGraphBuilder()
            builder.build_all_graphs()
            builder.save_graphs()

            print()
            print("Update complete!")
            return 0
        else:
            print("No update needed - data is current")
            return 0

    except Exception as e:
        print(f"ERROR: Update failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
