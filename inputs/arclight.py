import requests

#recordID = "ua902-010aspace_04e18499fd09efa113efc0baf5481328"
recordID = "ua902-010"
#recordID = "ua621"
recordURL = "https://archives.albany.edu/description/catalog/" + recordID + "?format=json"

translation = {"title_ssm" : "title_ssm",
    "extent_ssm": "extent_ssm",
    "language_ssm": "language_ssm",
    "abstract_ssm": "abstract_ssm",
    "collection_ssm": "collection_ssm",
    "accessrestrict_ssm": "accessrestrict_ssm",
    "scopecontent_ssm": "scopecontent_ssm",
    "repository_ssm": "repository_ssm",
    "ead_ssi": "ead_ssi",
    "level_ssm": "level_ssm",
    #"component_level_isim": "componentLevel",
    "has_online_content_ssim": "has_online_content_ssim",
    "normalized_title_ssm": "normalized_title_ssm",
    "normalized_date_ssm": "normalized_date_ssm"}

r = requests.get(recordURL)

aspaceRecord = r.json()['data']