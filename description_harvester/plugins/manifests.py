from description_harvester.plugins import Plugin
from description_harvester.iiif_utils import fetch_manifest, enrich_dao_from_manifest
from urllib.parse import urlparse, urlunparse
import requests
import yaml

class ManifestsPlugin(Plugin):
    """Plugin for reading digital object data from IIIF manifests.
    
    This is a local implementation example showing how to fetch and parse
    IIIF manifests to enrich digital object metadata. It handles both IIIF
    manifests and institution-specific web archive formats.
    """
    plugin_name = "manifests"

    def __init__(self):
        print(f"Setup {self.plugin_name} plugin for reading digital object data from IIIF manifests.")

    def update_dao(self, dao):
        """
        Reads and processes IIIF manifest data, extracting relevant information such as:
            - The manifest version (V2 or V3)
            - Thumbnail image URL
            - Textual content from renderings or canvas annotations
            - Rights statements
            - Metadata
        and updates the dao DadoCM fields

        Args:
            dao: The inital digital object record.

        Returns:
            dao: The updated digital object record with additions from the manifest.
        """

        # Initialize metadata if it's None
        if dao.metadata is None:
            dao.metadata = {}

        if dao.type == "web_archive":
            # Needs local custom handing for web archives since theres no established way to serve via a manifest
            expected_url = False
            if dao.identifier.strip().lower().startswith("https://media.archives.albany.edu/"):
                parsed = urlparse(dao.identifier.strip())
                parts = parsed.path.strip("/").split("/")

                if len(parts) >= 2:
                    collection_id, object_id = parts[0], parts[1]

                    if len(object_id) == 32 and all(c in "0123456789abcdef" for c in object_id.lower()):
                        base_path = f"/{collection_id}/{object_id}"
                        metadata_url = urlunparse(parsed._replace(path=f"{base_path}/metadata.yml"))
                        content_url = urlunparse(parsed._replace(path=f"{base_path}/content.txt"))
                        thumbnail_url = urlunparse(parsed._replace(path=f"{base_path}/thumbnail.jpg"))
                        expected_url = True

                        try:
                            r_meta = requests.get(metadata_url, timeout=10)
                            r_content = requests.get(content_url, timeout=10)

                            if r_meta.status_code == 200 and r_content.status_code == 200:
                                metadata = yaml.safe_load(r_meta.text)
                                dao.metadata["resource_type"] = metadata.get("resource_type", None)
                                dao.metadata["date_uploaded"] = metadata.get("date_uploaded", None)
                                dao.metadata["replay_content"] = content_url

                                if metadata["license"].lower().strip() == "unknown":
                                    dao.rights_statement = metadata.get("rights_statement", None)
                                else:
                                    dao.rights_statement = metadata.get("license", None)

                                # if theres a more specific url within the warc/wacz
                                if "replay_link" in metadata.keys():
                                    dao.identifier = metadata["replay_link"]

                                dao.text_content = r_content.text

                                expected_url = True  # mark as successful

                                try:
                                    pdf_filename = metadata.get("replay_pdf", None)
                                    if pdf_filename:
                                        pdf_url = urlunparse(parsed._replace(path=f"{base_path}/pdf/{pdf_filename}"))
                                        r_pdf = requests.head(pdf_url, timeout=5)
                                        if r_pdf.status_code == 200:
                                            dao.metadata["replay_pdf"] = pdf_url
                                except requests.RequestException:
                                    pass

                                # Adds the thumbnail only if present
                                try:
                                    r_thumb = requests.head(thumbnail_url, timeout=5)
                                    if r_thumb.status_code == 200:
                                        dao.thumbnail_href = thumbnail_url
                                except requests.RequestException:
                                    pass

                        except requests.HTTPError as he:
                            print(f"HTTP error accessing URL: {he}")
                            expected_url = False
                        except requests.RequestException as re:
                            print(f"Network error accessing URL: {re}")
                            expected_url = False
                        except Exception as e:
                            print(f"Unexpected error: {e}")
                            expected_url = False
            
            # fallback for anything that failed
            if not expected_url:
                dao.action = "link"
                dao.rights_statement = "https://rightsstatements.org/vocab/InC-EDU/1.0/"
        else:
            # Handle IIIF manifests
            
            # Remove Mirador URL wrapper (local URL cleanup)
            if dao.identifier.startswith("https://media.archives.albany.edu?manifest="):
                dao.identifier = dao.identifier.removeprefix("https://media.archives.albany.edu?manifest=")

            # Start by checking if the identifier is a manifest URL
            if not "manifest.json" in dao.identifier and not "https://archives.albany.edu/catalog?f[archivesspace_record_tesim][]=" in dao.identifier:
                dao.action = "link"
            else:
                # Use iiif_utils to enrich the DAO with manifest data
                if enrich_dao_from_manifest(dao, manifest_url=dao.identifier):
                    dao.action = "embed"
                else:
                    print(f"Failed to fetch manifest, linking instead of embedding.")
                    dao.action = "link"

        # Return the updated dao object
        return dao



