import requests
from description_indexer.dao_plugins import DaoSystem

class Hyrax(DaoSystem):
	dao_system_name = "hyrax"

	def __init__(self):
		print (f"Setup {self.dao_system_name} dao system for reading digital object data.")

	def read_data(dao):
		print ("reading data from " + dao.href)

		return dao