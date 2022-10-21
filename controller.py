from inputs.aspace import ArchivesSpace
from outputs.arclight import Arclight


aspace = ArchivesSpace()
record = aspace.read("ger032")

arclight = Arclight("http://192.168.1.164:8983/solr/test1")
solrDoc = arclight.convert(record)
arclight.post(solrDoc)
