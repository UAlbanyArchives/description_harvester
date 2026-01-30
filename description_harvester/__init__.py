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
from description_harvester.inputs.ead import EAD

config = Config()

def parse_args(args=None):
    parser = argparse.ArgumentParser(description='Description_harvester manages archival description.')
    parser.add_argument('--version', action='version', version=f'description_harvester {__version__}')
    parser.add_argument('-v', '--verbose', action="store_true")
    parser.add_argument('-nc', '--no-cache', action="store_true")
    parser.add_argument('--id', nargs="+")
    parser.add_argument('--uri', nargs="+")
    parser.add_argument('--delete', nargs="+")
    parser.add_argument('--updated', action="store_true")
    parser.add_argument('--new', action="store_true")
    parser.add_argument('--all', action="store_true")
    parser.add_argument('--hour', action="store_true")
    parser.add_argument('--today', action="store_true")
    parser.add_argument('--solr_url', nargs=1)
    parser.add_argument('--core', nargs=1)
    parser.add_argument('--repo', help="Override repository name in EAD/ArchivesSpace with a slug from the ArcLight repositories.yml.")
    parser.add_argument('--repo_id', type=int, help="ArchivesSpace repository ID (default: 2)")
    parser.add_argument(
        '--ead',
        metavar="PATH",
        help="Path to an EAD-XML file or a directory containing EAD-XML files."
    )

    return parser.parse_args(args) if args else parser.parse_args()

def add_record(arclight, record, repository_name=None, verbose=False):
    solr_doc = arclight.convert(record, repository_name)
    arclight.add(solr_doc)
    print(f"\tIndexed {record.id}")

def get_time_since(args):
    if args.updated:
        return config.last_query
    if args.hour:
        return str(int(time.time()) - 3600)
    if args.today:
        return str(int(time.time()) - 86400)
    return None

def index_record(args, arclight, source, identifier, repository_name=None, use_uri=False):
    # indexes a single collection/fonds/resource and manages cache
    record = None
    if not args.no_cache:
        record = load_from_cache(identifier, config.cache_dir, config.cache_expiration)

    if not record:
        record = source.fetch(identifier, use_uri=use_uri)
        if record:
            save_to_cache(identifier, record, config.cache_dir)

    if record:
        add_record(arclight, record, repository_name, args.verbose)

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

    required_actions = [
        args.id,
        args.new,
        args.all,
        args.updated,
        args.uri,
        args.ead,
        args.hour,
        args.today,
        args.delete,
    ]

    if not any(required_actions):
        print("No action requested, need a collection ID, EAD path, or --updated, --new, etc.")
        return

    solr_url = args.solr_url[0] if args.solr_url else config.solr_url
    solr_core = args.core[0] if args.core else config.solr_core

    if args.delete:
        handle_deletions(solr_url, solr_core, args.delete)
        return

    solr = pysolr.Solr(f"{solr_url}/{solr_core}", always_commit=False, timeout=600)
    solr.ping()

    # ---- Check input source ----
    source_type = "ead" if args.ead else "aspace"

    if source_type == "ead":
        source = EAD(args.ead, verbose=args.verbose)
    else:
        repo_id = str(args.repo_id) if args.repo_id else '2'
        source = ArchivesSpace(repository_id=repo_id, verbose=args.verbose)

    # Set up ArcLight
    arclight = Arclight(solr, config.metadata, config.online_content_label, config.component_id_separator)
    repository_name = Config.read_repositories(args.repo, args.verbose) if args.repo else None
    doc_count = 0

    # ---- ArchivesSpace-only features ----
    if source_type == "aspace":
        time_since = get_time_since(args)
        if time_since is not None:
            for uri in source.read_since(time_since):
                index_record(args, arclight, source, uri, repository_name, use_uri=True)
                doc_count += 1

        if args.new:
            for cid in source.all_resource_ids():
                results = solr.search(f"id:{cid.replace('.', '-')}", rows=1, fl="id")
                if results.hits == 0:
                    index_record(args, arclight, source, cid, repository_name)
                    doc_count += 1
                else:
                    print(f"\tSkipping {cid} (already exists)")

        if args.all:
            for cid in source.all_resource_ids():
                index_record(args, arclight, source, cid, repository_name)
                doc_count += 1

        if args.id:
            for cid in args.id:
                index_record(args, arclight, source, cid, repository_name)
                doc_count += 1

        if args.uri:
            for uri in args.uri:
                index_record(args, arclight, source, uri, repository_name, use_uri=True)
                doc_count += 1

    if source_type == "ead":
        for file in source.items():
            index_record(args, arclight, source, file, repository_name)
            doc_count += 1

    print (f"Committing {doc_count} collection docs to the Solr index...")
    solr.commit()

    end_time = time.time()
    config.last_query = str(int(end_time))
    with open(Path.home() / ".description_harvester.yml", "w") as f:
        yaml.dump(config.__dict__, f)

    print(f"Stored last run time as: {datetime.utcfromtimestamp(end_time)}")
    print(f"Execution time: {end_time - start_time:.2f} seconds")

    