import yaml
from pathlib import Path

class Config:

	def __init__(self):
		with open(Path.home() / ".description_harvester.yml", "r") as f:
			config = yaml.safe_load(f)

			for k in config.keys():
				setattr(self, k, config[k])


	def read_repositories(slug):
		"""
		Reads the `repositories.yml` configuration file from the user's home directory
		and retrieves the `name` of a repository based on the provided slug.

		Parameters:
		-----------
		slug : str
			The case-insensitive slug to look for within the repository keys in the YAML file.

		Returns:
		--------
		str
			The name of the repository matching the given slug, if found.

		"""

		repositories_path = Path.home() / "repositories.yml"

		if not repositories_path.exists():
			raise FileNotFoundError(f"The repositories configuration file {repositories_path} does not exist.")

		try:
			with open(repositories_path, "r") as f:
				repositories = yaml.safe_load(f) or {}
		except yaml.YAMLError as e:
			raise yaml.YAMLError(f"Error parsing YAML file: {e}")
		
		slug = slug.strip().lower()
		for key, repo_data in repositories.items():
			if key.lower() == slug:
				return repo_data.get('name', None)

		raise ValueError(f"No repository found for the specified slug: '{slug}'")

