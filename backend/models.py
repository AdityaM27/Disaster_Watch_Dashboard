"""
Data models and schemas for DisasterWatch India.
Includes Pydantic models for request validation, data serialization, and response types.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DisasterType(str, Enum):
    EARTHQUAKE = "Earthquake"
    FLOOD_RISK = "Flood Risk"
    FIRE = "Fire"
    CYCLONE = "Cyclone/Storm"
    HEATWAVE = "Heatwave"


class SeverityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class AlertStatus(str, Enum):
    CONFIRMED_EVENT = "Confirmed Event"
    OFFICIAL_ALERT = "Official Alert"
    ESTIMATED_RISK = "Estimated Risk"


class AlertItem(BaseModel):
    """
    Standardized disaster alert or monitoring event representation.
    Every event carries its real source, verified timestamp, and calculation basis.
    """
    id: str = Field(..., description="Unique event identifier (e.g. usgs-us6000m92z)")
    title: str = Field(..., description="Human-readable summary title")
    disaster_type: DisasterType = Field(..., description="Classification category")
    severity: SeverityLevel = Field(..., description="Severity level determined by risk engine")
    status: AlertStatus = Field(..., description="Confirmed Event, Official Alert, or Estimated Risk")
    location_name: str = Field(..., description="Descriptive geographic location")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    
    # Event-specific physical metrics
    magnitude: Optional[float] = Field(None, description="Earthquake Richter magnitude")
    depth_km: Optional[float] = Field(None, description="Focal depth in kilometers")
    rainfall_mm: Optional[float] = Field(None, description="Precipitation in mm")
    wind_speed_kmh: Optional[float] = Field(None, description="Wind speed in km/h")
    temperature_c: Optional[float] = Field(None, description="Ambient temperature in Celsius")
    
    # Risk and safety audit trail
    risk_score: Optional[float] = Field(None, description="Numeric risk index (0.0 to 10.0)")
    risk_rule_triggered: str = Field(..., description="Exact risk engine rule applied")
    risk_calculation_details: Dict[str, Any] = Field(default_factory=dict, description="Values and thresholds compared")
    safety_guidance: str = Field(..., description="Standard safety advice for this event type")
    
    # Data lineage & provenance
    source_name: str = Field(..., description="Official provider name (e.g., USGS, Open-Meteo)")
    source_url: Optional[str] = Field(None, description="Direct URL to original data point or portal")
    event_time: str = Field(..., description="ISO 8601 timestamp when event occurred")
    updated_time: str = Field(..., description="ISO 8601 timestamp when data was fetched/processed")
    
    # Map visualization flags
    is_estimated_zone: bool = Field(False, description="Whether this represents a calculated risk perimeter")
    is_official_alert: bool = Field(False, description="Whether this stems from an authorized agency CAP alert")
    zone_radius_km: Optional[float] = Field(None, description="Visual zone radius in km on Leaflet map")


class SourceStatus(BaseModel):
    """
    Operational status of an integrated or designated disaster feed.
    """
    id: str
    name: str
    disaster_type: str
    connection_status: str  # "Connected", "Not connected yet", "Configuration required", "Error"
    last_successful_update: Optional[str] = None
    update_frequency: str
    description: str
    website_url: str
    is_live: bool = False
    details: Optional[str] = None


class RefreshLog(BaseModel):
    """
    Audit log entry for a background or manual feed refresh.
    """
    id: Optional[int] = None
    timestamp: str
    source: str
    status: str  # "SUCCESS", "PARTIAL", "FAILED"
    events_count: int = 0
    message: str
    duration_ms: float = 0.0


class RiskExplanation(BaseModel):
    """
    Transparent breakdown of how an alert's risk/severity was computed.
    """
    alert_id: str
    disaster_type: str
    severity: str
    status: str
    triggered_rule: str
    measured_values: Dict[str, Any]
    threshold_benchmarks: Dict[str, Any]
    safety_guidance: str
    calculation_timestamp: str
    disclaimer: str


class MonitoredLocation(BaseModel):
    """
    Predefined or user-tracked observation station in India.
    """
    id: str
    name: str
    state: str
    latitude: float
    longitude: float
    description: str
    is_coastal: bool = False
    is_seismic_zone: bool = False


class DashboardSummary(BaseModel):
    """
    Live aggregated statistics for the dashboard counter widgets.
    """
    active_events: int = 0
    high_critical_events: int = 0
    recent_earthquakes: int = 0
    sources_online: int = 0
    total_sources: int = 0
    last_refreshed: Optional[str] = None
