import pytest
import description_harvester.inputs.aspace as aspace_mod
import description_harvester.plugins as plugins_mod
from description_harvester.inputs.aspace import ArchivesSpace
from description_harvester.models.description import Component


class FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code
    def json(self):
        return self._json

class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []
    def get(self, path, params=None):
        self.calls.append((path, params))
        key = (path, tuple(sorted((params or {}).items())))
        if key in self.routes:
            return FakeResponse(self.routes[key])
        if (path, None) in self.routes:
            return FakeResponse(self.routes[(path, None)])
        if path in self.routes:
            return FakeResponse(self.routes[path])
        raise KeyError(f"No fake route for: {path} params={params}")

@pytest.fixture
def make_aspace(monkeypatch):
    def _make(routes, repository_id=2):
        client = FakeClient(routes)
        monkeypatch.setattr(aspace_mod, 'ASnakeClient', lambda: client)
        monkeypatch.setattr(aspace_mod, 'import_plugins', lambda *args, **kwargs: None)
        monkeypatch.setattr(plugins_mod.Plugin, 'registry', {}, raising=False)
        inst = ArchivesSpace(repository_id=repository_id)
        # expose client to test for call inspection
        inst.client = client
        return inst
    return _make


def make_minimal_resource(ead_id="test001", title="Test Collection"):
    return {
        "jsonmodel_type": "resource",
        "uri": f"/repositories/2/resources/1",
        "ead_id": ead_id,
        "id_0": ead_id,
        "publish": True,
        "level": "collection",
        "title": title,
        "dates": [{"date_type": "inclusive", "expression": "1950-1960"}],
        "extents": [{"number": "3", "extent_type": "linear feet"}],
        "lang_materials": [],
        "linked_agents": [],
        "subjects": [],
        "notes": [],
        "instances": [],
    }


def test_read_by_id_zero_and_many(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    routes_zero = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["missing"]': {"resources": []},
    }
    aspace = make_aspace(routes_zero)
    with pytest.raises(Exception):
        aspace.read("missing")

    routes_many = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["dup"]': {"resources": [{"ref": resource["uri"]},{"ref": resource["uri"]}]},
    }
    aspace = make_aspace(routes_many)
    with pytest.raises(Exception):
        aspace.read("dup")


def test_unpublished_resource_read_uri(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    resource["publish"] = False
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/resources/1': resource,
    }
    aspace = make_aspace(routes)
    assert aspace.read_uri(1) is None


def test_dates_variants(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    resource["dates"] = [
        {"date_type": "bulk", "expression": "1940-1945"},
        {"date_type": "inclusive", "begin": "1950", "end": "1960"},
        {"date_type": "inclusive", "begin": "1970"},
    ]
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    # Current implementation sets date_type only when begin/end are present
    assert [d.date_type for d in rec.dates] == [None, "inclusive", "inclusive"]
    assert rec.dates[1].begin == "1950" and rec.dates[1].end == "1960"
    assert rec.dates[2].begin == "1970"
    assert all(d.expression for d in rec.dates)


def test_language_notes(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    resource["lang_materials"] = [
        {"language_and_script": {"language": "eng"}, "notes": [{"content": ["Spanish", "French"]}]}
    ]
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    # English from code + notes list
    assert set(rec.languages) == {"English", "Spanish", "French"}


def test_bibliography_merge_and_lists(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    resource["notes"] = [
        {"publish": True, "jsonmodel_type": "note_bibliography", "type": "bibliography", "label": "Works A", "items": ["A1"]},
        {"publish": True, "jsonmodel_type": "note_bibliography", "type": "bibliography", "label": "Works B", "items": ["B1","B2"]},
        {"publish": True, "jsonmodel_type": "note_multipart", "type": "odd", "subnotes": [
            {"publish": True, "jsonmodel_type": "note_orderedlist", "items": ["One","Two"]}
        ]},
        {"publish": True, "jsonmodel_type": "note_multipart", "type": "custodhist", "subnotes": [
            {"publish": True, "jsonmodel_type": "note_chronology", "items": [
                {"event_date": "1900", "events": "Started"},
                {"event_date": "1950", "events": "Moved"},
            ]}
        ]},
    ]
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    # Heading is overwritten by generic label set, then bibliography appends
    assert rec.bibliography_heading == "Works B; Works B"
    assert rec.bibliography == ["A1", "B1", "B2"]
    assert rec.odd == ["One\nTwo"]
    # Chronology renders as HTML table with dates and events
    assert rec.custodhist == ["<table><tr><th>1900</th><td>Started</td></tr><tr><th>1950</th><td>Moved</td></tr></table>"]


def test_three_level_containers(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    resource["instances"] = [
        {
            "sub_container": {
                "top_container": {"ref": "/top_containers/1"},
                "type_2": "folder",
                "indicator_2": "1",
                "type_3": "item",
                "indicator_3": "3",
            }
        }
    ]
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        '/top_containers/1': {"type": "box", "indicator": "2"},
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    c = rec.containers[0]
    assert (c.top_container, c.top_container_indicator) == ("box", "2")
    # Current implementation maps type_3/indicator_3 to sub_container fields
    assert (c.sub_container, c.sub_container_indicator) == ("item", "3")


def test_dao_rewrite_and_publishing(monkeypatch, make_aspace):
    # Representative instance and file version rewrite
    resource = make_minimal_resource(ead_id="apap009", title="Parent")
    ao_uri = "/repositories/2/archival_objects/10"
    child = {
        "jsonmodel_type": "archival_object",
        "uri": ao_uri,
        "ref_id": "abcd1234",
        "publish": True,
        "level": "series",
        "title": "Child",
        "dates": [],
        "extents": [],
        "lang_materials": [],
        "linked_agents": [],
        "subjects": [],
        "notes": [],
        "instances": [
            {"instance_type": "digital_object", "is_representative": True, "digital_object": {"ref": "/digital_objects/1"}},
            {"instance_type": "digital_object", "digital_object": {"ref": "/digital_objects/2"}},
        ],
    }
    dobj1 = {
        "publish": True,
        "title": "Obj A",
        "digital_object_type": "mixed",
        "file_versions": [
            {"publish": True, "is_representative": True, "file_uri": "https://media.archives.albany.edu/apap009/abcd1234/manifest.json", "xlink_show_attribute": "embed"},
            {"publish": True, "file_uri": "https://example.com/other"},
        ],
    }
    dobj2 = {
        "publish": True,
        "title": "Obj B",
        "digital_object_type": "image",
        "file_versions": [
            {"publish": True, "file_uri": "https://example.com/ignored"}
        ],
    }
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 1},
        (f"{resource['uri']}/tree/waypoint", tuple(sorted({"published_only": True, "offset": 0}.items()))): [
            {"uri": ao_uri}
        ],
        ao_uri: child,
        (f"{resource['uri']}/tree/node", tuple(sorted({"published_only": True, "node_uri": ao_uri}.items()))): {"waypoints": 0},
        '/digital_objects/1': dobj1,
        '/digital_objects/2': dobj2,
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    # DAO comes from child, with rewritten manifest URL
    child_comp = rec.components[0]
    assert len(child_comp.digital_objects) == 1
    manifest = f"https://media.archives.albany.edu/{resource['ead_id']}/{child['ref_id']}/manifest.json"
    assert child_comp.digital_objects[0].identifier == manifest
    assert child_comp.digital_objects[0].action == "embed"


def test_multi_waypoints(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    child1 = {"jsonmodel_type": "archival_object", "uri": "/repositories/2/archival_objects/11", "ref_id": "r1", "publish": True, "level": "series", "title": "C1", "dates": [], "extents": [], "lang_materials": [], "linked_agents": [], "subjects": [], "notes": [], "instances": []}
    child2 = {"jsonmodel_type": "archival_object", "uri": "/repositories/2/archival_objects/12", "ref_id": "r2", "publish": True, "level": "series", "title": "C2", "dates": [], "extents": [], "lang_materials": [], "linked_agents": [], "subjects": [], "notes": [], "instances": []}
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 2},
        (f"{resource['uri']}/tree/waypoint", tuple(sorted({"published_only": True, "offset": 0}.items()))): [{"uri": child1["uri"]}],
        (f"{resource['uri']}/tree/waypoint", tuple(sorted({"published_only": True, "offset": 1}.items()))): [{"uri": child2["uri"]}],
        child1["uri"]: child1,
        child2["uri"]: child2,
        (f"{resource['uri']}/tree/node", tuple(sorted({"published_only": True, "node_uri": child1["uri"]}.items()))): {"waypoints": 0},
        (f"{resource['uri']}/tree/node", tuple(sorted({"published_only": True, "node_uri": child2["uri"]}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    assert [c.title for c in rec.components] == ["C1", "C2"]


def test_chronology_with_multiple_events(monkeypatch, make_aspace):
    """Test that chronology notes handle both string and list format for events."""
    resource = make_minimal_resource()
    resource["notes"] = [
        {"publish": True, "jsonmodel_type": "note_multipart", "type": "bioghist", "subnotes": [
            {"publish": True, "jsonmodel_type": "note_chronology", "items": [
                {"event_date": "1907", "events": "Published <i>Der schwarze Haufen</i>"},
                {"event_date": "1948-1964", "events": ["Wrote for <i>Deutsche Zeitung</i>", "Contributed to <i>Der Monat</i>", "Published in <i>Weltwoche</i>"]},
                {"event_date": "1980", "events": "Final article in <i>Dissent</i>"},
            ]}
        ]},
    ]
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    
    # Verify HTML table structure
    assert len(rec.bioghist) == 1
    chronology = rec.bioghist[0]
    assert chronology.startswith("<table>")
    assert chronology.endswith("</table>")
    
    # Verify dates in th tags
    assert "<th>1907</th>" in chronology
    assert "<th>1948-1964</th>" in chronology
    assert "<th>1980</th>" in chronology
    
    # Verify single event as string
    assert "<td>Published <i>Der schwarze Haufen</i></td>" in chronology
    
    # Verify multiple events joined with comma
    assert "<td>Wrote for <i>Deutsche Zeitung</i>, Contributed to <i>Der Monat</i>, Published in <i>Weltwoche</i></td>" in chronology
    
    # Verify final event
    assert "<td>Final article in <i>Dissent</i></td>" in chronology


def test_read_since_and_all_resource_ids(monkeypatch, make_aspace):
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/resources?all_ids=true&modified_since=12345': [100, 200],
        'repositories/2/resources?all_ids=true': [10, 20],
        'repositories/2/resources/10': {"id_0": "r10"},
        'repositories/2/resources/20': {"id_0": "r20"},
    }
    aspace = make_aspace(routes)
    assert aspace.read_since(12345) == [100, 200]
    assert aspace.all_resource_ids() == ["r10", "r20"]
