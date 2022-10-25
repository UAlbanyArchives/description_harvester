# description_indexer
A tool for working with archival description for public access. description_indexer reads archival description into a minimalist data model for public-facing archival description.

description_indexer can index directly from the [ArchivesSpace](https://github.com/archivesspace/archivesspace) [API](https://archivesspace.github.io/archivesspace/api/#introduction) to an Arclight Solr instance using [ArchivesSnake](https://github.com/archivesspace-labs/ArchivesSnake) and [PySolr](https://github.com/django-haystack/pysolr).

This is still a bit drafty, as its only tested on ASpace v2.8.0 and needs better error handling.

### Installation

```python
pip install description_indexer
```

First, you need to configure ArchivesSnake by creating a `~/.archivessnake.yml`file with your API credentials as detailed by the [ArchivesSnake configuration docs](https://github.com/archivesspace-labs/ArchivesSnake#configuration).

Next, you also need a `~/.description_indexer.yml` file that lists your Solr URL and the core you want to index to. These can also be overridden with args.

```yml
solr_url: http://127.0.0.1:8983/solr
solr_core: blacklight-core
last_query: 0
```

### Indexing from ArchivesSpace API to Arclight

Once description_indexer is set up, you can index from the ASpace API to Arclight using the `to-arclight` command.

#### Index by id_0

You can provide one or more IDs to index using a resource's id_0` field

`to-arclight --id ua807`

`to-arclight --id mss123 apap106`

#### Index by URI

You can also use integers from ASpace URIs for resource, such as 263 for `https://my.aspace.edu/resources/263`

`to-arclight --uri 435`

`to-arclight --uri 1 755`

#### Indexing by modified time

Index collections modified in the past hour: `to-arclight --hour`

Index collections modified in the past day: `to-arclight --today`

Index collections modified since las run: `to-arclight --new`

#### Deleting collections

You can delete one or more collections using the `--delete` argument in addition to`--id`. This uses the Solr document ID, such as `apap106` for `https://my.arclight.edu/catalog/apap106`.

`to-arclight --id apap101 apap301 --delete`

