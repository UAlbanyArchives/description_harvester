import yaml
from pathlib import Path

class Config:

	def __init__(self):
		with open(Path.home() / ".description_indexer.yml", "r") as f:
			config = yaml.safe_load(f)

			for k in config.keys():
				setattr(self, k, config[k])
