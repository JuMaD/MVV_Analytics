"""
Pydantic models for API requests and responses
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class StopInfo(BaseModel):
    """Information about a transit stop"""
    stop_id: str
    stop_name: str
    lat: float
    lon: float


class ReachableStop(StopInfo):
    """A reachable stop with travel time information"""
    travel_time_minutes: float
    num_transfers: int


class MetadataResponse(BaseModel):
    """GTFS data metadata for attribution"""
    source: str
    download_date: Optional[str] = None
    feed_version: Optional[str] = None
    last_updated: Optional[str] = None


class ReachabilityRequest(BaseModel):
    """Request for reachability calculation"""
    origin_stop_id: str
    max_time_minutes: int = Field(default=30, ge=5, le=120)
    departure_time: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    day_type: str = Field(default="weekday", pattern="^(weekday|saturday|sunday)$")


class ReachabilityResponse(BaseModel):
    """Response for reachability calculation"""
    origin: StopInfo
    reachable_stops: List[ReachableStop]


class TimelineFrame(BaseModel):
    """Single frame in reachability timeline"""
    elapsed_minutes: int
    reachable_stops: List[ReachableStop]


class ReachabilityTimelineRequest(BaseModel):
    """Request for reachability timeline calculation"""
    origin_stop_id: str
    max_time_minutes: int = Field(default=30, ge=5, le=120)
    time_step_minutes: int = Field(default=5, ge=1, le=30)
    departure_time: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    day_type: str = Field(default="weekday", pattern="^(weekday|saturday|sunday)$")


class ReachabilityTimelineResponse(BaseModel):
    """Response for reachability timeline calculation"""
    origin: StopInfo
    timeline: List[TimelineFrame]


class UpdateResponse(BaseModel):
    """Response for update check"""
    updated: bool
    message: str
    metadata: Optional[MetadataResponse] = None
