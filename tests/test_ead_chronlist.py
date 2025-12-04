import pytest
from pathlib import Path
from lxml import etree

from description_harvester.inputs.ead import EAD

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "ead"


def test_render_chronlist_basic():
    """Test _render_chronlist generates HTML table from chronlist XML."""
    sample = FIXTURES_DIR / "ger071.xml"
    e = EAD(str(sample))
    
    # Parse the fixture to get a chronlist element
    xml_text = sample.read_text(encoding="utf-8")
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
    ns = {"ead": root.nsmap.get(None)}
    
    chronlist = root.find(".//ead:chronlist", namespaces=ns)
    assert chronlist is not None, "Fixture should contain a chronlist"
    
    # Render it
    result = e._render_chronlist(chronlist, ns)
    
    # Should produce a table
    assert result.startswith("<table>")
    assert result.endswith("</table>")
    assert "<tr>" in result
    assert "<th>" in result
    assert "<td>" in result


def test_render_chronlist_preserves_emph_tags():
    """Test that chronlist event parsing preserves and converts <emph> tags."""
    sample = FIXTURES_DIR / "ger071.xml"
    e = EAD(str(sample))
    
    xml_text = sample.read_text(encoding="utf-8")
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
    ns = {"ead": root.nsmap.get(None)}
    
    chronlist = root.find(".//ead:chronlist", namespaces=ns)
    result = e._render_chronlist(chronlist, ns)
    
    # Should convert <emph render="italic"> to <i>
    assert "<i>Der schwarze Haufen</i>" in result
    assert "<i>Economic Trends</i>" in result
    assert "<i>Espagne Creuset Politique</i>" in result
    assert "<i>Deutsche Zeitung</i>" in result
    
    # Should NOT contain raw EAD emph tags
    assert "<emph" not in result.lower()


def test_render_chronlist_multiple_events():
    """Test that chronlist handles eventgrp with multiple events."""
    sample = FIXTURES_DIR / "ger071.xml"
    e = EAD(str(sample))
    
    xml_text = sample.read_text(encoding="utf-8")
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
    ns = {"ead": root.nsmap.get(None)}
    
    chronlist = root.find(".//ead:chronlist", namespaces=ns)
    result = e._render_chronlist(chronlist, ns)
    
    # The 1948-1964 entry has multiple newspapers separated in the event text
    assert "1948-1964" in result
    # Should have the newspapers mentioned
    assert "Deutsche Zeitung" in result
    assert "Der Monat" in result
    assert "Weltwoche" in result


def test_chronlist_in_bioghist():
    """Test that chronlist is parsed as part of bioghist note field."""
    sample = FIXTURES_DIR / "ger071.xml"
    e = EAD(str(sample))
    comp = e.fetch(sample)
    
    # The fixture has a bioghist with a chronlist
    assert hasattr(comp, 'bioghist')
    assert comp.bioghist is not None
    assert isinstance(comp.bioghist, list)
    
    # Should have converted chronlist to HTML table
    bioghist_text = "\n".join(comp.bioghist)
    assert "<table>" in bioghist_text
    assert "<tr>" in bioghist_text
    
    # Should have dates from chronlist
    assert "1907" in bioghist_text
    assert "1980" in bioghist_text
    
    # Should have converted emph tags
    assert "<i>Der schwarze Haufen</i>" in bioghist_text
    assert "<i>Economic Trends</i>" in bioghist_text


def test_chronlist_dates_in_table():
    """Test that chronlist dates appear in table headers."""
    sample = FIXTURES_DIR / "ger071.xml"
    e = EAD(str(sample))
    
    xml_text = sample.read_text(encoding="utf-8")
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
    ns = {"ead": root.nsmap.get(None)}
    
    chronlist = root.find(".//ead:chronlist", namespaces=ns)
    result = e._render_chronlist(chronlist, ns)
    
    # Dates should be in <th> tags
    assert "<th>1907</th>" in result
    assert "<th>1925-1926</th>" in result
    assert "<th>1945-1950</th>" in result
    assert "<th>1980</th>" in result


def test_chronlist_events_in_table_data():
    """Test that chronlist events appear in table data cells."""
    sample = FIXTURES_DIR / "ger071.xml"
    e = EAD(str(sample))
    
    xml_text = sample.read_text(encoding="utf-8")
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
    ns = {"ead": root.nsmap.get(None)}
    
    chronlist = root.find(".//ead:chronlist", namespaces=ns)
    result = e._render_chronlist(chronlist, ns)
    
    # Events should be in <td> tags
    assert "<td>Born Heinz Maximilian Paechter" in result
    assert "<td>Married Hedwig Rösler" in result
    assert "<td>Died on December 10 in New York City.</td>" in result


def test_chronlist_no_phantom_event_tags():
    """Test that chronlist rendering doesn't leave phantom <event> tags."""
    sample = FIXTURES_DIR / "ger071.xml"
    e = EAD(str(sample))
    
    xml_text = sample.read_text(encoding="utf-8")
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
    ns = {"ead": root.nsmap.get(None)}
    
    chronlist = root.find(".//ead:chronlist", namespaces=ns)
    result = e._render_chronlist(chronlist, ns)
    
    # Should not contain any <event tags or </event> tags
    assert "<event" not in result.lower()
    assert "</event>" not in result.lower()
