"""Tests for IIIF utilities module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from description_harvester.iiif_utils import (
    fetch_manifest,
    get_manifest_version,
    extract_lang_value,
    get_thumbnail_url,
    get_rights_statement,
    extract_metadata_fields,
    fetch_text_content,
    extract_text_from_renderings,
    extract_text_from_annotations,
    extract_text_from_manifest,
    enrich_dao_from_manifest,
)
from description_harvester.models.description import DigitalObject


# Sample IIIF v3 manifest
SAMPLE_MANIFEST_V3 = {
    "@context": "http://iiif.io/api/presentation/3/context.json",
    "id": "https://example.org/iiif/manifest/v3",
    "type": "Manifest",
    "label": {"en": ["Test Collection V3"]},
    "rights": "https://creativecommons.org/licenses/by/4.0/",
    "metadata": [
        {"label": {"en": ["Author"]}, "value": {"en": ["Test Author"]}},
        {"label": {"en": ["Date"]}, "value": {"en": ["2025"]}},
        {"label": {"en": ["Subjects"]}, "value": {"en": ["Labor unions", "Uptown campus"]}},
    ],
    "items": [
        {
            "id": "https://example.org/canvas/1",
            "type": "Canvas",
            "thumbnail": [
                {"id": "https://example.org/thumb.jpg", "type": "Image"}
            ],
        }
    ],
}

# Sample IIIF v2 manifest
SAMPLE_MANIFEST_V2 = {
    "@context": "http://iiif.io/api/presentation/2/context.json",
    "@type": "sc:Manifest",
    "@id": "https://example.org/iiif/manifest/v2",
    "label": "Test Collection V2",
    "license": "https://creativecommons.org/publicdomain/zero/1.0/",
    "metadata": [
        {"label": "Creator", "value": "Test Creator"},
        {"label": "subjects", "value": ["Art", "Photography"]},
    ],
    "sequences": [
        {
            "canvases": [
                {
                    "@id": "https://example.org/canvas/1",
                    "thumbnail": {"@id": "https://example.org/thumb-v2.jpg"},
                }
            ]
        }
    ],
}


class TestFetchManifest:
    """Tests for fetch_manifest function."""

    @patch('description_harvester.iiif_utils.requests.get')
    def test_fetch_manifest_success(self, mock_get):
        """Test successful manifest fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MANIFEST_V3
        mock_get.return_value = mock_response

        result = fetch_manifest("https://example.org/manifest.json")
        
        assert result == SAMPLE_MANIFEST_V3
        mock_get.assert_called_once_with("https://example.org/manifest.json", timeout=30)

    @patch('description_harvester.iiif_utils.requests.get')
    def test_fetch_manifest_404(self, mock_get):
        """Test manifest fetch with 404 error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = fetch_manifest("https://example.org/missing.json")
        
        assert result is None

    @patch('description_harvester.iiif_utils.requests.get')
    def test_fetch_manifest_exception(self, mock_get):
        """Test manifest fetch with network exception."""
        mock_get.side_effect = Exception("Network error")

        result = fetch_manifest("https://example.org/error.json")
        
        assert result is None


class TestGetManifestVersion:
    """Tests for get_manifest_version function."""

    def test_detect_v3_manifest(self):
        """Test detection of IIIF v3 manifest."""
        version = get_manifest_version(SAMPLE_MANIFEST_V3)
        assert version == "3"

    def test_detect_v2_manifest(self):
        """Test detection of IIIF v2 manifest."""
        version = get_manifest_version(SAMPLE_MANIFEST_V2)
        assert version == "2"

    def test_detect_v3_with_list_context(self):
        """Test v3 detection when context is a list."""
        manifest = {
            "@context": [
                "http://iiif.io/api/presentation/3/context.json",
                "http://example.org/other"
            ]
        }
        version = get_manifest_version(manifest)
        assert version == "3"

    def test_unknown_version(self):
        """Test with unknown or missing version."""
        manifest = {"@context": "http://unknown.org/context"}
        version = get_manifest_version(manifest)
        assert version is None


class TestExtractLangValue:
    """Tests for extract_lang_value function."""

    def test_extract_from_dict_english(self):
        """Test extracting English value from language map."""
        obj = {"en": ["English text"], "fr": ["French text"]}
        result = extract_lang_value(obj)
        assert result == "English text"

    def test_extract_from_dict_multivalued(self):
        """Test extracting multiple values from language map."""
        obj = {"en": ["First", "Second"]}
        result = extract_lang_value(obj, allow_multivalued=True)
        assert result == ["First", "Second"]

    def test_extract_from_dict_fallback_language(self):
        """Test fallback to first available language."""
        obj = {"fr": ["French only"]}
        result = extract_lang_value(obj)
        assert result == "French only"

    def test_extract_from_list(self):
        """Test extracting from list."""
        obj = ["Item 1", "Item 2"]
        result = extract_lang_value(obj)
        assert result == "Item 1"
        
        result_multi = extract_lang_value(obj, allow_multivalued=True)
        assert result_multi == ["Item 1", "Item 2"]

    def test_extract_from_string(self):
        """Test extracting from plain string."""
        obj = "Simple string"
        result = extract_lang_value(obj)
        assert result == "Simple string"

    def test_extract_empty(self):
        """Test extracting from empty values."""
        assert extract_lang_value({}) == ""
        assert extract_lang_value([]) == ""
        assert extract_lang_value({}, allow_multivalued=True) == []


class TestGetThumbnailUrl:
    """Tests for get_thumbnail_url function."""

    def test_get_thumbnail_v3(self):
        """Test extracting thumbnail from v3 manifest."""
        url = get_thumbnail_url(SAMPLE_MANIFEST_V3)
        assert url == "https://example.org/thumb.jpg"

    def test_get_thumbnail_v2_dict(self):
        """Test extracting thumbnail from v2 manifest (dict format)."""
        url = get_thumbnail_url(SAMPLE_MANIFEST_V2)
        assert url == "https://example.org/thumb-v2.jpg"

    def test_get_thumbnail_v2_string(self):
        """Test extracting thumbnail from v2 manifest (string format)."""
        manifest = {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@type": "sc:Manifest",
            "sequences": [
                {
                    "canvases": [
                        {"thumbnail": "https://example.org/thumb-string.jpg"}
                    ]
                }
            ]
        }
        url = get_thumbnail_url(manifest)
        assert url == "https://example.org/thumb-string.jpg"

    def test_get_thumbnail_not_found(self):
        """Test when no thumbnail is available."""
        manifest = {
            "@context": "http://iiif.io/api/presentation/3/context.json",
            "items": []
        }
        url = get_thumbnail_url(manifest)
        assert url is None


class TestGetRightsStatement:
    """Tests for get_rights_statement function."""

    def test_get_rights_v3(self):
        """Test extracting rights from v3 manifest."""
        rights = get_rights_statement(SAMPLE_MANIFEST_V3)
        assert rights == "https://creativecommons.org/licenses/by/4.0/"

    def test_get_rights_v2(self):
        """Test extracting license from v2 manifest."""
        rights = get_rights_statement(SAMPLE_MANIFEST_V2)
        assert rights == "https://creativecommons.org/publicdomain/zero/1.0/"

    def test_get_rights_not_found(self):
        """Test when no rights statement is available."""
        manifest = {"@context": "http://iiif.io/api/presentation/3/context.json"}
        rights = get_rights_statement(manifest)
        assert rights is None


class TestExtractMetadataFields:
    """Tests for extract_metadata_fields function."""

    def test_extract_metadata_v3(self):
        """Test extracting metadata from v3 manifest."""
        metadata = extract_metadata_fields(SAMPLE_MANIFEST_V3)
        
        assert metadata["Author"] == ["Test Author"]
        assert metadata["Date"] == ["2025"]
        assert metadata["Subjects"] == ["Labor unions", "Uptown campus"]

    def test_extract_metadata_v2(self):
        """Test extracting metadata from v2 manifest."""
        metadata = extract_metadata_fields(SAMPLE_MANIFEST_V2)
        
        assert metadata["Creator"] == "Test Creator"
        assert metadata["subjects"] == ["Art", "Photography"]

    def test_extract_metadata_empty(self):
        """Test extracting from manifest with no metadata."""
        manifest = {"@context": "http://iiif.io/api/presentation/3/context.json"}
        metadata = extract_metadata_fields(manifest)
        
        assert metadata == {}


class TestFetchTextContent:
    """Tests for fetch_text_content function."""

    @patch('description_harvester.iiif_utils.requests.get')
    def test_fetch_plain_text(self, mock_get):
        """Test fetching plain text content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "  Sample plain text  "
        mock_get.return_value = mock_response

        result = fetch_text_content("https://example.org/text.txt", format_hint="text/plain")
        
        assert result == "Sample plain text"

    @patch('description_harvester.iiif_utils.requests.get')
    def test_fetch_text_404(self, mock_get):
        """Test fetching text with 404 error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = fetch_text_content("https://example.org/missing.txt", format_hint="text/plain")
        
        assert result is None

    @patch('description_harvester.iiif_utils.requests.get')
    def test_fetch_text_no_format_hint(self, mock_get):
        """Test fetching text without format hint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Some text"
        mock_get.return_value = mock_response

        result = fetch_text_content("https://example.org/unknown.dat")
        
        assert result is None


class TestExtractTextFromRenderings:
    """Tests for extract_text_from_renderings function."""

    @patch('description_harvester.iiif_utils.fetch_text_content')
    def test_extract_from_text_rendering(self, mock_fetch):
        """Test extracting text from plain text rendering."""
        mock_fetch.return_value = "Extracted text content"
        
        manifest = {
            "rendering": [
                {
                    "id": "https://example.org/text.txt",
                    "format": "text/plain"
                }
            ]
        }
        
        result = extract_text_from_renderings(manifest)
        
        assert result == "Extracted text content"
        mock_fetch.assert_called_once()

    @patch('description_harvester.iiif_utils.fetch_text_content')
    def test_extract_prioritizes_text_over_hocr(self, mock_fetch):
        """Test that plain text is prioritized over hOCR."""
        mock_fetch.side_effect = [None, "hOCR text"]
        
        manifest = {
            "rendering": [
                {
                    "id": "https://example.org/text.txt",
                    "format": "text/plain"
                },
                {
                    "id": "https://example.org/text.hocr",
                    "format": "text/vnd.hocr+html"
                }
            ]
        }
        
        result = extract_text_from_renderings(manifest)
        
        assert result == "hOCR text"

    def test_extract_no_renderings(self):
        """Test with no renderings available."""
        manifest = {}
        result = extract_text_from_renderings(manifest)
        assert result is None


class TestExtractTextFromAnnotations:
    """Tests for extract_text_from_annotations function."""

    def test_extract_from_v3_annotations(self):
        """Test extracting text from v3 annotation."""
        manifest = {
            "@context": "http://iiif.io/api/presentation/3/context.json",
            "items": [
                {
                    "annotations": [
                        {
                            "items": [
                                {
                                    "body": {
                                        "type": "TextualBody",
                                        "value": "Annotation text content"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = extract_text_from_annotations(manifest)
        assert result == "Annotation text content"

    def test_extract_from_v2_annotations(self):
        """Test extracting text from v2 annotation."""
        manifest = {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@type": "sc:Manifest",
            "sequences": [
                {
                    "canvases": [
                        {
                            "annotations": [
                                {
                                    "items": [
                                        {
                                            "body": {
                                                "type": "TextualBody",
                                                "value": "V2 annotation text"
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = extract_text_from_annotations(manifest)
        assert result == "V2 annotation text"

    def test_extract_no_annotations(self):
        """Test with no annotations available."""
        manifest = {
            "@context": "http://iiif.io/api/presentation/3/context.json",
            "items": []
        }
        result = extract_text_from_annotations(manifest)
        assert result is None


class TestExtractTextFromManifest:
    """Tests for extract_text_from_manifest function."""

    @patch('description_harvester.iiif_utils.extract_text_from_renderings')
    @patch('description_harvester.iiif_utils.extract_text_from_annotations')
    def test_extract_prioritizes_renderings(self, mock_annotations, mock_renderings):
        """Test that renderings are checked before annotations."""
        mock_renderings.return_value = "Rendering text"
        mock_annotations.return_value = "Annotation text"
        
        result = extract_text_from_manifest(SAMPLE_MANIFEST_V3)
        
        assert result == "Rendering text"
        mock_renderings.assert_called_once()
        mock_annotations.assert_not_called()

    @patch('description_harvester.iiif_utils.extract_text_from_renderings')
    @patch('description_harvester.iiif_utils.extract_text_from_annotations')
    def test_extract_falls_back_to_annotations(self, mock_annotations, mock_renderings):
        """Test fallback to annotations when renderings have no text."""
        mock_renderings.return_value = None
        mock_annotations.return_value = "Annotation text"
        
        result = extract_text_from_manifest(SAMPLE_MANIFEST_V3)
        
        assert result == "Annotation text"
        mock_renderings.assert_called_once()
        mock_annotations.assert_called_once()


class TestEnrichDaoFromManifest:
    """Tests for enrich_dao_from_manifest function."""

    @patch('description_harvester.iiif_utils.fetch_manifest')
    def test_enrich_dao_with_url(self, mock_fetch):
        """Test enriching DAO by fetching manifest from URL."""
        mock_fetch.return_value = SAMPLE_MANIFEST_V3
        
        dao = DigitalObject()
        dao.identifier = "https://example.org/manifest.json"
        
        result = enrich_dao_from_manifest(dao, manifest_url=dao.identifier)
        
        assert result is True
        assert dao.thumbnail_href == "https://example.org/thumb.jpg"
        assert dao.rights_statement == "https://creativecommons.org/licenses/by/4.0/"
        assert "Author" in dao.metadata
        mock_fetch.assert_called_once_with("https://example.org/manifest.json")

    def test_enrich_dao_with_manifest_dict(self):
        """Test enriching DAO with pre-fetched manifest."""
        dao = DigitalObject()
        dao.identifier = "https://example.org/manifest.json"
        
        result = enrich_dao_from_manifest(dao, manifest=SAMPLE_MANIFEST_V3)
        
        assert result is True
        assert dao.thumbnail_href == "https://example.org/thumb.jpg"
        assert dao.rights_statement == "https://creativecommons.org/licenses/by/4.0/"

    def test_enrich_dao_maps_subjects_to_attribute(self):
        """Test that subjects metadata is mapped to dao.subjects attribute."""
        dao = DigitalObject()
        
        result = enrich_dao_from_manifest(dao, manifest=SAMPLE_MANIFEST_V3)
        
        assert result is True
        assert dao.subjects == ["Labor unions", "Uptown campus"]

    def test_enrich_dao_maps_creators_to_attribute(self):
        """Test that creators metadata is mapped to dao.creators attribute."""
        manifest = {
            "@context": "http://iiif.io/api/presentation/3/context.json",
            "metadata": [
                {"label": {"en": ["Creators"]}, "value": {"en": ["Artist 1", "Artist 2"]}}
            ]
        }
        
        dao = DigitalObject()
        result = enrich_dao_from_manifest(dao, manifest=manifest)
        
        assert result is True
        assert dao.creators == ["Artist 1", "Artist 2"]

    def test_enrich_dao_initializes_metadata(self):
        """Test that metadata dict is initialized if None."""
        dao = DigitalObject()
        assert dao.metadata is None
        
        enrich_dao_from_manifest(dao, manifest=SAMPLE_MANIFEST_V3)
        
        assert dao.metadata is not None
        assert isinstance(dao.metadata, dict)

    @patch('description_harvester.iiif_utils.fetch_manifest')
    def test_enrich_dao_returns_false_on_failure(self, mock_fetch):
        """Test that enrichment returns False when manifest fetch fails."""
        mock_fetch.return_value = None
        
        dao = DigitalObject()
        result = enrich_dao_from_manifest(dao, manifest_url="https://example.org/missing.json")
        
        assert result is False

    def test_enrich_dao_requires_manifest_or_url(self):
        """Test that enrichment fails without manifest or URL."""
        dao = DigitalObject()
        result = enrich_dao_from_manifest(dao)
        
        assert result is False

    @patch('description_harvester.iiif_utils.extract_text_from_manifest')
    def test_enrich_dao_sets_text_content(self, mock_extract_text):
        """Test that text content is extracted and set."""
        mock_extract_text.return_value = "Full text from manifest"
        
        dao = DigitalObject()
        enrich_dao_from_manifest(dao, manifest=SAMPLE_MANIFEST_V3)
        
        assert dao.text_content == "Full text from manifest"
