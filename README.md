# description_harvester
A tool for working with archival description for public access. description_harvester reads archival description into a [minimalist data model for public-facing archival description](https://github.com/UAlbanyArchives/description_harvester/blob/main/description_harvester/models/description.py) and then converts it to the [ArcLight data model](https://github.com/UAlbanyArchives/description_harvester/blob/main/description_harvester/models/ArcLight.py) and POSTs it into an ArcLight Solr index using [PySolr](https://github.com/django-haystack/pysolr).

description_harvester is designed to be extensible and harvest archival description from a number of [sources](https://github.com/UAlbanyArchives/description_harvester/tree/main/description_harvester/inputs). Currently the only available sources harvests data from the [ArchivesSpace](https://github.com/archivesspace/archivesspace) [API](https://archivesspace.github.io/archivesspace/api/#introduction) using [ArchivesSnake](https://github.com/archivesspace-labs/ArchivesSnake) or [EAD 2002](https://www.loc.gov/ead/) XML files. Its also possible to add additional [output modules](https://github.com/UAlbanyArchives/description_harvester/tree/main/description_harvester/outputs) to serialize description to EAD or other formats in addition to or in replace of sending description to an ArcLight Solr instance. This potential opens up new possibilities of managing description using low-barrier formats and tools.

description_harvester is designed to be a drop-in replacement for the ArcLight Traject indexer. It also includes a [plugin](https://github.com/UAlbanyArchives/description_harvester/blob/main/description_harvester/plugins/manifests.py) that attempts to recognized IIIF manifests included as file versions and uses manifests to fully index digital objects from digital repositories and other sources, including item-level metadata fields, embedded text, OCR text, and transcriptions. 

Tested on ASpace up to v3.5.1 but needs some better error handling. Validation is also very minimal, but there is potential to add detailed validation with `jsonschema `.

## Installation

```python
pip install description_harvester
```

First, you need to configure ArchivesSnake by creating a `~/.archivessnake.yml`file with your API credentials as detailed by the [ArchivesSnake configuration docs](https://github.com/archivesspace-labs/ArchivesSnake#configuration).

Next, you also need a `~/.description_harvester/config.yml` file that lists your Solr URL and the core you want to index to. These can also be overridden with args. description_harvester reads your `config.yml` as utf-8, so if you're creating this file in a Windows environment you should ensure its utf-8.

```yml
solr_url: http://127.0.0.1:8983/solr
solr_core: blacklight-core
last_query: 0
cache_expiration: 3600
component_id_separator: "_"
online_content_label: "Online access"
```
The `component_id_separator` allows for a customizable separator between the collection and component IDs in ArcLight URLs. This can be set to `component_id_separator: ""` for pre-ArcLight v1.1.0 defaults which had no separator. This will default to `_` if this setting isn't set in `config.yml` as ArcLight now does.

The `online_content_label` setting allows you to customize the label displayed for items with online content in ArcLight. The default is "Online access".

### Adding custom digital object metadata

You can also add custom digital object metadata fields by adding them to your `config.yml` under the Solr suffix you would like them to be indexed as. These fields must match [metadata fields in your IIIF manifests](https://iiif.io/api/cookbook/recipe/0029-metadata-anywhere/).

```yml
metadata:
- ssi:
  - date_uploaded
- ssm:
  - date_digitized
  - extent
- ssim:
  - legacy_id
  - resource_type
  - coverage
  - preservation_package
  - creator
  - contributor
  - preservation_format
  - source
- tesm:
  - processing_activity
- tesim:
  - description
```

### Repositories

By default, when reading from ArchivesSpace, description harvester will use the repository name stored there.

To enable the --repo argument, place a copy of your ArcLight repositories.yml file as `~/.description_harvester/repositories.yml`. You can then use `harvest --id mss001 --repo slug` to index using the slug from repositories.yml. This will overrite the ArchivesSpace repository name.

There is also the option do customize this with a [plugin](https://github.com/UAlbanyArchives/description_harvester_plugins/blob/main/repo_plugin.py).

**Encoding note:** While ArcLight does not explicitly read `repositories.yml` as utf-8, its Rails stack means that you're likely reading it in a utf-8 (non-Windows) environment. Since description_harvester enables you to index from a Windows machine, it expects your `~/.description_harvester/repositories.yml` file to be utf-8.

## Indexing from ArchivesSpace API to ArcLight

Once description_harvester is set up, you can index from the ASpace API to ArcLight using the `to-ArcLight` command.

### Index by id_0

You can provide one or more IDs to index using a resource's id_0` field

`harvest --id ua807`

`harvest --id mss123 apap106`

### Index by URI

You can also use integers from ASpace URIs for resource, such as 263 for `https://my.aspace.edu/resources/263`

`harvest --uri 435`

`harvest --uri 1 755`

### Indexing by modified time

Index collections modified in the past hour: `harvest --hour`

Index collections modified in the past day: `harvest --today`

Index collections modified since las run: `harvest --updated`

Index collections not already in the index: `harvest --new`

## Indexing from EAD 2002

```
harvest --ead path/to/ead.xml
```

You can also give it a directory and it will harvest all *.xml

```
harvest --ead path/to/ead_files
```

## Verbose output

```
harvest --id ger071 -v
```

## Caching

description_harvester will cache collections from the ArchivesSpace API, storing them by default to `~/.description_harvester/cache` after they are converted to the description model. Cache time is set in seconds as `cache_expiration` in `~/.description_harvester/config.yml`. Thus, `cache_expiration: 3600` will use the cached data instead of the ArchivesSpace API for data less than 1 hour old.

You can override the cache path in config or turn caching off gobally with `cache_dir: false`.
```yml
cache_dir: "~/path/to/my_cache"
cache_dir: "C:/Users/username/my_cache"
cache_dir: false
```

## Deleting collections

You can delete one or more collections using the `--delete` argument. This uses the Solr document ID, such as `apap106` for `https://my.ArcLight.edu/catalog/apap106`.

`harvest --delete apap101 apap301`

## Plugins

Plugins let you add institution-specific customization without modifying the core package. Common use cases might be:
- Customizing repository names based on collection identifiers
- Enriching digital objects with data from local systems (e.g., IIIF manifests, preservation systems)

[UAlbany's local plugins](https://github.com/UAlbanyArchives/description_harvester_plugins) may be a helpful example.

### Creating a Plugin

1. **Copy the template**: Copy [default.py](https://github.com/UAlbanyArchives/description_harvester/blob/main/description_harvester/plugins/default.py) to `~/.description_harvester/` (or use `DESCRIPTION_HARVESTER_PLUGIN_DIR` environment variable)

2. **Rename the class**: Change `DefaultPlugin` to something descriptive (e.g., `MyInstitutionPlugin`)

3. **Update plugin_name**: Set a unique identifier:
   ```python
   class MyInstitutionPlugin(Plugin):
       plugin_name = "my_institution"
   ```

4. **Implement methods**: Override one or both customization hooks:

   - **`custom_repository(resource)`**: Customize repository names
     - Input: [ArchivesSpace resource API object](https://archivesspace.github.io/archivesspace/api/#get-a-resource)
     - Output: Repository name string or `None` for default behavior
   
   - **`update_dao(dao)`**: Enrich digital objects
     - Input: [DigitalObject](https://github.com/UAlbanyArchives/description_harvester/blob/main/description_harvester/models/description.py) with identifier, label, metadata, etc.
     - Output: Modified DigitalObject with additional metadata

### Plugin Discovery

Plugins are automatically loaded from (in order):
1. Built-in plugins in the package (e.g., `default.py`)
2. `~/.description_harvester/` directory
3. Custom directory set via `DESCRIPTION_HARVESTER_PLUGIN_DIR` environment variable

### Example Plugin

```python
from description_harvester.plugins import Plugin
from description_harvester.iiif_utils import enrich_dao_from_manifest

class MyInstitutionPlugin(Plugin):
    plugin_name = "my_institution"
    
    def custom_repository(self, resource):
        # Use custom names for special collections
        if resource['id_0'].startswith('sc'):
            return "Special Collections & Archives"
        return None  # Use default for others
    
    def update_dao(self, dao):
        # Enrich digital objects with IIIF manifest data
        if 'manifest.json' in dao.identifier:
            enrich_dao_from_manifest(dao, manifest_url=dao.identifier)
            # Add custom logic
            dao.metadata['institution_id'] = 'my_institution'
        return dao
```

### IIIF Utilities

For plugins working with IIIF manifests, `description_harvester.iiif_utils` provides helper functions:

```python
from description_harvester.iiif_utils import (
    fetch_manifest,              # Fetch and parse manifest from URL
    extract_text_from_manifest,  # Extract OCR/transcription text
    get_thumbnail_url,           # Get thumbnail image URL
    get_rights_statement,        # Get rights/license info
    extract_metadata_fields,     # Get all metadata as dict
    enrich_dao_from_manifest,    # All-in-one enrichment
)

def update_dao(self, dao):
    if 'manifest.json' in dao.identifier:
        # Option 1: Use convenience function
        enrich_dao_from_manifest(dao, manifest_url=dao.identifier)
        
        # Option 2: Fine-grained control
        manifest = fetch_manifest(dao.identifier)
        if manifest:
            dao.text_content = extract_text_from_manifest(manifest)
            dao.thumbnail_href = get_thumbnail_url(manifest)
            dao.rights_statement = get_rights_statement(manifest)
            # Optionally add metadata fields from manifests
            dao.metadata.update(extract_metadata_fields(manifest))

            # Set metadata fields with whatever local logic
            dao.metadata['custom_field'] = 'custom_value'
    
    return dao
```

See the [iiif_utils module documentation](https://github.com/UAlbanyArchives/description_harvester/blob/main/description_harvester/iiif_utils.py) for all available functions.

## Use as a library

You can also use description harvester in a script

```
from description_harvester import harvest

harvest(["--id", "myid001"])
```


