"""
Unit tests for Pydantic schemas in core/schemas.py.

These tests verify that validation triggers correctly on bad data.
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from backend.core.schemas import (
    ExtractedPerson,
    ExtractedOrganization,
    ExtractedAircraft,
    ExtractedLocation,
    ExtractedEvent,
    ExtractedEntitiesOutput,
    ExtractedRelationship,
    ExtractedEntitiesInput,
    DownloadTaskCreate,
    QueryRequest,
    ConfidenceLevel,
    EventType,
    RelationshipType,
    RelationshipScore,
)


class TestExtractedPerson:
    """Tests for ExtractedPerson schema."""

    def test_valid_person(self) -> None:
        """Test creating a valid person."""
        person = ExtractedPerson(
            full_name="Jeffrey Epstein",
            aliases=["Jeff", "Eppy"],
            source_documents=["doc1.pdf"],
            confidence="high",
        )
        assert person.full_name == "Jeffrey Epstein"
        assert person.aliases == ["Jeff", "Eppy"]
        assert person.confidence == ConfidenceLevel.HIGH

    def test_empty_name_fails(self) -> None:
        """Test that empty name fails validation."""
        with pytest.raises(ValidationError):
            ExtractedPerson(full_name="", source_documents=["doc1.pdf"])

    def test_missing_source_documents_fails(self) -> None:
        """Test that missing source documents fails."""
        with pytest.raises(ValidationError):
            ExtractedPerson(full_name="Test Person", source_documents=[])

    def test_invalid_confidence_fails(self) -> None:
        """Test that invalid confidence level fails."""
        with pytest.raises(ValidationError):
            ExtractedPerson(
                full_name="Test Person",
                source_documents=["doc1.pdf"],
                confidence="invalid",
            )

    def test_aliases_normalized_to_list(self) -> None:
        """Test that aliases are normalized to list."""
        person = ExtractedPerson(
            full_name="Test Person",
            aliases="single_alias",
            source_documents=["doc1.pdf"],
        )
        assert person.aliases == ["single_alias"]


class TestExtractedAircraft:
    """Tests for ExtractedAircraft schema."""

    def test_valid_aircraft(self) -> None:
        """Test creating a valid aircraft."""
        aircraft = ExtractedAircraft(
            tail_number="N228AW",
            make="Boeing",
            model="737-7BC",
            source_documents=["flight_log.pdf"],
        )
        assert aircraft.tail_number == "N228AW"
        assert aircraft.make == "Boeing"

    def test_invalid_tail_number_format(self) -> None:
        """Test that invalid tail number fails."""
        with pytest.raises(ValidationError):
            ExtractedAircraft(
                tail_number="invalid",
                source_documents=["doc1.pdf"],
            )

    def test_valid_tail_numbers(self) -> None:
        """Test various valid tail number formats."""
        valid_numbers = ["N228AW", "N120JE", "N977AJ", "N12345"]
        for num in valid_numbers:
            aircraft = ExtractedAircraft(
                tail_number=num,
                source_documents=["doc1.pdf"],
            )
            assert aircraft.tail_number == num


class TestExtractedLocation:
    """Tests for ExtractedLocation schema."""

    def test_valid_location(self) -> None:
        """Test creating a valid location."""
        location = ExtractedLocation(
            name="9 East 71st Street",
            location_type="residence",
            city="New York",
            state="NY",
            country="United States",
            source_documents=["doc1.pdf"],
        )
        assert location.name == "9 East 71st Street"
        assert location.location_type == "residence"

    def test_invalid_latitude(self) -> None:
        """Test that invalid latitude fails."""
        with pytest.raises(ValidationError):
            ExtractedLocation(
                name="Test",
                location_type="test",
                latitude=100,  # Invalid: > 90
                source_documents=["doc1.pdf"],
            )

    def test_invalid_longitude(self) -> None:
        """Test that invalid longitude fails."""
        with pytest.raises(ValidationError):
            ExtractedLocation(
                name="Test",
                location_type="test",
                longitude=200,  # Invalid: > 180
                source_documents=["doc1.pdf"],
            )


class TestExtractedEntitiesInput:
    """Tests for ExtractedEntitiesInput schema."""

    def test_valid_input(self) -> None:
        """Test creating valid input."""
        input_data = ExtractedEntitiesInput(
            raw_text="Sample text",
            source_file="document.pdf",
            source_type="pdf",
        )
        assert input_data.raw_text == "Sample text"
        assert input_data.source_type == "pdf"

    def test_invalid_source_type(self) -> None:
        """Test that invalid source type fails."""
        with pytest.raises(ValidationError):
            ExtractedEntitiesInput(
                raw_text="Sample text",
                source_file="document.pdf",
                source_type="invalid",
            )

    def test_empty_raw_text_fails(self) -> None:
        """Test that empty raw text fails."""
        with pytest.raises(ValidationError):
            ExtractedEntitiesInput(
                raw_text="",
                source_file="document.pdf",
                source_type="pdf",
            )


class TestDownloadTaskCreate:
    """Tests for DownloadTaskCreate schema."""

    def test_valid_url(self) -> None:
        """Test creating valid download task."""
        task = DownloadTaskCreate(
            url="https://example.com/file.pdf",
            dest_path="/downloads/file.pdf",
        )
        assert task.url == "https://example.com/file.pdf"

    def test_invalid_url_no_protocol(self) -> None:
        """Test that URL without protocol fails."""
        with pytest.raises(ValidationError):
            DownloadTaskCreate(
                url="example.com/file.pdf",
                dest_path="/downloads/file.pdf",
            )

    def test_http_url_valid(self) -> None:
        """Test that http URL is valid."""
        task = DownloadTaskCreate(
            url="http://example.com/file.pdf",
            dest_path="/downloads/file.pdf",
        )
        assert task.url == "http://example.com/file.pdf"


class TestQueryRequest:
    """Tests for QueryRequest schema."""

    def test_valid_query(self) -> None:
        """Test creating valid query request."""
        query = QueryRequest(query="Who flew with Epstein?")
        assert query.query == "Who flew with Epstein?"
        assert query.top_k == 10
        assert query.include_graph is True

    def test_top_k_bounds(self) -> None:
        """Test top_k validation bounds."""
        with pytest.raises(ValidationError):
            QueryRequest(query="Test", top_k=0)

        with pytest.raises(ValidationError):
            QueryRequest(query="Test", top_k=101)


class TestExtractedRelationship:
    """Tests for ExtractedRelationship schema."""

    def test_valid_relationship(self) -> None:
        """Test creating valid relationship."""
        rel = ExtractedRelationship(
            from_entity="Jeffrey Epstein",
            to_entity="Prince Andrew",
            relationship_type=RelationshipType.FLEW_WITH,
            score=RelationshipScore.DIRECT_CONTACT_6,
            evidence=["Flight log shows both on N228AW"],
            source_documents=["flight_log.pdf"],
        )
        assert rel.from_entity == "Jeffrey Epstein"
        assert rel.score == RelationshipScore.DIRECT_CONTACT_6

    def test_empty_entity_names_fail(self) -> None:
        """Test that empty entity names fail."""
        with pytest.raises(ValidationError):
            ExtractedRelationship(
                from_entity="",
                to_entity="Person B",
                relationship_type=RelationshipType.FLEW_WITH,
                score=5,
                evidence=["evidence"],
                source_documents=["doc.pdf"],
            )

    def test_evidence_min_length(self) -> None:
        """Test that evidence requires at least one item."""
        with pytest.raises(ValidationError):
            ExtractedRelationship(
                from_entity="Person A",
                to_entity="Person B",
                relationship_type=RelationshipType.FLEW_WITH,
                score=5,
                evidence=[],
                source_documents=["doc.pdf"],
            )


class TestExtractedEntitiesOutput:
    """Tests for ExtractedEntitiesOutput schema."""

    def test_valid_output(self) -> None:
        """Test creating valid entities output."""
        person = ExtractedPerson(
            full_name="Test Person",
            source_documents=["doc.pdf"],
        )
        output = ExtractedEntitiesOutput(
            persons=[person],
            source_file="doc.pdf",
        )
        assert len(output.persons) == 1
        assert not output.is_empty()

    def test_empty_output_detection(self) -> None:
        """Test is_empty method."""
        output = ExtractedEntitiesOutput(source_file="doc.pdf")
        assert output.is_empty() is True

    def test_extraction_date_auto_set(self) -> None:
        """Test that extraction date is auto-set."""
        output = ExtractedEntitiesOutput(source_file="doc.pdf")
        assert output.extraction_date is not None
        assert isinstance(output.extraction_date, datetime)
