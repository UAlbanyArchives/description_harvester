from description_harvester.plugins import Plugin
from urllib.parse import urlparse, urlunparse
import requests
import yaml

class MyPlugin(Plugin):
    plugin_name = "manifests"

    def __init__(self):
        print (f"Setup {self.plugin_name} plugin for reading digital object data from IIIF manifests.")

        # Set up any prerequisites or checks here


    def extract_lang_value(self, obj, allow_multivalued=False):
        """
        Extracts language-specific value(s) from a dict, list, or string, preferring English ('en').

        Args:
            obj: A dictionary with language keys, a list of values, or a plain string.
            allow_multivalued (bool): If True, allows returning a list of values. If False, always returns a string.

        Returns:
            str or list: A string or list of strings based on allow_multivalued.
        """
        if isinstance(obj, dict):
            values = obj.get("en") or next(iter(obj.values()), [])
            if not isinstance(values, list):
                values = [values]
            return values if allow_multivalued else values[0] if values else ""

        elif isinstance(obj, list):
            return obj if allow_multivalued else obj[0] if obj else ""

        elif isinstance(obj, str):
            return [obj] if allow_multivalued else obj

        return [] if allow_multivalued else ""

    def read_txt_content(self, txt_url):
        """
        Read the text content from a .txt file by fetching it from the provided URL.

        Args:
            txt_url (str): The URL pointing to the .txt file to be read.

        Returns:
            str: The text content extracted from the .txt file. If the file cannot be fetched, returns an empty string.
        """
        try:
            # Fetch the .txt file content from the URL
            response = requests.get(txt_url)
            if response.status_code == 200:
                return response.text.strip()
            else:
                print(f"Warning: Failed to fetch .txt file from {txt_url}")
                return ""
        except Exception as e:
            print(f"Error while fetching .txt file from {txt_url}: {e}")
            return ""

    def read_hocr_content(self, hocr_url):
        """
        Read the text content from an .hocr file by parsing its XML structure.

        Args:
            hocr_url (str): The URL pointing to the .hocr file to be read.

        Returns:
            str: The extracted text content from the .hocr file. If unable to fetch or parse, returns an empty string.
        """
        try:
            # Fetch the .hocr file content from the URL
            response = requests.get(hocr_url)
            if response.status_code == 200:
                # Parse the .hocr content
                hocr_data = response.text
                soup = BeautifulSoup(hocr_data, "html.parser")
                # Extract text from the <span class="ocrx_word"> tags
                words = [span.get_text() for span in soup.find_all("span", class_="ocrx_word")]
                return " ".join(words).strip()
            else:
                print(f"Warning: Failed to fetch .hocr file from {hocr_url}")
                return ""
        except Exception as e:
            print(f"Error while fetching or parsing .hocr file from {hocr_url}: {e}")
            return ""

    def read_alto_content(self, alto_url):
        """
        Read the text content from an ALTO file by parsing its XML structure.

        Args:
            alto_url (str): The URL pointing to the .alto file to be read.

        Returns:
            str: The extracted text content from the .alto file. If unable to fetch or parse, returns an empty string.
        """
        try:
            # Fetch the .alto file content from the URL
            response = requests.get(alto_url)
            if response.status_code == 200:
                # Parse the .alto content
                alto_data = response.text
                soup = BeautifulSoup(alto_data, "xml")
                # Extract text from <String> tags
                words = [string_tag.get_text() for string_tag in soup.find_all("String")]
                return " ".join(words).strip()
            else:
                print(f"Warning: Failed to fetch .alto file from {alto_url}")
                return ""
        except Exception as e:
            print(f"Error while fetching or parsing .alto file from {alto_url}: {e}")
            return ""

    # Function to check renderings for .txt, .hocr, or ALTO files
    def check_renderings(self, renderings):
        """
        Checks a list of renderings to find and read the appropriate text content.
        This function prioritizes .txt renderings first, and falls back to .hocr and .alto if necessary.

        Args:
            renderings (list): A list of rendering objects, each containing 'format' and 'url' keys.

        Returns:
            str: The text content extracted from the first valid rendering found, or an empty string if no valid renderings are found.
        """
        for rendering in renderings:
            format = rendering.get("format", "").lower()
            url = rendering.get("id", "")
            # Check for .txt file format
            if "text/plain" in format or ".txt" in format:
                text_content = self.read_txt_content(url)
                if text_content:
                    return text_content
            
            # Check for .hocr file format
            elif ".hocr" in format:
                text_content = self.read_hocr_content(url)
                if text_content:
                    return text_content
            
            # Check for .alto file format
            elif ".alto" in format:
                text_content = self.read_alto_content(url)
                if text_content:
                    return text_content
        
        # Return an empty string if no suitable renderings were found
        return ""

    def read_data(self, dao):
        """
        Reads and processes IIIF manifest data, extracting relevant information such as:
        - The manifest version (V2 or V3)
        - Thumbnail image URL
        - Textual content from renderings or canvas annotations
        - Rights statements
        - Metadata

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
            dao.action = "link"
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
            # assume IIIF manifest because of our bad data

            # Start by checking if the identifier is a manifest URL
            if not "manifest.json" in dao.identifier and not "https://archives.albany.edu/catalog?f[archivesspace_record_tesim][]=" in dao.identifier:
                dao.action = "link"
            else:
                # Fetch the manifest
                response = requests.get(dao.identifier)
                if response.status_code != 200:
                    print (f"Failed to fetch manifest: {response.status_code}, linking instead of embeding.")
                    dao.action = "link"
                    #raise ValueError(f"Failed to fetch manifest: {response.status_code}")
                else:
                    dao.action = "embed"
                    dao.text_content = None

                    # Parse the manifest
                    manifest = response.json()
                    context = manifest.get("@context", "")
                    if isinstance(context, list):
                        context = context[0]

                    # Determine IIIF version (V3 or V2)
                    is_v3 = "presentation/3" in context
                    is_v2 = "presentation/2" in context or "@type" in manifest and manifest["@type"] == "sc:Manifest"

                    # Handle V3 Manifest
                    if is_v3:
                        canvases = manifest.get("items", [])
                        if canvases:
                            canvas = canvases[0]
                            thumbs = canvas.get("thumbnail", [])
                            if isinstance(thumbs, list) and thumbs:
                                dao.thumbnail_href = thumbs[0].get("id") or thumbs[0].get("@id")

                        # Check for manifest-level renderings first, then canvas annotations if needed
                        dao.text_content = self.check_renderings(manifest.get("rendering", []))
                        if not dao.text_content:
                            dao.text_content = self._extract_text_from_canvas(canvases)

                        # Set rights metadata
                        dao.rights_statement = manifest.get("rights")

                        # Add metadata to dao
                        for entry in manifest.get("metadata", []):
                            label = self.extract_lang_value(entry.get("label", ""))
                            value = self.extract_lang_value(entry.get("value", ""), allow_multivalued=True)

                            label_name = label.lower()
                            target_fields = {"subjects", "creators"}
                            if label_name in target_fields:
                                normalized_value = [value] if isinstance(value, str) else (
                                    value if isinstance(value, list) else [str(value)]
                                )
                                setattr(dao, label_name, normalized_value)
                            else:
                                dao.metadata[label] = value

                    # Handle V2 Manifest
                    elif is_v2:
                        sequences = manifest.get("sequences", [])
                        if sequences:
                            canvases = sequences[0].get("canvases", [])
                            if canvases:
                                canvas = canvases[0]
                                thumbs = canvas.get("thumbnail")
                                if isinstance(thumbs, dict):
                                    dao.thumbnail_href = thumbs.get("@id")
                                elif isinstance(thumbs, str):
                                    dao.thumbnail_href = thumbs

                                # Check for manifest-level renderings first, then canvas annotations if needed
                                dao.text_content = self.check_renderings(manifest.get("rendering", []))
                                if not dao.text_content:
                                    dao.text_content = self._extract_text_from_canvas(canvases)

                        # Set rights metadata for V2 manifest
                        dao.rights_statement = manifest.get("license") or manifest.get("rights")

                        # Add metadata to dao (v2)
                        for entry in manifest.get("metadata", []):
                            label = entry.get("label", "")
                            value = entry.get("value", "")

                            if label.lower() == "subjects":
                                if isinstance(value, str):
                                    dao.subjects = [value]
                                elif isinstance(value, list):
                                    dao.subjects = value
                                else:
                                    dao.subjects = [str(value)]
                            else:
                                dao.metadata[label] = value


        # Return the updated dao object
        return dao

    def _extract_text_from_canvas(self, canvases):
        """
        Extracts textual content from canvas annotations, including checking both direct annotations
        and annotations found within canvas items.

        Args:
            canvases: List of canvases from the IIIF manifest.

        Returns:
            str or None: The extracted textual content, or None if no text is found.
        """
        # Helper function to extract text from canvas annotations
        for canvas in canvases:
            annotations = canvas.get("annotations", [])
            for annotation_page in annotations:
                items = annotation_page.get("items", [])
                for item in items:
                    body = item.get("body", {})
                    if isinstance(body, dict):
                        # Check if it's a textual body (contains text content)
                        if body.get("type") == "TextualBody":
                            return body.get("value")

            # Or try items -> annotations if no direct textual body found
            items = canvas.get("items", [])
            for item in items:
                annotations = item.get("annotations", [])
                for page in annotations:
                    for annotation in page.get("items", []):
                        body = annotation.get("body", {})
                        if isinstance(body, dict) and body.get("type") == "TextualBody":
                            return body.get("value")
        
        # If no text content found, return None
        return None



