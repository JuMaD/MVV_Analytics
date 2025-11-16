"""
Configuration for Munich Transit Reachability Map
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""

    # GTFS Data Source
    GTFS_URL: str = "https://www.mvv-muenchen.de/fileadmin/mediapool/02-Fahrplanauskunft/03-Downloads/openData/gesamt_gtfs.zip"
    GTFS_INFO_URL: str = "https://www.mvv-muenchen.de/fahrplanauskunft/fuer-entwickler/opendata/index.html"

    # Data Attribution (REQUIRED)
    DATA_SOURCE: str = "Münchner Verkehrs- und Tarifverbund GmbH (MVV)"

    # Local Storage Paths
    DATA_DIR: str = "static/data"
    GTFS_ZIP_PATH: str = "static/data/gtfs.zip"
    GTFS_EXTRACT_DIR: str = "static/data/gtfs"
    GRAPH_DIR: str = "static/data/graphs"
    METADATA_PATH: str = "static/data/metadata.json"

    # GCP Settings (optional for local development)
    GCP_PROJECT_ID: Optional[str] = None
    GCS_BUCKET_NAME: Optional[str] = None
    GCS_GTFS_PATH: str = "gtfs_data/current.zip"
    GCS_METADATA_PATH: str = "gtfs_data/metadata.json"

    # Map Center (Munich)
    MAP_CENTER_LAT: float = 48.1351
    MAP_CENTER_LON: float = 11.5820

    # Transit Parameters
    DEFAULT_TRANSFER_TIME: int = 180  # 3 minutes in seconds
    MAX_CALCULATION_TIME: int = 3600  # 60 minutes in seconds

    # Animation Parameters
    DEFAULT_TIME_STEP_MINUTES: int = 5
    ANIMATION_FRAME_DURATION_MS: int = 1000  # 1 second per frame

    # API Settings
    API_PREFIX: str = "/api"
    ADMIN_TOKEN: Optional[str] = None

    # Performance
    CACHE_GRAPHS: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure directories exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.GTFS_EXTRACT_DIR, exist_ok=True)
os.makedirs(settings.GRAPH_DIR, exist_ok=True)
