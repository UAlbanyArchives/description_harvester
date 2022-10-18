import json
import pysolr
from inputs.aspace import ArchivesSpace


solr = pysolr.Solr('http://192.168.1.164:8983/solr/test1', always_commit=True)

solr.ping()

aspace = ArchivesSpace(repository=2)
#record = aspace.read(101)
record = aspace.read("ger014")
## resource URI or EADID? integer or string?s

#print (record.to_struct())
print(json.dumps(record.to_struct(), indent=4))
#solr.add([record.to_struct()])

"""
record = Collection()
record.id = aspaceRecord["id"]
record.unitID = [str(aspaceRecord["id"])]
for key in translation.keys():
    #print (key)       
    setattr(record, translation[key], aspaceRecord['attributes'][key]['attributes']['value'])

print (record.to_struct())
#record_json = json.dumps(record.to_struct())
#print(json.dumps(record.to_struct(), indent=4))

"""