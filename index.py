import json
import pysolr
import requests


solr = pysolr.Solr('http://192.168.1.164:8983/solr/test1', always_commit=True)

solr.ping()

#recordID = "ua902-010aspace_04e18499fd09efa113efc0baf5481328"
#recordID = "ua902-010"
recordID = "ua621"
recordURL = "https://archives.albany.edu/description/catalog/" + recordID + "?format=json"

keys = ["title_ssm",
        "extent_ssm",
        "language_ssm",
        "abstract_ssm",
        "collection_ssm",
        "accessrestrict_ssm",
        "scopecontent_ssm",
        "repository_ssm",
        #"unitid_ssm",
        #"id",
        "ead_ssi",
        "level_ssm",
        "has_online_content_ssim",
        #"names_coll_ssim",
        "normalized_title_ssm",
        "normalized_date_ssm"]

r = requests.get(recordURL)

recordJSON = r.json()['data']
record = {}
record["id"] = recordJSON["id"]
record["unitid_ssm"] = str(recordJSON["id"])
for key in keys:
	record[key] = recordJSON['attributes'][key]['attributes']['value']

#print (record['attributes'].keys())
print(json.dumps(record, indent=4))

solr.add([record])