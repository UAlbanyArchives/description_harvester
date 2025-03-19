from description_harvester.dao_plugins import DaoSystem

class MySystem(DaoSystem):
	dao_system_name = "default"

	def __init__(self):
		print (f"Setup {self.dao_system_name} dao system for reading digital object data.")

		# Set up any prerequisites or checks here

	def read_data(dao):
		pass
		#print (f"reading data from {dao.identifier}")
		
		# Add or override dao here
		# dao.metadata = {}

		return dao
