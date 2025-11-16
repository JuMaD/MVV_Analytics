#!/usr/bin/env python3
"""
Initialize data for Munich Transit Reachability Map

This script:
1. Downloads GTFS data from MVV
2. Validates the data
3. Builds transit network graphs for all day types
4. Saves graphs for use by the API

Run this before starting the application for the first time.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.data.gtfs_downloader import GTFSDownloader
from backend.graph.graph_builder import TransitGraphBuilder


def main():
    print("=" * 70)
    print("Munich Transit Reachability Map - Data Initialization")
    print("=" * 70)
    print()

    # Step 1: Download GTFS data
    print("Step 1: Downloading GTFS data from MVV...")
    print("-" * 70)

    downloader = GTFSDownloader(use_gcs=False)

    try:
        downloader.force_download()
    except Exception as e:
        print(f"ERROR: Failed to download GTFS data: {e}")
        return 1

    print()

    # Step 2: Build graphs
    print("Step 2: Building transit network graphs...")
    print("-" * 70)

    builder = TransitGraphBuilder()

    try:
        builder.build_all_graphs()
        builder.save_graphs()
    except Exception as e:
        print(f"ERROR: Failed to build graphs: {e}")
        return 1

    print()
    print("=" * 70)
    print("Data initialization complete!")
    print("=" * 70)
    print()
    print("You can now start the application with:")
    print("  uvicorn backend.api.app:app --reload")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
