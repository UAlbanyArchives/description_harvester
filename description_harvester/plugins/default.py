from description_harvester.plugins import Plugin

class MyPlugin(Plugin):
	plugin_name = "default"

	def __init__(self):
		print (f"Setup {self.plugin_name} plugin for reading digital object data.")

		# Set up any prerequisites or checks here

	def custom_repository(self, resource):
		pass
		#print (f"reading data from {resource['id_0']}")
		
		# custom logic for repository name here and return a string
		#return repo_name

	def read_data(self, dao):
		"""
		Reads and updates a digital object record, likely from dao.identifier or external sources

		Args:
			dao: The inital digital object record.

		Returns:
			dao: The updated digital object record with changes.
		"""
		#print (f"reading data from {dao.identifier}")
		
		# Add or override dao here
		# dao.metadata = {}

		return dao
