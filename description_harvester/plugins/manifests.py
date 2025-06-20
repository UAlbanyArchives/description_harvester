from description_harvester.plugins import Plugin
import requests

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
			
				# Initialize metadata if it's None
				if dao.metadata is None:
					dao.metadata = {}

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
					dao.type = 'application/ld+json;profile="http://iiif.io/api/presentation/3/context.json"'
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
					dao.type = 'application/ld+json;profile="http://iiif.io/api/presentation/2/context.json"'
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



