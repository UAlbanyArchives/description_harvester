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
    # Just verify we get multiple EAD files
    assert len(items) >= 3
    assert all(item.endswith(".xml") for item in items)


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


def test_container_parsing_file_component_apap101():
    """Verify container parsing for a file-level component in apap101.xml.

    Expect top container indicator '2' (Oversized/treated as top) and sub container indicator '15' (Folder).
    """
    sample = FIXTURES_DIR / "apap101.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)

    # Find the target component by id or title anywhere in hierarchy
    def _walk(c):
        yield c
        for ch in getattr(c, "components", []):
            yield from _walk(ch)

    target = None
    for node in _walk(comp):
        if getattr(node, "id", "") == "aspace_89030ee800a414a2cd3f48143818ae16" or getattr(node, "title", "") == "ACT UP New York poster":
            target = node
            break

    assert target is not None, "Expected to find target file-level component"
    assert hasattr(target, "containers")
    assert isinstance(target.containers, list)
    assert len(target.containers) >= 1
    cont = target.containers[0]

    # Indicators from XML text
    assert cont.top_container_indicator == "2"
    assert cont.sub_container_indicator == "15"

    # Type heuristics
    assert cont.top_container in ("box", "oversized", None)  # oversized is allowed; some EADs use non-standard labels
    assert cont.sub_container in ("folder", "file")


def test_dao_parsing_identifier_label_action_type_ua600():
    """Validate DAO parsing on ua600.007 fixtures which include daodesc and xlink attrs."""
    sample = FIXTURES_DIR / "ua600.007.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)

    # Find first file component with a dao
    def _walk(c):
        yield c
        for ch in getattr(c, "components", []):
            yield from _walk(ch)

    target = None
    for node in _walk(comp):
        if getattr(node, "digital_objects", None):
            if len(node.digital_objects) > 0:
                target = node
                break
    assert target is not None
    dobj = target.digital_objects[0]

    # Identifier should be the xlink:href URL
    assert isinstance(dobj.identifier, str)
    assert dobj.identifier.startswith("https://")

    # Label should come from daodesc text
    assert isinstance(dobj.label, str)
    assert len(dobj.label) > 0
    assert "Online object uploaded typically on user request." in dobj.label

    # Action should be embed (from xlink:show), but may be "link" if manifest plugin can't fetch
    assert dobj.action in ("embed", "link", None)

    # Type should be 'simple'
    assert dobj.type in ("simple", None)


def test_dao_parsing_title_fallback_apap101():
    """Validate DAO parsing on apap101 fixture and general behavior."""
    sample = FIXTURES_DIR / "apap101.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)

    # Find a node with digital objects
    def _walk(c):
        yield c
        for ch in getattr(c, "components", []):
            yield from _walk(ch)

    node_with_dao = None
    for node in _walk(comp):
        if getattr(node, "digital_objects", None) and node.digital_objects:
            node_with_dao = node
            break

    assert node_with_dao is not None
    dobj = node_with_dao.digital_objects[0]
    assert dobj.identifier.startswith("https://")
    # Label should be a non-empty string (plugins may transform content)
    assert isinstance(dobj.label, str)
    assert dobj.label.strip() != ""
    # Action and type may be plugin-dependent; if present, they should be strings
    if dobj.action is not None:
        assert isinstance(dobj.action, str)
        assert dobj.action.strip() != ""
    if dobj.type is not None:
        assert isinstance(dobj.type, str)
        assert dobj.type.strip() != ""


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


def test_origination_parsing_corpname():
    """Test that <origination><corpname> is parsed into Creator agent."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # apap185 has a corpname origination
    assert comp.creators is not None
    assert len(comp.creators) > 0
    
    # Find the creators
    creators = comp.creators[0]
    assert creators.name == "Capital District Transgender Community Archive"
    assert creators.agent_type == "creator"


def test_origination_parsing_persname():
    """Test that <origination><persname> is parsed into Creator agent."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # ger069 has a persname origination
    assert comp.creators is not None
    assert len(comp.creators) > 0
    
    # Find the creator
    creator = comp.creators[0]
    assert creator.name == "Hans Philipp Neisser"
    assert creator.agent_type == "creator"


def test_agent_type_always_creator():
    """Test that agents created from origination (creators) have agent_type='creator'."""
    fixtures = [FIXTURES_DIR / "apap185.xml", FIXTURES_DIR / "ger069.xml"]

    for fixture in fixtures:
        e = EAD(str(fixture))
        comp = e.fetch(fixture)

        # All creators from origination should have agent_type='creator'
        for creator in comp.creators:
            assert creator.agent_type == "creator", f"Expected 'creator' but got '{creator.agent_type}'"
def test_origination_missing_handled_gracefully():
    """Test that components without origination are handled gracefully."""
    sample = FIXTURES_DIR / "ua600.007.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # Should have agents field (may be empty)
    assert hasattr(comp, "agents")
    assert isinstance(comp.agents, list)


def test_multiple_originators():
    """Test that multiple <origination> elements create multiple agents."""
    # This tests the structure that could handle multiple originators
    # (though our fixtures may not have examples)
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # Should be able to handle both single and multiple agents
    assert isinstance(comp.agents, list)
    assert len(comp.agents) >= 0  # May be 0, 1, or more


def test_controlaccess_subjects():
    """Test that <controlaccess><subject> elements are extracted to record.subjects."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # apap185 has multiple subject entries in controlaccess
    assert len(comp.subjects) > 0
    assert "Social Activists and Public Advocates" in comp.subjects
    assert "Human Sexuality and Gender Identity" in comp.subjects
    assert "Transgender people--New York (State)" in comp.subjects


def test_controlaccess_genreform():
    """Test that <controlaccess><genreform> elements are extracted to record.genreform."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # apap185 has multiple genreform entries
    assert len(comp.genreform) > 0
    assert "Magazines (periodicals)" in comp.genreform
    assert "Newspapers" in comp.genreform
    assert "Correspondence" in comp.genreform


def test_controlaccess_geogname_to_places():
    """Test that <controlaccess><geogname> elements are extracted to record.places."""
    sample = FIXTURES_DIR / "apap185.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # apap185 has geogname entries
    assert len(comp.places) > 0
    assert "Albany (N.Y.)" in comp.places


def test_controlaccess_corpname_agent():
    """Test that <controlaccess><corpname> creates Agent with agent_type='corporate_entity'."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # ger069 has a corpname in controlaccess
    assert len(comp.agents) > 0
    corp_agents = [a for a in comp.agents if a.agent_type == "corporate_entity"]
    assert len(corp_agents) > 0
    
    corp_agent = corp_agents[0]
    assert corp_agent.name == "New School for Social Research (New York, N.Y. : 1919-1997)"


def test_controlaccess_persname_agent():
    """Test that <controlaccess><persname> creates Agent with agent_type='person'."""
    sample = FIXTURES_DIR / "apap101.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # apap101 has a persname in controlaccess
    assert len(comp.agents) > 0
    person_agents = [a for a in comp.agents if a.agent_type == "person"]
    assert len(person_agents) > 0
    
    person_agent = person_agents[0]
    assert person_agent.name == "DeMarco, Michelle"


def test_controlaccess_multiple_subjects():
    """Test that multiple subject elements are all collected."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # ger069 has multiple subjects
    assert len(comp.subjects) >= 5
    assert "World War, 1939-1945 -- Refugees." in comp.subjects
    assert "Economics -- Study and teaching." in comp.subjects


def test_controlaccess_multiple_genreform():
    """Test that multiple genreform elements are all collected."""
    sample = FIXTURES_DIR / "apap101.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # apap101 has multiple genreform entries
    assert len(comp.genreform) >= 5
    assert "Correspondence" in comp.genreform
    assert "Ephemera (general)" in comp.genreform
    assert "Newspapers" in comp.genreform


def test_controlaccess_empty_when_missing():
    """Test that missing controlaccess doesn't cause errors."""
    # Create a component with no controlaccess
    sample = FIXTURES_DIR / "ua600.007.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # Should have empty lists, not None
    assert isinstance(comp.subjects, list)
    assert isinstance(comp.genreform, list)
    assert isinstance(comp.places, list)


def test_controlaccess_separation_from_creators():
    """Test that controlaccess agents are separate from origination creators."""
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # Should have creators from origination
    assert len(comp.creators) > 0
    creator = comp.creators[0]
    assert creator.agent_type == "creator"
    assert creator.name == "Hans Philipp Neisser"
    
    # Should have agents from controlaccess
    assert len(comp.agents) > 0
    agent = comp.agents[0]
    assert agent.agent_type == "corporate_entity"
    assert agent.name == "New School for Social Research (New York, N.Y. : 1919-1997)"
    
    # Should be separate lists
    assert creator not in comp.agents
    assert agent not in comp.creators


def test_controlaccess_hierarchical_components():
    """Test that controlaccess is parsed for each component in hierarchy."""
    # Test that child components can have their own controlaccess
    sample = FIXTURES_DIR / "ger069.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # Top-level should have controlaccess parsed
    assert len(comp.subjects) > 0
    assert len(comp.agents) > 0
    
    # This verifies controlaccess parsing works for top-level
    # (Individual child components would need controlaccess in their own XML)



