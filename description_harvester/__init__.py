import time
import yaml
import pysolr
import argparse
from pathlib import Path
from datetime import datetime
from .version import __version__
from .configurator import Config
from .utils import write2disk, save_to_cache, load_from_cache
from description_harvester.outputs.arclight import Arclight
from description_harvester.inputs.aspace import ArchivesSpace

config = Config()

def parse_args(args=None):
    parser = argparse.ArgumentParser(description='Description_harvester manages archival description.')
    parser.add_argument('--version', action='version', version=f'description_harvester {__version__}')
    parser.add_argument('-v', '--verbose', action="store_true")
    parser.add_argument('--id', nargs="+")
    parser.add_argument('--uri', nargs="+")
    parser.add_argument('--delete', nargs="+")
    parser.add_argument('--updated', action="store_true")
    parser.add_argument('--new', action="store_true")
    parser.add_argument('--hour', action="store_true")
    parser.add_argument('--today', action="store_true")
    parser.add_argument('--solr_url', nargs=1)
    parser.add_argument('--core', nargs=1)
    parser.add_argument('--repo')
    parser.add_argument('--repo_id', type=int)
    #parser.add_argument('--ead', default=False, action="store_true", help='Optionally write to a EAD file(s).')
    
    return parser.parse_args(args) if args else parser.parse_args()

def post_record(arclight, record, verbose=False):
    solr_doc = arclight.convert(record)
    arclight.post(solr_doc)
    print(f"\tIndexed {record.id}")

def get_time_since(args):
    if args.updated:
        return config.last_query
    if args.hour:
        return str(int(time.time()) - 3600)
    if args.today:
        return str(int(time.time()) - 86400)
    return None

def index_record(arclight, aspace, collection_id, use_uri=False, verbose=False):
    loader = aspace.read_uri if use_uri else aspace.read
    record = load_from_cache(collection_id, config.cache_expiration)
    if not record:
        record = loader(collection_id)
        if record:
            save_to_cache(collection_id, record)
    if record:
        post_record(arclight, record, verbose)

def handle_deletions(solr_url, solr_core, collection_ids):
    solr = pysolr.Solr(f"{solr_url}/{solr_core}", always_commit=True)
    solr.ping()
    for collection_id in collection_ids:
        solr.delete(id=collection_id.replace(".", "-"))
        print(f"\tDeleted {collection_id}")

def harvest(args=None):
    args = parse_args(args)
    start_time = time.time()
    print(f"\n------------------------------\nRan at: {datetime.fromtimestamp(start_time)}")

    if not (args.id or args.new or args.updated or args.uri or args.hour or args.today or args.delete):
        print("No action requested, need a collection ID or --updated or --new")
        return

    solr_url = args.solr_url[0] if args.solr_url else config.solr_url
    solr_core = args.core[0] if args.core else config.solr_core

    if args.delete:
        handle_deletions(solr_url, solr_core, args.delete)
        return

    repository_name = Config.read_repositories(args.repo) if args.repo else None
    repo_id = str(args.repo_id) if args.repo_id else '2'
    aspace = ArchivesSpace(repository_id=repo_id, verbose=args.verbose)
    arclight = Arclight(f"{solr_url}/{solr_core}", repository_name)

    time_since = get_time_since(args)
    if time_since is not None:
        for uri in aspace.read_since(time_since):
            print (uri)
            index_record(arclight, aspace, uri, use_uri=True, verbose=args.verbose)

    if args.new:
        solr = pysolr.Solr(f"{solr_url}/{solr_core}", always_commit=True)
        solr.ping()
        for cid in aspace.all_resource_ids():
            results = solr.search(f"id:{cid.replace('.', '-')}", rows=1, **{"fl": "id"})
            if results.hits == 0:
                index_record(arclight, aspace, cid, verbose=args.verbose)
            else:
                print(f"\tSkipping {cid} (already exists)")

    if args.id:
        for cid in args.id:
            index_record(arclight, aspace, cid, verbose=args.verbose)

    if args.uri:
        for uri in args.uri:
            index_record(arclight, aspace, uri, use_uri=True, verbose=args.verbose)

    end_time = time.time()
    config.last_query = str(int(end_time))
    with open(Path.home() / ".description_harvester.yml", "w") as f:
        yaml.dump(config.__dict__, f)

    print(f"Stored last run time as: {datetime.utcfromtimestamp(end_time)}")
    print(f"Execution time: {end_time - start_time:.2f} seconds")

	