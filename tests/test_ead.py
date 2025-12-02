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

    # Check that languages were parsed
    assert isinstance(comp.languages, list)
    # The ger069 fixture contains English (and German) languages
    assert any("English" in l for l in comp.languages)


def test_note_fields_basic_extraction():
    """Test that all note fields are extracted from the EAD."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # apap185 should have bioghist and scopecontent
    assert hasattr(comp, 'bioghist')
    assert hasattr(comp, 'scopecontent')
    
    # Both should be non-empty lists
    assert isinstance(comp.bioghist, list)
    assert len(comp.bioghist) > 0
    assert isinstance(comp.scopecontent, list)
    assert len(comp.scopecontent) > 0
    
    # Content should be strings
    for item in comp.bioghist:
        assert isinstance(item, str)
        assert len(item) > 0
    for item in comp.scopecontent:
        assert isinstance(item, str)
        assert len(item) > 0


def test_note_field_headings():
    """Test that note field headings are extracted separately."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # Check that heading fields exist
    assert hasattr(comp, 'bioghist_heading')
    assert hasattr(comp, 'scopecontent_heading')
    
    # The apap185 fixture has explicit <head> elements
    # bioghist_heading should be None (no explicit head in bioghist)
    # scopecontent_heading should be None (no explicit head in scopecontent)
    # (These are set by explicit <head> tags in the XML)


def test_note_field_tag_normalization_emph_italic():
    """Test that <emph render="italic"> tags are converted to <i> tags."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # The apap185 bioghist has <emph render="italic">Trannies in Love</emph>
    bioghist_text = " ".join(comp.bioghist)
    assert "<i>Trannies in Love</i>" in bioghist_text
    
    # Should NOT contain the original emph tag
    assert "<emph" not in bioghist_text
    
    # The scopecontent has multiple <emph render="italic"> tags
    scopecontent_text = " ".join(comp.scopecontent)
    assert "<i>TV-TS Tapestry</i>" in scopecontent_text
    assert "<i>Transgender Tapestry</i>" in scopecontent_text
    assert "<i>Femme Mirror</i>" in scopecontent_text


def test_note_field_tag_normalization_title():
    """Test that <title> tags are converted to <i> tags."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # The apap185 separatedmaterial has <title><emph>...</emph></title> tags
    # After normalization, both should become <i>
    all_notes = []
    for attr in ['bioghist', 'scopecontent', 'separatedmaterial', 'abstract',
                 'arrangement', 'accessrestrict', 'bibliography', 'note',
                 'physloc', 'materialspec']:
        if hasattr(comp, attr):
            notes = getattr(comp, attr)
            if notes:
                all_notes.extend(notes if isinstance(notes, list) else [notes])
    
    combined = " ".join(all_notes)
    
    # Check for book titles converted from <title> to <i>
    # (The fixture has <title><emph render="italic">A Quiet Song, A Little Storm</emph></title>)
    # After normalization, this should be <i>A Quiet Song, A Little Storm</i>
    if "A Quiet Song, A Little Storm" in combined:
        # Should have <i> tags around it, not <title> tags
        assert "<title>" not in combined or "<i>" in combined


def test_note_field_multiple_paragraphs():
    """Test that multiple paragraphs in a note field are properly separated."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # bioghist should have multiple paragraphs
    assert len(comp.bioghist) >= 1
    
    # scopecontent should have multiple paragraphs
    assert len(comp.scopecontent) >= 1
    
    # Each paragraph should be a separate list item
    for para in comp.bioghist:
        assert len(para) > 50  # Each paragraph should have meaningful content


def test_note_fields_whitespace_handling():
    """Test that whitespace is properly handled in note extraction."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # No note content should have leading/trailing whitespace
    for para in comp.bioghist:
        assert para == para.strip()
    
    for para in comp.scopecontent:
        assert para == para.strip()
    
    # No note content should have excessive internal whitespace
    for para in comp.bioghist:
        assert "  " not in para  # No double spaces
    
    for para in comp.scopecontent:
        assert "  " not in para  # No double spaces


def test_note_field_ger069_fixture():
    """Test note extraction with ger069 fixture (different EAD structure)."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # ger069 has bioghist with <emph> tags
    assert hasattr(comp, 'bioghist')
    if comp.bioghist:
        bioghist_text = " ".join(comp.bioghist)
        
        # Check for expected titles (ger069 has book titles with emph)
        # "<emph render="italic">Der Tauschwert des Geldes</emph>" should become "<i>Der Tauschwert des Geldes</i>"
        if "Der Tauschwert des Geldes" in bioghist_text:
            assert "<i>Der Tauschwert des Geldes</i>" in bioghist_text
            assert "<emph" not in bioghist_text or "<i>" in bioghist_text
        
        # Should have content about Hans Neisser
        assert "Hans Neisser" in bioghist_text or "Neisser" in bioghist_text


def test_note_field_mixed_content_with_tags():
    """Test note extraction with mixed text and tag content."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # scopecontent has plain text mixed with <emph> tags
    scopecontent_text = " ".join(comp.scopecontent)
    
    # Should have both plain text and tagged content
    assert len(scopecontent_text) > 500  # Substantial content
    assert "<i>" in scopecontent_text  # Has formatted content
    
    # Check for expected structure: text containing "includes" followed by tagged titles
    if "includes" in scopecontent_text:
        # The sentence should have titles properly formatted
        assert "<i>" in scopecontent_text


def test_all_note_field_attributes_exist():
    """Test that all note field attributes are defined on Component."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # All note fields should exist as attributes
    note_fields = [
        'abstract', 'bioghist', 'scopecontent', 'arrangement',
        'accessrestrict', 'userestrict', 'accruals', 'bibliography',
        'note', 'physloc', 'materialspec', 'separatedmaterial'
    ]
    
    for field in note_fields:
        assert hasattr(comp, field), f"Component should have {field} attribute"
    
    # All heading fields should exist
    for field in note_fields:
        heading_field = f"{field}_heading"
        assert hasattr(comp, heading_field), f"Component should have {heading_field} attribute"


def test_note_field_normalization_preserves_content():
    """Test that tag normalization doesn't lose or corrupt content."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    scopecontent_text = " ".join(comp.scopecontent)
    
    # Should contain key terms and concepts
    assert "Capital Region" in scopecontent_text or "Transgender" in scopecontent_text
    
    # Should not have incomplete or mangled tags
    assert "<emph" not in scopecontent_text  # Old tags should be gone
    assert "</i>" in scopecontent_text or "<i>" not in scopecontent_text  # Proper closing tags


def test_note_field_empty_handling():
    """Test that empty or missing note fields are handled gracefully."""
    sample = FIXTURES_DIR / "ua600.007.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # ua600.007 may not have all note fields
    # All fields should exist but may be empty lists
    note_fields = [
        'abstract', 'bioghist', 'scopecontent', 'arrangement',
        'accessrestrict', 'userestrict', 'accruals', 'bibliography',
        'note', 'physloc', 'materialspec', 'separatedmaterial'
    ]
    
    for field in note_fields:
        attr = getattr(comp, field, None)
        # Should be None or empty list, not raise an error
        assert attr is None or isinstance(attr, list)


def test_recursive_component_hierarchy_multilevel():
    """Test that multi-level component hierarchies are properly parsed."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # ger069 has 3+ levels of components
    # Top level: collection
    assert comp.level == "collection"
    assert len(comp.components) > 0
    
    # Second level: series
    series = [c for c in comp.components if c.level == "series"]
    assert len(series) >= 2  # Should have at least 2 series
    
    # Third level: files/others nested under series
    has_third_level = False
    for series_comp in series:
        if len(series_comp.components) > 0:
            has_third_level = True
            # Check that components have correct level and IDs
            for child in series_comp.components:
                assert child.level is not None
                assert child.id is not None
                assert child.collection_id == comp.collection_id
                # All descendants should inherit collection_id
                for grandchild in child.components:
                    assert grandchild.collection_id == comp.collection_id
    
    assert has_third_level, "Should have 3+ levels of components"


def test_recursive_component_count():
    """Test that all components are counted correctly across levels."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    def count_all_components(component):
        """Recursively count all components including the root."""
        count = 1
        for child in component.components:
            count += count_all_components(child)
        return count
    
    total = count_all_components(comp)
    
    # ger069 has many components across multiple levels
    # Should have more than just the top-level series
    assert total > 10, f"Expected many components, got {total}"
    
    # The fixture has ~150 components total (series + subseries + files)
    # Be conservative with the lower bound
    assert total >= 100, f"Expected at least 100 components, got {total}"


def test_deeply_nested_components():
    """Test that deeply nested component relationships are preserved."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # Find a series with subseries
    series_with_subseries = None
    for series in comp.components:
        if any(c.level == "otherlevel" for c in series.components):
            series_with_subseries = series
            break
    
    assert series_with_subseries is not None, "Should have series with subseries"
    
    # Get the subseries (otherlevel)
    subseries = [c for c in series_with_subseries.components if c.level == "otherlevel"]
    assert len(subseries) > 0
    
    # Each subseries should have file components
    for ss in subseries:
        assert len(ss.components) > 0
        files = [c for c in ss.components if c.level == "file"]
        assert len(files) > 0




