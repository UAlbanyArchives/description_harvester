import os
from pathlib import Path
import json
import hashlib
from unittest.mock import Mock, MagicMock

import pytest

from description_harvester.outputs.arclight import Arclight
from description_harvester.models.description import Component, Date, Extent, Agent, Container, DigitalObject
from description_harvester.models.arclight import SolrCollection, SolrComponent


def create_minimal_component(component_id="test001", level="collection", title="Test Collection"):
    """Helper to create a minimal Component for testing."""
    comp = Component()
    comp.id = component_id
    comp.collection_id = component_id
    comp.repository = "Test Repository"
    comp.level = level
    comp.collection_name = title
    comp.title = title
    comp.dates = []
    comp.extents = []
    comp.languages = []
    comp.creators = []
    comp.agents = []
    comp.subjects = []
    comp.genreform = []
    comp.places = []
    comp.containers = []
    comp.digital_objects = []
    comp.components = []
    return comp


class TestArclightInit:
    """Test Arclight initialization."""
    
    def test_init_with_solr_and_config(self):
        """Test that Arclight initializes with solr connection and metadata config."""
        mock_solr = Mock()
        metadata_config = [{"ssim": ["field1", "field2"]}, {"ssm": ["field3"]}]
        
        arclight = Arclight(mock_solr, metadata_config)
        
        assert arclight.solr == mock_solr
        assert arclight.metadata_config == metadata_config
    
    def test_init_with_default_separator(self):
        """Test that default component_id_separator is '_'."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        assert arclight.component_id_separator == "_"
    
    def test_init_with_custom_separator(self):
        """Test that custom component_id_separator can be set."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [], component_id_separator="-")
        
        assert arclight.component_id_separator == "-"
    
    def test_init_with_empty_separator(self):
        """Test that component_id_separator can be empty string."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [], component_id_separator="")
        
        assert arclight.component_id_separator == ""


class TestComponentIdSeparator:
    """Test component ID separator functionality."""
    
    def test_component_id_with_default_separator(self):
        """Test that component IDs use default '_' separator."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        child = create_minimal_component("comp001", "series", "Series 1")
        child.collection_id = "coll001"  # Child needs parent's collection_id
        child.dates = [Date(expression="1950")]
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        # Component ID should be collection_id + "_" + component_id
        assert result.components[0].id == "coll001_comp001"
    
    def test_component_id_with_custom_separator(self):
        """Test that component IDs use custom separator."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [], component_id_separator="-")
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        child = create_minimal_component("comp001", "series", "Series 1")
        child.collection_id = "coll001"  # Child needs parent's collection_id
        child.dates = [Date(expression="1950")]
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        # Component ID should be collection_id + "-" + component_id
        assert result.components[0].id == "coll001-comp001"
    
    def test_component_id_with_empty_separator(self):
        """Test that component IDs can have no separator."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [], component_id_separator="")
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        child = create_minimal_component("comp001", "series", "Series 1")
        child.collection_id = "coll001"  # Child needs parent's collection_id
        child.dates = [Date(expression="1950")]
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        # Component ID should be collection_id + "" + component_id (no separator)
        assert result.components[0].id == "coll001comp001"
    
    def test_component_id_with_dots_replaced(self):
        """Test that dots in IDs are replaced with hyphens before joining."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [], component_id_separator="_")
        
        collection = create_minimal_component("coll.001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        child = create_minimal_component("comp.001", "series", "Series 1")
        child.collection_id = "coll.001"  # Child needs parent's collection_id
        child.dates = [Date(expression="1950")]
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        # Dots should be replaced with hyphens, then joined with separator
        assert result.components[0].id == "coll-001_comp-001"


class TestStripText:
    """Test the strip_text method for removing HTML."""
    
    def test_strip_text_simple_string(self):
        """Test stripping HTML from a simple string."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.strip_text("<p>Hello World</p>")
        assert result == "Hello World"
    
    def test_strip_text_list_of_strings(self):
        """Test stripping HTML from a list of strings."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.strip_text(["<p>First paragraph</p>", "<p>Second paragraph</p>"])
        assert result == "First paragraph Second paragraph"
    
    def test_strip_text_complex_html(self):
        """Test stripping complex HTML with nested tags."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.strip_text("<div><p>Text with <i>italic</i> and <b>bold</b></p></div>")
        assert result == "Text with italic and bold"
    
    def test_strip_text_with_emph_tags(self):
        """Test stripping EAD emph tags."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.strip_text('<emph render="italic">Emphasized text</emph>')
        assert result == "Emphasized text"


class TestReplaceEmphTags:
    """Test the replace_emph_tags method for converting EAD tags to HTML."""
    
    def test_replace_emph_italic(self):
        """Test replacing emph render='italic' with <i> tag."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.replace_emph_tags('<emph render="italic">Italic text</emph>')
        assert result == "<i>Italic text</i>"
    
    def test_replace_emph_bold(self):
        """Test replacing emph render='bold' with <b> tag."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.replace_emph_tags('<emph render="bold">Bold text</emph>')
        assert result == "<b>Bold text</b>"
    
    def test_replace_emph_underline(self):
        """Test replacing emph render='underline' with <u> tag."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.replace_emph_tags('<emph render="underline">Underlined text</emph>')
        assert result == "<u>Underlined text</u>"
    
    def test_replace_emph_no_render_defaults_to_italic(self):
        """Test that emph without render attribute defaults to italic."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.replace_emph_tags('<emph>Default text</emph>')
        assert result == "<i>Default text</i>"
    
    def test_replace_emph_sub(self):
        """Test replacing emph render='sub' with <sub> tag."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.replace_emph_tags('<emph render="sub">Subscript</emph>')
        assert result == "<sub>Subscript</sub>"
    
    def test_replace_emph_super(self):
        """Test replacing emph render='super' with <sup> tag."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        result = arclight.replace_emph_tags('<emph render="super">Superscript</emph>')
        assert result == "<sup>Superscript</sup>"


class TestConvertCollectionBasics:
    """Test basic conversion of Component to SolrCollection."""
    
    def test_convert_minimal_collection(self):
        """Test converting a minimal collection component."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950-1960")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert isinstance(result, SolrCollection)
        assert result.id == "test001"
        assert result.level_ssm == ["collection"]
        assert result.repository_ssm == ["Test Repository"]
    
    def test_convert_sets_hashed_id(self):
        """Test that convert sets a hashed ID."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950-1960")]
        
        result = arclight.convert(comp, "Test Repository")
        
        expected_hash = hashlib.md5("test001".encode('utf-8')).hexdigest()
        assert result.hashed_id_ssi == expected_hash
    
    def test_convert_replaces_dots_in_id(self):
        """Test that dots in IDs are replaced with hyphens."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component(component_id="test.001.xyz")
        comp.dates = [Date(expression="1950-1960")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.id == "test-001-xyz"
        assert "." not in result.id


class TestConvertDates:
    """Test date conversion in Arclight output."""
    
    def test_convert_date_with_expression(self):
        """Test converting a date with expression."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950-1960")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert "1950-1960" in result.unitdate_ssm
        assert result.normalized_date_ssm == ["1950-1960"]
    
    def test_convert_date_with_begin_end(self):
        """Test converting a date with begin/end."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950-1960", begin="1950", end="1960")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.date_range_isim == list(range(1950, 1961))
        assert "1950-1960" in result.unitdate_ssm
    
    def test_convert_bulk_date(self):
        """Test converting a bulk date."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950-1960", date_type="bulk")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.normalized_date_ssm == ["bulk 1950-1960"]
    
    def test_convert_multiple_dates(self):
        """Test converting multiple dates."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [
            Date(expression="1950-1960"),
            Date(expression="1975", date_type="bulk")
        ]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert len(result.unitdate_ssm) == 2
        assert "1950-1960" in result.unitdate_ssm
        assert "1975" in result.unitdate_ssm


class TestConvertTitle:
    """Test title conversion in Arclight output."""
    
    def test_convert_simple_title(self):
        """Test converting a simple title."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component(title="Test Collection Title")
        comp.dates = [Date(expression="1950")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.title_ssm == ["Test Collection Title"]
        assert result.title_tesim == ["Test Collection Title"]
        assert result.normalized_title_ssm == ["Test Collection Title, 1950"]
    
    def test_convert_title_with_emph(self):
        """Test converting a title with emph tags."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component(title='<emph render="italic">Emphasized</emph> Title')
        comp.dates = [Date(expression="1950")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.title_ssm == ["Emphasized Title"]  # stripped
        assert result.title_html_tesm == ["<i>Emphasized</i> Title"]  # converted
    
    def test_convert_title_with_html(self):
        """Test converting a title with HTML tags."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component(title="<p>Title with HTML</p>")
        comp.dates = [Date(expression="1950")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.title_ssm == ["Title with HTML"]


class TestConvertExtents:
    """Test extent conversion in Arclight output."""
    
    def test_convert_single_extent(self):
        """Test converting a single extent."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.extents = [Extent(number="5", unit="linear feet")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.extent_ssm == ["5 linear feet"]
        assert result.extent_tesim == ["5 linear feet"]
    
    def test_convert_multiple_extents(self):
        """Test converting multiple extents."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.extents = [
            Extent(number="5", unit="linear feet"),
            Extent(number="10", unit="boxes")
        ]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert len(result.extent_ssm) == 2
        assert "5 linear feet" in result.extent_ssm
        assert "10 boxes" in result.extent_ssm


class TestConvertLanguages:
    """Test language conversion in Arclight output."""
    
    def test_convert_single_language(self):
        """Test converting a single language."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.languages = ["English"]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.language_ssim == ["English"]
    
    def test_convert_multiple_languages(self):
        """Test converting multiple languages."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.languages = ["English", "French", "German"]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.language_ssim == ["English, French, German"]


class TestConvertAgents:
    """Test agent and creator conversion in Arclight output."""
    
    def test_convert_person_creator(self):
        """Test converting a person creator."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.creators = [Agent(name="John Smith", agent_type="creator")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert "John Smith" in result.creator_ssm
        assert "John Smith" in result.creator_ssim
        assert result.creator_sort == "John Smith"
    
    def test_convert_corporate_entity_agent(self):
        """Test converting a corporate entity agent."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.agents = [Agent(name="Test Corporation", agent_type="corporate_entity")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.corpname_ssim == ["Test Corporation"]
        assert "Test Corporation" in result.names_ssim
    
    def test_convert_family_agent(self):
        """Test converting a family agent."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.agents = [Agent(name="Smith Family", agent_type="family")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.famname_ssim == ["Smith Family"]
        assert "Smith Family" in result.names_ssim
    
    def test_convert_person_agent(self):
        """Test converting a person agent."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.agents = [Agent(name="Jane Doe", agent_type="person")]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.persname_ssim == ["Jane Doe"]
        assert "Jane Doe" in result.names_ssim
    
    def test_convert_multiple_creators(self):
        """Test converting multiple creators."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.creators = [
            Agent(name="John Smith", agent_type="creator"),
            Agent(name="Jane Doe", agent_type="creator")
        ]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert len(result.creator_ssm) == 2
        assert "John Smith" in result.creator_ssm
        assert "Jane Doe" in result.creator_ssm
        # creator_sort should be the alphabetically first one
        assert result.creator_sort == "Jane Doe"


class TestConvertSubjects:
    """Test subject conversion in Arclight output."""
    
    def test_convert_subjects(self):
        """Test converting subjects."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.subjects = ["History", "Politics", "Economics"]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.access_subjects_ssm == ["History", "Politics", "Economics"]
        assert result.access_subjects_ssim == ["History", "Politics", "Economics"]
    
    def test_convert_genreform(self):
        """Test converting genreform."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.genreform = ["Correspondence", "Photographs"]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.genreform_ssim == ["Correspondence", "Photographs"]
    
    def test_convert_places(self):
        """Test converting places."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.places = ["New York", "Boston"]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.geogname_ssm == ["New York", "Boston"]
        assert result.geogname_ssim == ["New York", "Boston"]
        assert result.places_ssim == ["New York", "Boston"]


class TestConvertNotes:
    """Test note conversion in Arclight output."""
    
    def test_convert_abstract(self):
        """Test converting abstract note."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.abstract = ["This is the abstract text."]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.abstract_tesim == ["This is the abstract text."]
        assert result.abstract_html_tesm == ["This is the abstract text."]
    
    def test_convert_scopecontent(self):
        """Test converting scopecontent note."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.scopecontent = ["<p>Scope and content description.</p>"]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.scopecontent_tesim == ["Scope and content description."]
        assert "<p>" not in result.scopecontent_tesim[0]
    
    def test_convert_note_with_heading(self):
        """Test converting note with heading."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.bioghist = ["Biographical text"]
        comp.bioghist_heading = "Biography"
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.bioghist_tesim == ["Biographical text"]
        assert result.bioghist_heading_ssm == ["Biography"]
    
    def test_convert_note_with_emph_tags(self):
        """Test converting note with emph tags."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.scopecontent = ['Text with <emph render="italic">emphasis</emph>']
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.scopecontent_tesim == ["Text with emphasis"]
        assert result.scopecontent_html_tesm == ["Text with <i>emphasis</i>"]
    
    def test_convert_accessrestrict_note(self):
        """Test converting accessrestrict note (special handling)."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.accessrestrict = ["Access is restricted."]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.accessrestrict_tesim == ["Access is restricted."]
    
    def test_convert_userestrict_note(self):
        """Test converting userestrict note (special handling)."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.userestrict = ["Use is restricted."]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.userestrict_tesim == ["Use is restricted."]
        assert result.access_terms_ssm == ["Use is restricted."]


class TestConvertContainers:
    """Test container conversion in Arclight output."""
    
    def test_convert_single_container(self):
        """Test converting a single container."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        container = Container()
        container.top_container = "box"
        container.top_container_indicator = "1"
        comp.containers = [container]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert "box 1" in result.containers_ssim
    
    def test_convert_container_with_sub_container(self):
        """Test converting container with sub-container."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        container = Container()
        container.top_container = "box"
        container.top_container_indicator = "1"
        container.sub_container = "folder"
        container.sub_container_indicator = "5"
        comp.containers = [container]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert "box 1" in result.containers_ssim
        assert "folder 5" in result.containers_ssim
    
    def test_convert_container_with_all_levels(self):
        """Test converting container with all three levels."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        container = Container()
        container.top_container = "box"
        container.top_container_indicator = "1"
        container.sub_container = "folder"
        container.sub_container_indicator = "5"
        container.sub_sub_container = "item"
        container.sub_sub_container_indicator = "3"
        comp.containers = [container]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert "box 1" in result.containers_ssim
        assert "folder 5" in result.containers_ssim
        assert "item 3" in result.containers_ssim


class TestConvertDigitalObjects:
    """Test digital object conversion in Arclight output."""
    
    def test_convert_digital_object_basic(self):
        """Test converting a basic digital object."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        dao = DigitalObject(identifier="https://example.com/object1")
        dao.label = "Object Label"
        comp.digital_objects = [dao]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.dado_identifier_ssm == "https://example.com/object1"
        assert result.dado_label_tesim == "Object Label"
        assert result.has_online_content_ssim == ["Online access"]
        assert result.online_item_count_is == 1
    
    def test_convert_digital_object_with_metadata(self):
        """Test converting digital object with custom metadata."""
        mock_solr = Mock()
        metadata_config = [{"ssim": ["field1", "field2"]}, {"ssm": ["field3"]}]
        arclight = Arclight(mock_solr, metadata_config)
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        dao = DigitalObject(identifier="https://example.com/object1")
        dao.metadata = {"field1": ["value1", "value2"], "field3": "value3"}
        comp.digital_objects = [dao]
        
        result = arclight.convert(comp, "Test Repository")
        
        result_dict = result.to_dict()
        assert result_dict["dado_field1_ssim"] == ["value1", "value2"]
        assert result_dict["dado_field3_ssm"] == ["value3"]
    
    def test_convert_digital_object_legacy_format(self):
        """Test that digital objects are also stored in legacy format."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        dao = DigitalObject(identifier="https://example.com/object1")
        dao.label = "Test Label"
        comp.digital_objects = [dao]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert len(result.digital_objects_ssm) == 1
        legacy_dao = json.loads(result.digital_objects_ssm[0])
        assert legacy_dao["href"] == "https://example.com/object1"
        assert legacy_dao["label"] == "Test Label"
    
    def test_convert_digital_object_marks_online_content(self):
        """Test that digital objects mark the collection as having online content."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        dao = DigitalObject(identifier="https://example.com/object1")
        comp.digital_objects = [dao]
        
        result = arclight.convert(comp, "Test Repository")
        
        assert result.has_online_content_ssim == ["Online access"]
        assert result.online_item_count_is == 1


class TestConvertHierarchy:
    """Test conversion of hierarchical components."""
    
    def test_convert_component_hierarchy(self):
        """Test converting a collection with child components."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        # Create parent collection
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Create child component
        child = create_minimal_component("comp001", "series", "Series 1")
        child.dates = [Date(expression="1950")]
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        assert len(result.components) == 1
        assert isinstance(result.components[0], SolrComponent)
        assert result.components[0].level_ssm == ["series"]
        assert result.total_component_count_is == 1
    
    def test_convert_nested_hierarchy(self):
        """Test converting nested component hierarchy."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        # Create collection
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Create series
        series = create_minimal_component("series001", "series", "Series 1")
        series.dates = [Date(expression="1950")]
        
        # Create file under series
        file_comp = create_minimal_component("file001", "file", "File 1")
        file_comp.dates = [Date(expression="1950")]
        series.components.append(file_comp)
        
        collection.components.append(series)
        
        result = arclight.convert(collection, "Test Repository")
        
        assert len(result.components) == 1
        assert len(result.components[0].components) == 1
        assert result.total_component_count_is == 2
    
    def test_convert_component_parent_relationships(self):
        """Test that child components have correct parent relationships."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        child = create_minimal_component("comp001", "series", "Series 1")
        child.dates = [Date(expression="1950")]
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        child_solr = result.components[0]
        assert "coll001" in child_solr.parent_ssim
        assert child_solr.parent_ssi == ["coll001"]
        assert child_solr.collection_ssm == ["Test Collection, 1950-1960"]
    
    def test_convert_component_sort_order(self):
        """Test that components are assigned sort order."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Add multiple children
        for i in range(3):
            child = create_minimal_component(f"comp00{i+1}", "series", f"Series {i+1}")
            child.dates = [Date(expression="1950")]
            collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        assert result.components[0].sort_isi == 1
        assert result.components[1].sort_isi == 2
        assert result.components[2].sort_isi == 3


class TestConvertOnlineContent:
    """Test online content marking and propagation."""
    
    def test_online_content_propagates_to_parents(self):
        """Test that online content in child marks parents."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Child with digital object
        child = create_minimal_component("comp001", "series", "Series 1")
        child.dates = [Date(expression="1950")]
        dao = DigitalObject(identifier="https://example.com/object1")
        child.digital_objects = [dao]
        
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        # Collection should be marked as having online content
        assert result.has_online_content_ssim == ["Online access"]
        assert result.online_item_count_is == 1
    
    def test_multiple_online_items_counted(self):
        """Test that multiple online items are counted correctly."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Add two children with digital objects
        for i in range(2):
            child = create_minimal_component(f"comp00{i+1}", "series", f"Series {i+1}")
            child.dates = [Date(expression="1950")]
            dao = DigitalObject(identifier=f"https://example.com/object{i+1}")
            child.digital_objects = [dao]
            collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        assert result.online_item_count_is == 2


class TestConvertWithRepositoryOverride:
    """Test repository name override functionality."""
    
    def test_repository_override(self):
        """Test that repository name can be overridden."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.repository = "Original Repository"
        
        result = arclight.convert(comp, "Override Repository")
        
        assert result.repository_ssm == ["Override Repository"]
        assert result.repository_ssim == ["Override Repository"]
    
    def test_repository_no_override(self):
        """Test that repository uses component value when not overridden."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        comp.repository = "Original Repository"
        
        result = arclight.convert(comp, None)
        
        assert result.repository_ssm == ["Original Repository"]


class TestCustomOnlineContentLabel:
    """Test custom online content label configuration."""
    
    def test_custom_online_content_label(self):
        """Test that custom online content label is used when provided."""
        mock_solr = Mock()
        custom_label = "Custom Online Label"
        arclight = Arclight(mock_solr, [], online_content_label=custom_label)
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Child with digital object
        child = create_minimal_component("comp001", "series", "Series 1")
        child.dates = [Date(expression="1950")]
        dao = DigitalObject(identifier="https://example.com/object1")
        child.digital_objects = [dao]
        
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        # Should use custom label
        assert result.has_online_content_ssim == [custom_label]
    
    def test_default_online_content_label(self):
        """Test that default label is used when no custom label provided."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Child with digital object
        child = create_minimal_component("comp001", "series", "Series 1")
        child.dates = [Date(expression="1950")]
        dao = DigitalObject(identifier="https://example.com/object1")
        child.digital_objects = [dao]
        
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        # Should use default label
        assert result.has_online_content_ssim == ["Online access"]


class TestConfigIntegration:
    """Integration tests for config → Arclight initialization."""
    
    def test_config_loads_default_separator(self, tmp_path, monkeypatch):
        """Test that Config loads default component_id_separator when not in config file."""
        # Create a minimal config without component_id_separator
        config_dir = tmp_path / ".description_harvester"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("solr_url: http://test.com\nsolr_core: test")
        
        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        
        # Import and create Config (will read from mocked location)
        from description_harvester.configurator import Config
        config = Config()
        
        # Should have default separator
        assert config.component_id_separator == "_"
    
    def test_config_loads_custom_separator(self, tmp_path, monkeypatch):
        """Test that Config loads custom component_id_separator from config file."""
        # Create config with custom separator
        config_dir = tmp_path / ".description_harvester"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text('solr_url: http://test.com\nsolr_core: test\ncomponent_id_separator: "-"')
        
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        
        from description_harvester.configurator import Config
        config = Config()
        
        assert config.component_id_separator == "-"
    
    def test_config_loads_empty_separator(self, tmp_path, monkeypatch):
        """Test that Config loads empty string separator from config file."""
        # Create config with empty separator (quoted to preserve empty string)
        config_dir = tmp_path / ".description_harvester"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text('solr_url: http://test.com\nsolr_core: test\ncomponent_id_separator: ""')
        
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        
        from description_harvester.configurator import Config
        config = Config()
        
        assert config.component_id_separator == ""
        assert isinstance(config.component_id_separator, str)
    
    def test_arclight_receives_separator_from_config(self, tmp_path, monkeypatch):
        """Integration test: Config → Arclight initialization with separator."""
        # Create config with custom separator
        config_dir = tmp_path / ".description_harvester"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text('solr_url: http://test.com\nsolr_core: test\ncomponent_id_separator: "||"')
        
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        
        from description_harvester.configurator import Config
        config = Config()
        
        # Simulate what happens in harvest() function
        mock_solr = Mock()
        arclight = Arclight(mock_solr, config.metadata, config.online_content_label, config.component_id_separator)
        
        # Verify Arclight received the separator
        assert arclight.component_id_separator == "||"
        
        # Test it actually uses it
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        child = create_minimal_component("comp001", "series", "Series 1")
        child.collection_id = "coll001"
        child.dates = [Date(expression="1950")]
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        assert result.components[0].id == "coll001||comp001"


class TestAddToSolr:
    """Test adding documents to Solr."""
    
    def test_add_calls_solr(self):
        """Test that add method calls solr.add with correct data."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        comp = create_minimal_component()
        comp.dates = [Date(expression="1950")]
        
        collection = arclight.convert(comp, "Test Repository")
        arclight.add(collection)
        
        # Verify solr.add was called once
        assert mock_solr.add.called
        assert mock_solr.add.call_count == 1
        
        # Verify it was called with a list containing a dict
        call_args = mock_solr.add.call_args[0][0]
        assert isinstance(call_args, list)
        assert len(call_args) == 1
        assert isinstance(call_args[0], dict)


class TestNestPath:
    """Test _nest_path_ field for Solr 9 nested document support."""
    
    def test_collection_nest_path(self):
        """Test that collection documents have _nest_path_ = '/'."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        result = arclight.convert(collection, "Test Repository")
        
        assert result._nest_path_ == "/"
    
    def test_single_level_component_nest_path(self):
        """Test that direct children of collection get _nest_path_ = '/0', '/1', etc."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Add multiple children
        for i in range(3):
            child = create_minimal_component(f"comp00{i+1}", "series", f"Series {i+1}")
            child.dates = [Date(expression="1950")]
            collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        
        assert result.components[0]._nest_path_ == "/0"
        assert result.components[1]._nest_path_ == "/1"
        assert result.components[2]._nest_path_ == "/2"
    
    def test_nested_component_nest_path(self):
        """Test that deeply nested components get correct hierarchical paths."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        # Create collection
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Create series (level 1)
        series = create_minimal_component("series001", "series", "Series 1")
        series.dates = [Date(expression="1950")]
        
        # Create file under series (level 2)
        file_comp = create_minimal_component("file001", "file", "File 1")
        file_comp.dates = [Date(expression="1950")]
        series.components.append(file_comp)
        
        # Create item under file (level 3)
        item_comp = create_minimal_component("item001", "item", "Item 1")
        item_comp.dates = [Date(expression="1950")]
        file_comp.components.append(item_comp)
        
        collection.components.append(series)
        
        result = arclight.convert(collection, "Test Repository")
        
        # Verify nest paths at each level
        assert result._nest_path_ == "/"
        assert result.components[0]._nest_path_ == "/0"  # series
        assert result.components[0].components[0]._nest_path_ == "/0/0"  # file
        assert result.components[0].components[0].components[0]._nest_path_ == "/0/0/0"  # item
    
    def test_multiple_branch_nest_paths(self):
        """Test nest paths with multiple branches in hierarchy."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        # Create two series
        for series_idx in range(2):
            series = create_minimal_component(f"series00{series_idx+1}", "series", f"Series {series_idx+1}")
            series.dates = [Date(expression="1950")]
            
            # Add two files to each series
            for file_idx in range(2):
                file_comp = create_minimal_component(f"file{series_idx}{file_idx}", "file", f"File {file_idx+1}")
                file_comp.dates = [Date(expression="1950")]
                series.components.append(file_comp)
            
            collection.components.append(series)
        
        result = arclight.convert(collection, "Test Repository")
        
        # Series nest paths
        assert result.components[0]._nest_path_ == "/0"
        assert result.components[1]._nest_path_ == "/1"
        
        # File nest paths under series 0
        assert result.components[0].components[0]._nest_path_ == "/0/0"
        assert result.components[0].components[1]._nest_path_ == "/0/1"
        
        # File nest paths under series 1
        assert result.components[1].components[0]._nest_path_ == "/1/0"
        assert result.components[1].components[1]._nest_path_ == "/1/1"
    
    def test_nest_path_in_dict_output(self):
        """Test that _nest_path_ is included in to_dict() output for Solr indexing."""
        mock_solr = Mock()
        arclight = Arclight(mock_solr, [])
        
        collection = create_minimal_component("coll001", "collection", "Test Collection")
        collection.dates = [Date(expression="1950-1960")]
        
        child = create_minimal_component("comp001", "series", "Series 1")
        child.dates = [Date(expression="1950")]
        collection.components.append(child)
        
        result = arclight.convert(collection, "Test Repository")
        result_dict = result.to_dict()
        
        # Check that _nest_path_ is in the dict output
        assert "_nest_path_" in result_dict
        assert result_dict["_nest_path_"] == "/"
        
        # Check nested component
        assert len(result_dict["components"]) == 1
        assert "_nest_path_" in result_dict["components"][0]
        assert result_dict["components"][0]["_nest_path_"] == "/0"
