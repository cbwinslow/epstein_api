from datetime import date, datetime
from enum import Enum
from typing import NotRequired, TypedDict

from pydantic import BaseModel, Field


class EntitySource(str, Enum):
    PDF = "pdf"
    OCR = "ocr"
    AUDIO = "audio"
    VIDEO = "video"
    MANUAL = "manual"


class RelationshipType(str, Enum):
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


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Person(BaseModel):
    id: str | None = None
    full_name: str
    aliases: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    first_seen: date | None = None
    last_seen: date | None = None
    source_documents: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: str | None = None


class Organization(BaseModel):
    id: str | None = None
    name: str
    aliases: list[str] = Field(default_factory=list)
    organization_type: str | None = None
    founded_date: date | None = None
    dissolution_date: date | None = None
    jurisdiction: str | None = None
    source_documents: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: str | None = None


class Aircraft(BaseModel):
    id: str | None = None
    tail_number: str
    make: str | None = None
    model: str | None = None
    registration_country: str | None = None
    source_documents: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class Location(BaseModel):
    id: str | None = None
    name: str
    location_type: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_documents: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class EventType(str, Enum):
    FLIGHT = "flight"
    MEETING = "meeting"
    COURT_DEPOSITION = "court_deposition"
    FINANCIAL_TRANSFER = "financial_transfer"
    PHONE_CALL = "phone_call"
    EMAIL = "email"
    TRANSACTION = "transaction"


class Event(BaseModel):
    id: str | None = None
    event_type: EventType
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    inferred_date: str | None = None
    location: str | None = None
    participants: list[str] = Field(default_factory=list)
    aircraft: str | None = None
    source_documents: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: str | None = None


class ExtractedEntities(BaseModel):
    persons: list[Person] = Field(default_factory=list)
    organizations: list[Organization] = Field(default_factory=list)
    aircraft: list[Aircraft] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    source_file: str
    extraction_date: datetime = Field(default_factory=datetime.now)


class RelationshipScore(int, Enum):
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


class ExtractedRelationship(BaseModel):
    from_entity: str
    to_entity: str
    relationship_type: RelationshipType
    score: RelationshipScore
    evidence: list[str] = Field(default_factory=list)
    source_documents: list[str] = Field(default_factory=list)
    first_seen: date | None = None
    last_seen: date | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: str | None = None


class ExtractedRelationships(BaseModel):
    relationships: list[ExtractedRelationship] = Field(default_factory=list)
    source_file: str
    extraction_date: datetime = Field(default_factory=datetime.now)
