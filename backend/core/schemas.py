"""
Pydantic schemas for strict validation of AI agent outputs.

These schemas ensure AI agents return valid structured data before
reaching the Neo4j/ChromaDB databases. Used by MCP tools.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EntityType(str, Enum):
    """Types of entities that can be extracted."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    AIRCRAFT = "aircraft"
    EVENT = "event"


class ConfidenceLevel(str, Enum):
    """Confidence level for extracted entities."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RelationshipType(str, Enum):
    """Types of relationships between entities."""

    FLEW_WITH = "FLEW_WITH"
    MET_AT = "MET_AT"
    WORKED_FOR = "WORKED_FOR"
    BOARD_MEMBER = "BOARD_MEMBER"
    FINANCIAL_TIE = "FINANCIAL_TIE"
    LEGAL_REP = "LEGAL_REP"
    SHARED_OWNERSHIP = "SHARED_OWNERSHIP"
    CO_DEFENDANT = "CO_DEFENDANT"
    FACILITATOR = "FACILITATOR"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    EMAIL_EXCHANGE = "EMAIL_EXCHANGE"


class RelationshipScore(int, Enum):
    """Relationship strength score (1-10)."""

    INCIDENTAL_1 = 1
    INCIDENTAL_2 = 2
    PROXIMITY_3 = 3
    PROXIMITY_4 = 4
    DIRECT_CONTACT_5 = 5
    DIRECT_CONTACT_6 = 6
    PROFESSIONAL_7 = 7
    PROFESSIONAL_8 = 8
    CORE_NETWORK_9 = 9
    CORE_NETWORK_10 = 10


class EventType(str, Enum):
    """Types of events."""

    FLIGHT = "flight"
    MEETING = "meeting"
    COURT_DEPOSITION = "court_deposition"
    FINANCIAL_TRANSFER = "financial_transfer"
    PHONE_CALL = "phone_call"
    EMAIL = "email"
    TRANSACTION = "transaction"


class ExtractedPerson(BaseModel):
    """Validated person entity extracted by AI.

    This schema is used by the Extractor Agent to ensure
    valid data before reaching the database.
    """

    model_config = {"extra": "forbid"}

    full_name: str = Field(..., min_length=1, max_length=200)
    aliases: list[str] = Field(default_factory=list, max_length=50)
    titles: list[str] = Field(default_factory=list, max_length=20)
    first_seen: date | None = None
    last_seen: date | None = None
    source_documents: list[str] = Field(..., min_length=1)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: str | None = None

    @field_validator("aliases", "titles", mode="before")
    @classmethod
    def validate_lists(cls, v: Any) -> list:
        """Ensure lists are actually lists."""
        if v is None:
            return []
        return list(v) if isinstance(v, (list, tuple)) else [v]


class ExtractedOrganization(BaseModel):
    """Validated organization entity extracted by AI."""

    model_config = {"extra": "forbid"}

    name: str = Field(..., min_length=1, max_length=300)
    aliases: list[str] = Field(default_factory=list, max_length=50)
    organization_type: str | None = None
    founded_date: date | None = None
    dissolution_date: date | None = None
    jurisdiction: str | None = None
    source_documents: list[str] = Field(..., min_length=1)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: str | None = None


class ExtractedAircraft(BaseModel):
    """Validated aircraft entity extracted by AI."""

    model_config = {"extra": "forbid"}

    tail_number: str = Field(..., pattern=r"^[A-Z0-9]{2,6}$")
    make: str | None = None
    model: str | None = None
    registration_country: str | None = None
    source_documents: list[str] = Field(..., min_length=1)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class ExtractedLocation(BaseModel):
    """Validated location entity extracted by AI."""

    model_config = {"extra": "forbid"}

    name: str = Field(..., min_length=1, max_length=300)
    location_type: str = Field(..., min_length=1)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    source_documents: list[str] = Field(..., min_length=1)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class ExtractedEvent(BaseModel):
    """Validated event entity extracted by AI."""

    model_config = {"extra": "forbid"}

    event_type: EventType
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    inferred_date: str | None = None
    location: str | None = None
    participants: list[str] = Field(default_factory=list)
    aircraft: str | None = None
    source_documents: list[str] = Field(..., min_length=1)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: str | None = None


class ExtractedEntitiesInput(BaseModel):
    """Input schema for entity extraction.

    This is what the AI agent receives as input.
    """

    model_config = {"extra": "forbid"}

    raw_text: str = Field(..., min_length=1)
    source_file: str = Field(..., min_length=1)
    source_type: str = Field(..., pattern="^(pdf|ocr|audio|video|manual)$")
    document_date: date | None = None


class ExtractedEntitiesOutput(BaseModel):
    """Validated output from the Extractor Agent.

    This schema ensures AI returns valid data before database insertion.
    """

    model_config = {"extra": "forbid"}

    persons: list[ExtractedPerson] = Field(default_factory=list)
    organizations: list[ExtractedOrganization] = Field(default_factory=list)
    aircraft: list[ExtractedAircraft] = Field(default_factory=list)
    locations: list[ExtractedLocation] = Field(default_factory=list)
    events: list[ExtractedEvent] = Field(default_factory=list)
    source_file: str
    extraction_date: datetime = Field(default_factory=datetime.now)

    @field_validator("source_file", mode="before")
    @classmethod
    def validate_source_file(cls, v: Any) -> str:
        """Ensure source file is not empty."""
        if not v or not isinstance(v, str):
            raise ValueError("source_file must be a non-empty string")
        return v

    def is_empty(self) -> bool:
        """Check if no entities were extracted."""
        return (
            not self.persons
            and not self.organizations
            and not self.aircraft
            and not self.locations
            and not self.events
        )


class ExtractedRelationship(BaseModel):
    """Validated relationship between entities."""

    model_config = {"extra": "forbid"}

    from_entity: str = Field(..., min_length=1)
    to_entity: str = Field(..., min_length=1)
    relationship_type: RelationshipType
    score: RelationshipScore
    evidence: list[str] = Field(default_factory=list, min_length=1)
    source_documents: list[str] = Field(..., min_length=1)
    first_seen: date | None = None
    last_seen: date | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: str | None = None

    @field_validator("from_entity", "to_entity", mode="before")
    @classmethod
    def validate_entity_names(cls, v: Any) -> str:
        """Ensure entity names are not empty."""
        if not v or not isinstance(v, str):
            raise ValueError("Entity names must be non-empty strings")
        return v.strip()


class ExtractedRelationshipsOutput(BaseModel):
    """Validated output from the Relationship Analyst Agent."""

    model_config = {"extra": "forbid"}

    relationships: list[ExtractedRelationship] = Field(default_factory=list)
    source_file: str
    extraction_date: datetime = Field(default_factory=datetime.now)


class QueryRequest(BaseModel):
    """User query request to the Query Agent."""

    model_config = {"extra": "forbid"}

    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(10, ge=1, le=100)
    include_graph: bool = True
    include_vectors: bool = True


class QueryResult(BaseModel):
    """Result from the Query Agent."""

    model_config = {"extra": "forbid"}

    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    graph_paths: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)


class DownloadTaskCreate(BaseModel):
    """Request to create a download task."""

    model_config = {"extra": "forbid"}

    url: str = Field(..., min_length=1)
    dest_path: str = Field(..., min_length=1)
    expected_hash: str | None = None

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: Any) -> str:
        """Validate URL format."""
        if not v or not isinstance(v, str):
            raise ValueError("URL must be a non-empty string")
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class DownloadTaskResponse(BaseModel):
    """Response for a download task."""

    model_config = {"extra": "forbid"}

    url: str
    dest_path: str
    status: str
    retries: int = 0
    error_message: str | None = None
    sha256_hash: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProcessingTaskCreate(BaseModel):
    """Request to create a processing task."""

    model_config = {"extra": "forbid"}

    file_path: str = Field(..., min_length=1)
    file_type: str = Field(..., pattern="^(pdf|image|audio|video)$")
    priority: int = Field(0, ge=0, le=10)

    @field_validator("file_path", mode="before")
    @classmethod
    def validate_file_path(cls, v: Any) -> str:
        """Validate file path."""
        if not v or not isinstance(v, str):
            raise ValueError("file_path must be a non-empty string")
        return v.strip()


class ProcessingTaskResponse(BaseModel):
    """Response for a processing task."""

    model_config = {"extra": "forbid"}

    task_id: str
    file_path: str
    status: str
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
