from description_harvester.plugins import Plugin

class DefaultPlugin(Plugin):
	"""Default plugin template showing available customization hooks.
	
	Copy this file to ~/.description_harvester/ or your plugin directory
	and customize the methods below to add institution-specific logic.
	"""
	plugin_name = "default"

	def __init__(self):
		"""Initialize your plugin. Run any setup code here."""
		print(f"Set up {self.plugin_name} plugin for reading digital object data.")

		# Set up any prerequisites or checks here

	def custom_repository(self, resource):
		"""Customize the repository name based on resource data.
		
		Args:
			resource (dict): ArchivesSpace resource API object containing fields like:
				- id_0, id_1, id_2, id_3: Resource identifier parts
				- title: Resource title
				- ead_id: EAD ID
				- repository: Repository reference dict with 'ref' key
		
		Returns:
			str: Custom repository name, or None to use default behavior
		
		Example:
			# Return custom name based on ID prefix
			if resource['id_0'].startswith('special'):
				return "Special Collections"
			return None
		"""
		pass
		# Uncomment to implement custom logic:
		# if resource['id_0'].startswith('apap'):
		#     return "National Death Penalty Archive"
		# return None

	def update_dao(self, dao):
		"""Enrich digital object with additional data from external sources.
		
		Args:
			dao (DigitalObject): Digital object with fields:
				- identifier (str): URL or identifier (e.g., IIIF manifest URL)
				- label (str): Display label
				- action (str): Display action ('embed' or 'link')
				- type (str): Object type (e.g., 'web_archive', 'iiif')
				- metadata (dict): Additional metadata fields
				- text_content (str): Full text content for indexing
				- rights_statement (str): Rights information
				- thumbnail_href (str): URL to thumbnail image
		
		Returns:
			DigitalObject: Updated dao with enriched metadata
		
		Example with IIIF utilities:
			from description_harvester.iiif_utils import enrich_dao_from_manifest
			
			if 'manifest.json' in dao.identifier:
				# Option 1: Use convenience function to extract everything
				enrich_dao_from_manifest(dao, manifest_url=dao.identifier)
				
				# Option 2: Fine-grained control
				# from description_harvester.iiif_utils import fetch_manifest, extract_text_from_manifest
				# manifest = fetch_manifest(dao.identifier)
				# if manifest:
				#     dao.text_content = extract_text_from_manifest(manifest)
				#     dao.metadata['custom_field'] = 'custom_value'
			
			return dao
		"""
		# Uncomment to implement custom logic:
		# from description_harvester.iiif_utils import enrich_dao_from_manifest
		# if 'manifest.json' in dao.identifier:
		#     enrich_dao_from_manifest(dao, manifest_url=dao.identifier)
		return dao
