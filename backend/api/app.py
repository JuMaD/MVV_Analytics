"""
FastAPI Application for Munich Transit Reachability Map
"""
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.api.models import (
    StopInfo,
    MetadataResponse,
    ReachabilityRequest,
    ReachabilityResponse,
    ReachabilityTimelineRequest,
    ReachabilityTimelineResponse,
    UpdateResponse
)
from backend.data.gtfs_downloader import GTFSDownloader
from backend.graph.graph_builder import TransitGraphBuilder
from backend.graph.reachability import ReachabilityCalculator


# Initialize FastAPI app
app = FastAPI(
    title="Munich Transit Reachability Map",
    description="Interactive visualization of Munich public transit reachability",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
calculator: Optional[ReachabilityCalculator] = None


def load_calculator():
    """Load or reload the reachability calculator with current graphs"""
    global calculator

    try:
        builder = TransitGraphBuilder()
        graphs = builder.load_graphs()
        calculator = ReachabilityCalculator(graphs)
        print("Reachability calculator loaded successfully")
    except FileNotFoundError:
        print("Graphs not found - need to build them first")
        calculator = None


# Load calculator on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    print("Starting Munich Transit Reachability Map API...")

    # Check if graphs exist, if not, try to build them
    graph_dir = Path(settings.GRAPH_DIR)
    graph_files = list(graph_dir.glob("graph_*.pkl"))

    if len(graph_files) < 3:
        print("Graphs not found - checking for GTFS data...")

        # Check if GTFS data exists
        gtfs_dir = Path(settings.GTFS_EXTRACT_DIR)
        if not gtfs_dir.exists() or not (gtfs_dir / 'stops.txt').exists():
            print("GTFS data not found - please download first")
            print("Run: python -m backend.data.gtfs_downloader")
        else:
            print("Building graphs from existing GTFS data...")
            builder = TransitGraphBuilder()
            builder.build_all_graphs()
            builder.save_graphs()

    # Load calculator
    load_calculator()


@app.get("/")
async def root():
    """Serve the main application page"""
    return FileResponse("frontend/index.html")


@app.get(f"{settings.API_PREFIX}/stops", response_model=List[StopInfo])
async def get_stops(day_type: str = "weekday"):
    """
    Get all transit stops

    Args:
        day_type: Day type for graph selection (weekday, saturday, sunday)

    Returns:
        List of all stops with coordinates
    """
    if calculator is None:
        raise HTTPException(status_code=503, detail="Calculator not initialized")

    try:
        stops = calculator.get_all_stops(day_type=day_type)
        return stops
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_PREFIX}/metadata", response_model=MetadataResponse)
async def get_metadata():
    """
    Get GTFS data metadata for attribution

    Returns:
        Metadata including source, download date, and feed version
    """
    try:
        downloader = GTFSDownloader(use_gcs=False)
        metadata = downloader.load_metadata()

        return MetadataResponse(
            source=settings.DATA_SOURCE,
            download_date=metadata.get('download_date'),
            feed_version=metadata.get('feed_version'),
            last_updated=metadata.get('last_updated')
        )
    except Exception as e:
        # Return basic info even if metadata file doesn't exist
        return MetadataResponse(
            source=settings.DATA_SOURCE,
            download_date=None,
            feed_version=None,
            last_updated=None
        )


@app.post(f"{settings.API_PREFIX}/reachability", response_model=ReachabilityResponse)
async def calculate_reachability(request: ReachabilityRequest):
    """
    Calculate reachable stops from an origin

    Args:
        request: Reachability calculation parameters

    Returns:
        List of reachable stops with travel times
    """
    if calculator is None:
        raise HTTPException(status_code=503, detail="Calculator not initialized")

    try:
        # Get origin stop info
        origin = calculator.get_stop_info(request.origin_stop_id, request.day_type)
        if origin is None:
            raise HTTPException(status_code=404, detail=f"Stop not found: {request.origin_stop_id}")

        # Calculate reachability
        reachable = calculator.calculate_reachability(
            origin_stop_id=request.origin_stop_id,
            departure_time=request.departure_time,
            max_time_minutes=request.max_time_minutes,
            day_type=request.day_type
        )

        return ReachabilityResponse(
            origin=origin,
            reachable_stops=reachable
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/reachability-timeline", response_model=ReachabilityTimelineResponse)
async def calculate_reachability_timeline(request: ReachabilityTimelineRequest):
    """
    Calculate reachability timeline for animation

    Args:
        request: Timeline calculation parameters

    Returns:
        Timeline with reachable stops at each time interval
    """
    if calculator is None:
        raise HTTPException(status_code=503, detail="Calculator not initialized")

    try:
        # Get origin stop info
        origin = calculator.get_stop_info(request.origin_stop_id, request.day_type)
        if origin is None:
            raise HTTPException(status_code=404, detail=f"Stop not found: {request.origin_stop_id}")

        # Calculate timeline
        timeline = calculator.calculate_reachability_timeline(
            origin_stop_id=request.origin_stop_id,
            departure_time=request.departure_time,
            max_time_minutes=request.max_time_minutes,
            time_step_minutes=request.time_step_minutes,
            day_type=request.day_type
        )

        return ReachabilityTimelineResponse(
            origin=origin,
            timeline=timeline
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/admin/update-gtfs", response_model=UpdateResponse)
async def update_gtfs(authorization: Optional[str] = Header(None)):
    """
    Check for GTFS updates and rebuild graphs if needed

    Requires admin token in Authorization header.

    Returns:
        Update status and new metadata
    """
    # Check authorization
    if settings.ADMIN_TOKEN and authorization != f"Bearer {settings.ADMIN_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Check and update GTFS data
        downloader = GTFSDownloader(use_gcs=False)
        updated = downloader.check_and_update()

        if updated:
            # Rebuild graphs
            print("Rebuilding graphs...")
            builder = TransitGraphBuilder()
            builder.build_all_graphs()
            builder.save_graphs()

            # Reload calculator
            load_calculator()

            # Get new metadata
            metadata = downloader.load_metadata()

            return UpdateResponse(
                updated=True,
                message="GTFS data updated and graphs rebuilt",
                metadata=MetadataResponse(
                    source=settings.DATA_SOURCE,
                    download_date=metadata.get('download_date'),
                    feed_version=metadata.get('feed_version'),
                    last_updated=metadata.get('last_updated')
                )
            )
        else:
            return UpdateResponse(
                updated=False,
                message="No update needed - data is current"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "calculator_loaded": calculator is not None
    }


# Mount static files (for frontend)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass  # Directory might not exist yet


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
