import os
from pathlib import Path

import pytest

from description_harvester.inputs.ead import EAD
from description_harvester.models.description import Component, Date, Extent

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "ead"


def test_items_with_file():
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    items = list(e.items())
    assert len(items) == 1
    assert Path(items[0]).resolve() == sample.resolve()


def test_items_with_dir():
    e = EAD(str(FIXTURES_DIR))
    items = sorted([p.name for p in e.items()])
    expected = sorted(["apap185.xml", "ger069.xml", "ua600.007.xml"])
    assert items == expected


def test_fetch_reads_raw_xml():
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    # Ensure fetch returns a Component and that the raw XML is available
    assert hasattr(comp, "raw_xml")
    expected_text = Path(sample).read_text(encoding="utf-8")
    assert comp.raw_xml == expected_text


def test_fetch_maps_to_component_model():
    """TDD: expect `fetch()` to return a `Component` model for the top-level description.

    This test will fail until `EAD.fetch()` is implemented to parse XML and return
    a `Component` instance mapped from the collection-level archdesc/did.
    """
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)

    # Expect a Component instance (TDD)
    assert isinstance(comp, Component)

    # Basic required fields from the EAD
    assert getattr(comp, "id", None) == "ger069"
    # collection_id should at least match the unitid
    assert getattr(comp, "collection_id", None) == "ger069"
    # repository should contain the repository name from the EAD
    assert isinstance(getattr(comp, "repository", None), str)
    assert "Grenander" in comp.repository

    # Dates and extents should be parsed into model classes
    assert isinstance(comp.dates, list)
    assert any(isinstance(d, Date) for d in comp.dates)

    assert isinstance(comp.extents, list)
    assert any(isinstance(x, Extent) for x in comp.extents)

    # Top-level components (dsc/c elements) should be parsed into children
    assert isinstance(comp.components, list)
    assert len(comp.components) > 0


def test_path_not_found_raises_error():
    """Test that EAD raises FileNotFoundError for non-existent paths."""
    with pytest.raises(FileNotFoundError):
        EAD("/nonexistent/path/to/file.xml")


def test_component_hierarchy():
    """Test that child components are properly parsed from the dsc tree."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # Top-level should have child components
    assert len(comp.components) > 0
    
    # Each child should be a Component instance
    for child in comp.components:
        assert isinstance(child, Component)
        # Children should have their own id, title, and other required fields
        assert child.id is not None
        assert child.collection_id == comp.collection_id
        assert child.repository == comp.repository


def test_component_metadata_extraction():
    """Test that component metadata is correctly extracted from EAD elements."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # Check that top-level metadata was extracted
    assert comp.title is not None
    assert len(comp.title) > 0
    assert comp.level is not None
    assert comp.repository is not None
    
    # Check that dates were parsed
    if comp.dates:
        for date in comp.dates:
            assert isinstance(date, Date)
            assert date.expression is not None
    
    # Check that extents were parsed
    if comp.extents:
        for extent in comp.extents:
            assert isinstance(extent, Extent)
            assert extent.number is not None
            assert extent.unit is not None


