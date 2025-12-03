import pytest
from unittest.mock import Mock
import description_harvester.inputs.aspace as aspace_mod
import description_harvester.plugins as plugins_mod
from description_harvester.inputs.aspace import ArchivesSpace
from description_harvester.models.description import Component, Date, Extent, Agent, Container, DigitalObject


class FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code
    def json(self):
        return self._json

class FakeClient:
    def __init__(self, routes):
        self.routes = routes
    def get(self, path, params=None):
        # emulate ArchivesSnake client.get(path)
        key = (path, tuple(sorted((params or {}).items())))
        if key in self.routes:
            return FakeResponse(self.routes[key])
        # fallback to path only
        if (path, None) in self.routes:
            return FakeResponse(self.routes[(path, None)])
        # simple direct path mapping
        if path in self.routes:
            return FakeResponse(self.routes[path])
        raise KeyError(f"No fake route for: {path} params={params}")


@pytest.fixture
def make_aspace(monkeypatch):
    def _make(routes, repository_id=2):
        client = FakeClient(routes)
        # Patch ASnakeClient constructor to return our fake client
        monkeypatch.setattr(aspace_mod, 'ASnakeClient', lambda: client)
        # Disable plugin loading and clear registry to avoid side effects
        monkeypatch.setattr(aspace_mod, 'import_plugins', lambda *args, **kwargs: None)
        monkeypatch.setattr(plugins_mod.Plugin, 'registry', {}, raising=False)
        return ArchivesSpace(repository_id=repository_id)
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
        "lang_materials": [{"language_and_script": {"language": "eng"}}],
        "linked_agents": [],
        "subjects": [],
        "notes": [],
        "instances": [],
    }


def test_init_fetches_repository_name(monkeypatch, make_aspace):
    routes = {
        'repositories/2': {"name": "Test Repository"},
    }
    aspace = make_aspace(routes)
    assert aspace.repo_name == "Test Repository"


def test_read_basic_resource(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    routes = {
        'repositories/2': {"name": "Test Repository"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {
            "resources": [{"ref": resource["uri"]}]
        },
        resource["uri"]: resource,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {
            "waypoints": 0
        },
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    assert isinstance(rec, Component)
    assert rec.id == resource["ead_id"]
    assert rec.collection_id == resource["ead_id"]
    assert rec.collection_name == resource["title"]
    assert rec.repository == "Test Repository"
    assert [e.unit for e in rec.extents] == ["linear feet"]
    assert rec.languages == ["English"]
    assert rec.dates and rec.dates[0].expression == "1950-1960"


def test_read_uri(monkeypatch, make_aspace):
    resource = make_minimal_resource(ead_id="abc123")
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/resources/1': resource,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {
            "waypoints": 0
        },
    }
    aspace = make_aspace(routes)
    rec = aspace.read_uri(1)
    assert rec.id == "abc123"
    assert rec.collection_id == "abc123"
    assert rec.title == "Test Collection".replace("<emph>", "<i>").replace("</emph>", "</i>")


def test_agents_and_subjects(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    # linked agent and subject refs
    person_agent = {"title": "Jane Doe", "agent_type": "agent_person"}
    corp_agent = {"title": "ACME Corp", "agent_type": "agent_corporate_entity"}
    resource["linked_agents"] = [
        {"ref": "/agents/people/1", "role": "creator"},
        {"ref": "/agents/corporate_entities/1", "role": "source"},
    ]
    resource["subjects"] = [
        {"ref": "/subjects/1"},
        {"ref": "/subjects/2"},
        {"ref": "/subjects/3"},
    ]
    subject_topical = {"title": "Archives", "terms": [{"term_type": "topical"}]}
    subject_genre = {"title": "Photographs", "terms": [{"term_type": "genre_form"}]}
    subject_geo = {"title": "Albany, NY", "terms": [{"term_type": "geographic"}]}

    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        '/agents/people/1': person_agent,
        '/agents/corporate_entities/1': corp_agent,
        '/subjects/1': subject_topical,
        '/subjects/2': subject_genre,
        '/subjects/3': subject_geo,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    assert [a.name for a in rec.creators] == ["Jane Doe"]
    assert [a.agent_type for a in rec.creators] == ["person"]
    assert [a.name for a in rec.agents] == ["ACME Corp"]
    assert [a.agent_type for a in rec.agents] == ["corporate_entity"]
    assert rec.subjects == ["Archives"]
    assert rec.genreform == ["Photographs"]
    assert rec.places == ["Albany, NY"]


def test_notes_parsing(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    resource["notes"] = [
        {"publish": True, "jsonmodel_type": "note_singlepart", "type": "abstract", "content": ["Intro text"]},
        {"publish": True, "jsonmodel_type": "note_multipart", "type": "scopecontent", "subnotes": [
            {"publish": True, "jsonmodel_type": "note_text", "content": "Paragraph one\n\nParagraph two"}
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
    assert rec.abstract == ["Intro text"]
    assert rec.scopecontent == ["Paragraph one", "Paragraph two"]


def test_containers(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    resource["instances"] = [
        {
            "sub_container": {
                "top_container": {"ref": "/top_containers/1"},
                "type_2": "folder",
                "indicator_2": "1",
            }
        }
    ]
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        '/top_containers/1': {"type": "box", "indicator": "1"},
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    assert len(rec.containers) == 1
    c = rec.containers[0]
    assert c.top_container == "box"
    assert c.top_container_indicator == "1"
    assert c.sub_container == "folder"
    assert c.sub_container_indicator == "1"


def test_digital_objects_representative_filtering(monkeypatch, make_aspace):
    resource = make_minimal_resource()
    resource["instances"] = [
        {"instance_type": "digital_object", "is_representative": True, "digital_object": {"ref": "/digital_objects/1"}},
        {"instance_type": "digital_object", "digital_object": {"ref": "/digital_objects/2"}},
    ]
    # digital object responses with file_versions; only representative should be used
    dobj1 = {
        "publish": True,
        "title": "Object A",
        "digital_object_type": "image",
        "file_versions": [
            {"publish": True, "is_representative": True, "file_uri": "https://example.com/a.jpg", "xlink_show_attribute": "embed"},
            {"publish": True, "file_uri": "https://example.com/a2.jpg"},
        ],
    }
    dobj2 = {
        "publish": True,
        "title": "Object B",
        "digital_object_type": "audio",
        "file_versions": [
            {"publish": True, "file_uri": "https://example.com/b.mp3"}
        ],
    }
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        '/digital_objects/1': dobj1,
        '/digital_objects/2': dobj2,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    # Only representative instance (dobj1) should produce DAO
    assert len(rec.digital_objects) == 1
    dao = rec.digital_objects[0]
    assert dao.identifier == "https://example.com/a.jpg"
    assert dao.label == "Object A"
    assert dao.action == "embed"
    assert dao.type == "image"


def test_hierarchy_traversal(monkeypatch, make_aspace):
    # Resource with one child component via tree API
    resource = make_minimal_resource(title="Parent")
    child = {
        "jsonmodel_type": "archival_object",
        "uri": "/repositories/2/archival_objects/10",
        "ref_id": "xyz789",
        "publish": True,
        "level": "series",
        "title": "Child",
        "dates": [],
        "extents": [],
        "lang_materials": [],
        "linked_agents": [],
        "subjects": [],
        "notes": [],
        "instances": [],
    }
    routes = {
        'repositories/2': {"name": "Repo"},
        'repositories/2/find_by_id/resources?identifier[]=["test001"]': {"resources": [{"ref": resource["uri"]}]},
        resource["uri"]: resource,
        (f"{resource['uri']}/tree/root", tuple(sorted({"published_only": True}.items()))): {"waypoints": 1},
        (f"{resource['uri']}/tree/waypoint", tuple(sorted({"published_only": True, "offset": 0}.items()))): [
            {"uri": child["uri"]}
        ],
        child["uri"]: child,
        (f"{resource['uri']}/tree/node", tuple(sorted({"published_only": True, "node_uri": child["uri"]}.items()))): {"waypoints": 0},
    }
    aspace = make_aspace(routes)
    rec = aspace.read("test001")
    assert len(rec.components) == 1
    child_comp = rec.components[0]
    assert child_comp.id.startswith("aspace_")
    assert child_comp.collection_id == resource["ead_id"]
    assert child_comp.title == "Child"
