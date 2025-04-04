import time
import yaml
import pysolr
import argparse
from pathlib import Path
from datetime import datetime
from .configurator import Config
from .utils import write2disk
from description_harvester.outputs.arclight import Arclight
from description_harvester.inputs.aspace import ArchivesSpace

def harvest(args=None):

	parser = argparse.ArgumentParser(description='Description_harvester manages archival description.')
	parser.add_argument('--id', nargs="+", help='One or more ASpace id_0s to index.')
	parser.add_argument('--uri', nargs="+", help='One or more ASpace collection uri integers to index, such as 755 for /resources/755.')
	parser.add_argument('--delete', nargs="+", help='The ID for the collection to be removed from the index.')
	parser.add_argument('--updated', default=False, action="store_true", help='Index collections modified since last run.')
	parser.add_argument('--new', default=False, action="store_true", help='Index collections not already present in the index.')
	parser.add_argument('--hour', default=False, action="store_true", help='Index collections modified in the last hour.')
	parser.add_argument('--today', default=False, action="store_true", help='Index collections modified in the last 24 hours.')
	parser.add_argument('--solr_url', nargs=1, help='A solr URL, such as http://127.0.0.1:8983/solr, to override ~/.description_harvester.yml')
	parser.add_argument('--core', nargs=1, help='A solr core, such as blacklight-core, to override ~/.description_harvester.yml')
	parser.add_argument('--repo', help="A repository slug used by ArcLight. This will set the repository name using ArcLight's ~/repositories.yml")
	parser.add_argument('--repo_id', type=int, help='The numerical ID for the repository in ArchivesSpace. Will default to \'2\'.')
	#parser.add_argument('--ead', default=False, action="store_true", help='Optionally write to a EAD file(s).')

	if args is None:
		args = parser.parse_args()
	else:
		args = parser.parse_args(args)

	start_time = time.time()
	config = Config()
	
	#print (args)
	if not (args.id or args.new or args.updated or args.uri or args.hour or args.today or args.delete):
		parser.error('No action requested, need a collection ID or --updated or --new')
	
	if args.delete:
		solr = pysolr.Solr(config.solr_url + "/" + config.solr_core, always_commit=True)
		solr.ping()
		for collection_id in args.delete:
			solr.delete(id=collection_id.replace(".", "-"))
			print (f"Deleted {collection_id}")
	else:
		if args.repo:
			repository_name = Config.read_repositories(args.repo)
		else:
			repository_name = None

		arclight = Arclight(config.solr_url + "/" + config.solr_core, repository_name)
		if args.repo_id:
			aspace = ArchivesSpace(repository_id=str(args.repo_id))
		else:
			aspace = ArchivesSpace(repository_id=2)
		if args.updated or args.hour or args.today:
			if args.updated:
				time_since = config.last_query	
			elif args.hour:
				time_since = str(time.time() - 3600).split(".")[0]
			elif args.today:
				time_since = str(time.time() - 86400).split(".")[0]
			collection_uris = aspace.read_since(time_since)
			for collection_uri in collection_uris:
				record = aspace.read_uri(collection_uri)
				if record:
					solrDoc = arclight.convert(record)
					arclight.post(solrDoc)
					print (f"Indexed {record.id}")
		elif args.new:
			collection_ids = aspace.all_resource_ids()
			solr = pysolr.Solr(config.solr_url + "/" + config.solr_core, always_commit=True)
			solr.ping()
			for collection_id in collection_ids:
				results = solr.search(f"id:{collection_id.replace('.', '-')}", rows=1, **{"fl": "id"})
				if results.hits > 0:
					print(f"Skipping {collection_id} as it already exists.")
				else:
					record = aspace.read(collection_id)
					if record:
						solrDoc = arclight.convert(record)
						arclight.post(solrDoc)
						print (f"Indexed {collection_id}")
		elif args.id:
			for collection_id in args.id:
				record = aspace.read(collection_id)
				if record:
					#write2disk(record, collection_id)
					solrDoc = arclight.convert(record)
					arclight.post(solrDoc)
					print (f"Indexed {collection_id}")
		elif args.uri:
			for collection_uri in args.uri:
				record = aspace.read_uri(collection_uri)
				if record:
					solrDoc = arclight.convert(record)
					arclight.post(solrDoc)
					print (f"Indexed {collection_uri}")

		lastExportTime = time.time()
		endTimeHuman = datetime.utcfromtimestamp(lastExportTime).strftime('%Y-%m-%d %H:%M:%S')
		config.last_query = str(lastExportTime).split(".")[0]
		with open(Path.home() / ".description_harvester.yml", "w") as f:
			yaml.dump(config.__dict__, f)
		print (f"Stored last run time as: {endTimeHuman}")
	end_time = time.time()
	duration = end_time - start_time
	print(f"Execution time: {duration:.4f} seconds")
	