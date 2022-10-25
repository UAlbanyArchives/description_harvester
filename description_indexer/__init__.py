import time
import yaml
import pysolr
import argparse
from pathlib import Path
from datetime import datetime
from .configurator import Config
from description_indexer.outputs.arclight import Arclight
from description_indexer.inputs.aspace import ArchivesSpace

parser = argparse.ArgumentParser(description='Description_Indexer manages archival description.')
parser.add_argument('--id', nargs="+", help='One or more ASpace id_0s to index.')
parser.add_argument('--uri', nargs="+", help='One or more ASpace collection uri integers to index, such as 755 for /resources/755.')
parser.add_argument('--delete', default=False, action="store_true", help='an integer for the accumulator')
parser.add_argument('--new', default=False, action="store_true", help='Index collections modified since last run.')
parser.add_argument('--hour', default=False, action="store_true", help='Index collections modified in the last hour.')
parser.add_argument('--today', default=False, action="store_true", help='Index collections modified in the last 24 hours.')
parser.add_argument('--solr_url', nargs=1, help='A solr URL, such as http://127.0.0.1:8983/solr, to override ~/.description_indexer.yml')
parser.add_argument('--core', nargs=1, help='A solr core, such as blacklight-core, to override ~/.description_indexer.yml')
#parser.add_argument('--ead', default=False, action="store_true", help='Optionally write to a EAD file(s).')

def index():
	config = Config()
	args = parser.parse_args()
	#print (args)
	if not (args.id or args.new or args.uri or args.hour or args.today):
		parser.error('No action requested, need a collection ID or --new')
	
	if args.delete:
		solr = pysolr.Solr(config.solr_url + "/" + config.solr_core, always_commit=True)
		solr.ping()
		for collection_id in args.id:
			solr.delete(id=collection_id.replace(".", "-"))
			print (f"Deleted {collection_id}")
	else:
		arclight = Arclight(config.solr_url + "/" + config.solr_core)
		aspace = ArchivesSpace()
		if args.new or args.hour or args.today:
			if args.new:
				time_since = config.last_query	
			elif args.hour:
				time_since = str(time.time() - 3600).split(".")[0]
			elif args.today:
				time_since = str(time.time() - 86400).split(".")[0]
			records = aspace.read_since(time_since)
			for record in records:
				solrDoc = arclight.convert(record)
				arclight.post(solrDoc)
				print (f"Indexed {record.id}")
		elif args.id:
			for collection_id in args.id:
				record = aspace.read(collection_id)
				solrDoc = arclight.convert(record)
				arclight.post(solrDoc)
				print (f"Indexed {collection_id}")
		elif args.uri:
			for collection_uri in args.uri:
				record = aspace.read_uri(collection_uri)
				solrDoc = arclight.convert(record)
				arclight.post(solrDoc)
				print (f"Indexed {collection_uri}")

		lastExportTime = time.time()
		endTimeHuman = datetime.utcfromtimestamp(lastExportTime).strftime('%Y-%m-%d %H:%M:%S')
		config.last_query = str(lastExportTime).split(".")[0]
		with open(Path.home() / ".description_indexer.yml", "w") as f:
			yaml.dump(config.__dict__, f)
		print (f"Stored last run time as: {endTimeHuman}")
		