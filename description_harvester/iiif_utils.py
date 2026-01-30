"""Utilities for working with IIIF manifests in plugins.

This module provides helper functions for plugin authors who want to enrich
digital objects with data from IIIF Presentation API manifests (v2 and v3).

Example usage in a plugin:
    from description_harvester.iiif_utils import fetch_manifest, extract_text_from_manifest
    
    def update_dao(self, dao):
        if 'manifest.json' in dao.identifier:
            manifest = fetch_manifest(dao.identifier)
            if manifest:
                dao.text_content = extract_text_from_manifest(manifest)
                dao.thumbnail_href = get_thumbnail_url(manifest)
        return dao
"""

import requests
from typing import Optional, Union, List, Dict, Any


def fetch_manifest(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """Fetch and parse a IIIF manifest from a URL.
    
    Args:
        url: URL to the IIIF manifest (typically ending in manifest.json)
        timeout: Request timeout in seconds (default: 10)
        
    Returns:
        Parsed manifest as a dictionary, or None if fetch failed
        
    Example:
        >>> manifest = fetch_manifest('https://example.org/iiif/manifest.json')
        >>> if manifest:
        ...     print(manifest.get('label'))
    """
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Warning: Failed to fetch manifest from {url} (status {response.status_code})")
            return None
    except Exception as e:
        print(f"Error fetching manifest from {url}: {e}")
        return None


def get_manifest_version(manifest: Dict[str, Any]) -> Optional[str]:
    """Detect IIIF Presentation API version from manifest.
    
    Args:
        manifest: Parsed IIIF manifest dictionary
        
    Returns:
        "3" for IIIF v3, "2" for IIIF v2, or None if version cannot be determined
        
    Example:
        >>> version = get_manifest_version(manifest)
        >>> if version == "3":
        ...     # Use v3-specific logic
    """
    context = manifest.get("@context", "")
    if isinstance(context, list):
        context = context[0]
    
    if "presentation/3" in context:
        return "3"
    elif "presentation/2" in context or manifest.get("@type") == "sc:Manifest":
        return "2"
    return None


def extract_lang_value(obj: Union[Dict, List, str], 
                      prefer_language: str = "en",
                      allow_multivalued: bool = False) -> Union[str, List[str]]:
    """Extract language-specific value(s) from IIIF multilingual fields.
    
    IIIF v3 uses language maps like {"en": ["Title"], "fr": ["Titre"]}.
    This function extracts values in the preferred language.
    
    Args:
        obj: IIIF field value (dict with language keys, list, or string)
        prefer_language: Preferred language code (default: "en")
        allow_multivalued: If True, return list; if False, return first value as string
        
    Returns:
        String or list of strings based on allow_multivalued parameter
        
    Example:
        >>> label = {"en": ["My Collection"], "fr": ["Ma Collection"]}
        >>> extract_lang_value(label)
        'My Collection'
        >>> extract_lang_value(label, allow_multivalued=True)
        ['My Collection']
    """
    if isinstance(obj, dict):
        values = obj.get(prefer_language) or next(iter(obj.values()), [])
        if not isinstance(values, list):
            values = [values]
        return values if allow_multivalued else (values[0] if values else "")
    
    elif isinstance(obj, list):
        return obj if allow_multivalued else (obj[0] if obj else "")
    
    elif isinstance(obj, str):
        return [obj] if allow_multivalued else obj
    
    return [] if allow_multivalued else ""


def get_thumbnail_url(manifest: Dict[str, Any]) -> Optional[str]:
    version = get_manifest_version(manifest)

    # --- explicit thumbnail in the manifest ---
    if version == "3":
        canvases = manifest.get("items", [])
        if canvases:
            thumbs = canvases[0].get("thumbnail", [])
            if isinstance(thumbs, list) and thumbs:
                return thumbs[0].get("id") or thumbs[0].get("@id")

    elif version == "2":
        sequences = manifest.get("sequences", [])
        if sequences:
            canvases = sequences[0].get("canvases", [])
            if canvases:
                thumbs = canvases[0].get("thumbnail")
                if isinstance(thumbs, dict):
                    return thumbs.get("@id")
                elif isinstance(thumbs, str):
                    return thumbs

    # --- fallback: derive from image service if present ---
    try:
        if version == "3":
            canvas = manifest.get("items", [])[0]

            anno_pages = canvas.get("items", [])
            if not anno_pages:
                return None

            annos = anno_pages[0].get("items", [])
            if not annos:
                return None

            body = annos[0].get("body", {})
            services = body.get("service")

            if not services:
                return None

            if isinstance(services, dict):
                services = [services]

            service_id = services[0].get("id") or services[0].get("@id")
            if service_id:
                return f"{service_id}/full/200,/0/default.jpg"

        elif version == "2":
            canvas = manifest.get("sequences", [])[0].get("canvases", [])[0]

            images = canvas.get("images", [])
            if not images:
                return None

            resource = images[0].get("resource", {})
            service = resource.get("service")

            if not isinstance(service, dict):
                return None

            service_id = service.get("@id")
            if service_id:
                return f"{service_id}/full/200,/0/default.jpg"

    except (IndexError, KeyError, TypeError):
        pass

    return None


def get_rights_statement(manifest: Dict[str, Any]) -> Optional[str]:
    """Extract rights/license statement from IIIF manifest.
    
    Args:
        manifest: Parsed IIIF manifest dictionary
        
    Returns:
        Rights statement URL or text, or None if not found
        
    Example:
        >>> rights = get_rights_statement(manifest)
        >>> if rights:
        ...     dao.rights_statement = rights
    """
    # Try v3 'rights' field first, then v2 'license' field
    return manifest.get("rights") or manifest.get("license")


def extract_metadata_fields(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata fields from IIIF manifest into a flat dictionary.
    
    Args:
        manifest: Parsed IIIF manifest dictionary
        
    Returns:
        Dictionary of metadata key-value pairs
        
    Example:
        >>> metadata = extract_metadata_fields(manifest)
        >>> dao.metadata.update(metadata)
    """
    metadata = {}
    version = get_manifest_version(manifest)
    
    for entry in manifest.get("metadata", []):
        if version == "3":
            label = extract_lang_value(entry.get("label", ""))
            value = extract_lang_value(entry.get("value", ""), allow_multivalued=True)
        else:  # v2
            label = entry.get("label", "")
            value = entry.get("value", "")
        
        if label:
            metadata[label] = value
    
    return metadata


def fetch_text_content(url: str, format_hint: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    """Fetch text content from various formats (plain text, hOCR, ALTO XML).
    
    Args:
        url: URL to the text resource
        format_hint: MIME type or format indicator (e.g., "text/plain", "application/alto+xml")
        timeout: Request timeout in seconds (default: 10)
        
    Returns:
        Extracted text content, or None if fetch/parse failed
        
    Example:
        >>> text = fetch_text_content(rendering_url, format_hint="text/plain")
        >>> if text:
        ...     dao.text_content = text
    """
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            print(f"Warning: Failed to fetch text from {url} (status {response.status_code})")
            return None
        
        format_lower = (format_hint or "").lower()
        
        # Plain text
        if "text/plain" in format_lower or ".txt" in format_lower:
            return response.text.strip()
        
        # hOCR (HTML with OCR data)
        elif "hocr" in format_lower or "text/html" in format_lower:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                words = [span.get_text() for span in soup.find_all("span", class_="ocrx_word")]
                return " ".join(words).strip() if words else None
            except ImportError:
                print("Warning: BeautifulSoup4 required for hOCR parsing. Install with: pip install beautifulsoup4")
                return None
        
        # ALTO XML
        elif "alto" in format_lower or "application/xml" in format_lower:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "xml")
                words = [tag.get("CONTENT", "") for tag in soup.find_all("String")]
                return " ".join(words).strip() if words else None
            except ImportError:
                print("Warning: BeautifulSoup4 required for ALTO parsing. Install with: pip install beautifulsoup4")
                return None
        
        return None
        
    except Exception as e:
        print(f"Error fetching text from {url}: {e}")
        return None


def extract_text_from_renderings(manifest: Dict[str, Any]) -> Optional[str]:
    """Extract text content from IIIF manifest renderings.
    
    Checks manifest-level rendering resources for plain text, hOCR, or ALTO files.
    Prioritizes plain text, then hOCR, then ALTO.
    
    Args:
        manifest: Parsed IIIF manifest dictionary
        
    Returns:
        Extracted text content, or None if no text found
        
    Example:
        >>> text = extract_text_from_renderings(manifest)
        >>> if text:
        ...     dao.text_content = text
    """
    for rendering in manifest.get("rendering", []):
        format_type = rendering.get("format", "").lower()
        url = rendering.get("id") or rendering.get("@id", "")
        
        if not url:
            continue
        
        # Try in priority order: txt, hocr, alto
        if "text/plain" in format_type or ".txt" in format_type:
            text = fetch_text_content(url, format_hint=format_type)
            if text:
                return text
        elif "hocr" in format_type:
            text = fetch_text_content(url, format_hint=format_type)
            if text:
                return text
        elif "alto" in format_type:
            text = fetch_text_content(url, format_hint=format_type)
            if text:
                return text
    
    return None


def extract_text_from_annotations(manifest: Dict[str, Any]) -> Optional[str]:
    """Extract text content from canvas annotations in IIIF manifest.
    
    Looks for TextualBody annotations in canvas annotation pages.
    
    Args:
        manifest: Parsed IIIF manifest dictionary
        
    Returns:
        Extracted text content from first TextualBody found, or None
        
    Example:
        >>> text = extract_text_from_annotations(manifest)
        >>> if text:
        ...     dao.text_content = text
    """
    version = get_manifest_version(manifest)
    
    # Get canvases based on version
    if version == "3":
        canvases = manifest.get("items", [])
    elif version == "2":
        sequences = manifest.get("sequences", [])
        canvases = sequences[0].get("canvases", []) if sequences else []
    else:
        return None
    
    # Search for TextualBody in annotations
    for canvas in canvases:
        # Check direct annotations
        annotations = canvas.get("annotations", [])
        for annotation_page in annotations:
            items = annotation_page.get("items", [])
            for item in items:
                body = item.get("body", {})
                if isinstance(body, dict) and body.get("type") == "TextualBody":
                    return body.get("value")
        
        # Check items -> annotations (v3 structure)
        items = canvas.get("items", [])
        for item in items:
            annotations = item.get("annotations", [])
            for page in annotations:
                for annotation in page.get("items", []):
                    body = annotation.get("body", {})
                    if isinstance(body, dict) and body.get("type") == "TextualBody":
                        return body.get("value")
    
    return None


def extract_text_from_manifest(manifest: Dict[str, Any]) -> Optional[str]:
    """Extract text content from IIIF manifest using all available methods.
    
    Tries in order:
    1. Manifest-level renderings (plain text, hOCR, ALTO)
    2. Canvas annotations with TextualBody
    
    Args:
        manifest: Parsed IIIF manifest dictionary
        
    Returns:
        Extracted text content, or None if no text found
        
    Example:
        >>> manifest = fetch_manifest(dao.identifier)
        >>> if manifest:
        ...     dao.text_content = extract_text_from_manifest(manifest)
    """
    # Try renderings first (usually more complete)
    text = extract_text_from_renderings(manifest)
    if text:
        return text
    
    # Fall back to annotations
    return extract_text_from_annotations(manifest)


def enrich_dao_from_manifest(dao, manifest_url: str = None, manifest: Dict[str, Any] = None) -> bool:
    """Convenience function to enrich a DigitalObject with IIIF manifest data.
    
    Populates: thumbnail_href, rights_statement, text_content, and metadata fields.
    Either provide manifest_url (to fetch) or pre-fetched manifest dict.
    
    Args:
        dao: DigitalObject instance to enrich
        manifest_url: URL to fetch manifest from (optional)
        manifest: Pre-fetched manifest dictionary (optional)
        
    Returns:
        True if enrichment succeeded, False otherwise
        
    Example:
        >>> from description_harvester.iiif_utils import enrich_dao_from_manifest
        >>> 
        >>> def update_dao(self, dao):
        ...     if 'manifest.json' in dao.identifier:
        ...         enrich_dao_from_manifest(dao, manifest_url=dao.identifier)
        ...     return dao
    """
    if manifest is None and manifest_url:
        manifest = fetch_manifest(manifest_url)
    
    if manifest is None:
        return False
    
    # Initialize metadata if needed
    if dao.metadata is None:
        dao.metadata = {}
    
    # Extract and set fields
    thumbnail = get_thumbnail_url(manifest)
    if thumbnail:
        dao.thumbnail_href = thumbnail
    
    rights = get_rights_statement(manifest)
    if rights:
        dao.rights_statement = rights
    
    text = extract_text_from_manifest(manifest)
    if text:
        dao.text_content = text
    
    # Extract metadata fields
    metadata = extract_metadata_fields(manifest)
    version = get_manifest_version(manifest)
    
    # Handle special fields that map to dao attributes
    for label, value in metadata.items():
        label_lower = label.lower()
        
        # Map subjects and creators to dao attributes
        if label_lower in ("subjects", "creators"):
            if isinstance(value, str):
                value = [value]
            elif not isinstance(value, list):
                value = [str(value)]
            setattr(dao, label_lower, value)
        else:
            # Everything else goes to metadata dict
            dao.metadata[label] = value
    
    return True
