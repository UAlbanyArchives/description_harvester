import pysolr

solr = pysolr.Solr('http://192.168.1.164:8983/solr/test1', always_commit=True)

solr.ping()

solr.delete(id="ger032")
