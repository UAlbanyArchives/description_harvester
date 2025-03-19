# description_harvester
A tool for working with archival description for public access. description_harvester reads archival description into a [minimalist data model for public-facing archival description](https://github.com/UAlbanyArchives/description_harvester/blob/main/description_harvester/models/description.py) and then converts it to the [Arclight data model](https://github.com/UAlbanyArchives/description_harvester/blob/main/description_harvester/models/arclight.py) and POSTs it into an Arclight Solr index using [PySolr](https://github.com/django-haystack/pysolr).

description_harvester is designed to be extensible and harvest archival description from a number of [sources](https://github.com/UAlbanyArchives/description_harvester/tree/main/description_harvester/inputs). Currently the only available source harvests data from the [ArchivesSpace](https://github.com/archivesspace/archivesspace) [API](https://archivesspace.github.io/archivesspace/api/#introduction) using [ArchivesSnake](https://github.com/archivesspace-labs/ArchivesSnake). It is possible in the future to add modules for EAD2002 and other sources. Its also possible to add additional [output modules](https://github.com/UAlbanyArchives/description_harvester/tree/main/description_harvester/outputs) to serialize description to EAD or other formats in addition to or in replace of sending description to an Arclight Solr instance. This potential opens up new possibilities of managing description using low-barrier formats and tools.

The [main branch](https://github.com/UAlbanyArchives/description_harvester) is designed to be a drop-in replacement for the Arclight Traject indexer, while the [dao-indexing branch](https://github.com/UAlbanyArchives/description_harvester/tree/dao-indexing) tries to fully index digital objects from digital repositories and other sources, including item-level metadata fields, embedded text, OCR text, and transcriptions. 

This is still a bit drafty, as its only tested on ASpace v2.8.0 and needs better error handling. Validation is also very minimal, but there is potential to add detailed validation with `jsonschema `.

### Installation

```python
pip install description_harvester
```

First, you need to configure ArchivesSnake by creating a `~/.archivessnake.yml`file with your API credentials as detailed by the [ArchivesSnake configuration docs](https://github.com/archivesspace-labs/ArchivesSnake#configuration).

Next, you also need a `~/.description_harvester.yml` file that lists your Solr URL and the core you want to index to. These can also be overridden with args.

```yml
solr_url: http://127.0.0.1:8983/solr
solr_core: blacklight-core
last_query: 0
```

### Indexing from ArchivesSpace API to Arclight

Once description_harvester is set up, you can index from the ASpace API to Arclight using the `to-arclight` command.

#### Index by id_0

You can provide one or more IDs to index using a resource's id_0` field

`harvest --id ua807`

`harvest --id mss123 apap106`

#### Index by URI

You can also use integers from ASpace URIs for resource, such as 263 for `https://my.aspace.edu/resources/263`

`harvest --uri 435`

`harvest --uri 1 755`

#### Indexing by modified time

Index collections modified in the past hour: `harvest --hour`

Index collections modified in the past day: `harvest --today`

Index collections modified since las run: `harvest --new`

#### Deleting collections

You can delete one or more collections using the `--delete` argument in addition to`--id`. This uses the Solr document ID, such as `apap106` for `https://my.arclight.edu/catalog/apap106`.

`harvest --id apap101 apap301 --delete`

#### Use as a library

You can also use description harvester in a script

```
from description_harvester import harvest

harvest(["--id", "myid001"])
```
