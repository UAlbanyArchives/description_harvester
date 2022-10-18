import sys
#pip install iso-639
from iso639 import languages
#from asnake.aspace import ASpace
from asnake.client import ASnakeClient
import asnake.logging as logging
from models import Collection, Component

logging.setup_logging(stream=sys.stdout, level='INFO')

class ArchivesSpace():

    def __init__(self, repository):
        #aspace = ASpace()
        self.client = ASnakeClient()
        self.client.authorize()

        self.repo = repository

        self.repo_name = self.client.get('repositories/' + str(self.repo)).json()['name']
        print (self.repo_name)

    #def singlepart(self, resource, note_type):

    
    def read(self, id):

        #collection = self.repo.resources(id)
        #print (collection.title)
        if isinstance(id, int):
            resource_resp = self.client.get(f'repositories/{str(self.repo)}/resources/{id}')
        elif isinstance(id, list):
            resources = self.client.get(f'repositories/{str(self.repo)}/find_by_id/resources?identifier[]={id}')
            resource_resp = self.client.get(resources.json()['resources'][0]['ref'])
        else:
            resources = self.client.get(f'repositories/{str(self.repo)}/find_by_id/resources?identifier[]=["{id}"]')
            resource_resp = self.client.get(resources.json()['resources'][0]['ref'])
        resource = resource_resp.json()

        if resource["publish"] != True:
            print ("unpublished record")
        else:

            record = Collection()
            record.id = resource["ead_id"]
            record.unitid_ssm = [resource["ead_id"]]
            record.title_ssm = [resource["title"]]
            record.ead_ssi = [resource["ead_id"]]

            record.repository_ssm = [self.repo_name]

            record.level_ssm = ["collection"]

            dates = []
            normalized_dates = []
            for date in resource["dates"]:
                if "bulk" in date['date_type'].lower():
                    normalized_date = "bulk "
                else:
                    normalized_date = ""
                if "expression" in date.keys():
                    dates.append(date['expression'])
                    normalized_date += date['expression']
                elif "end" in date.keys():
                    dates.append(f"{date['begin']}-{date['end']}")
                    normalized_date = f"{normalized_date}{date['begin']}-{date['end']}"
                else:
                    dates.append(date['begin'])
                    normalized_date += date['begin']
                normalized_dates.append(normalized_date)
            record.unitdate_ssm = dates
            record.normalized_date_ssm = [", ".join(normalized_dates)]

            record.normalized_title_ssm = [f"{record.title_ssm[0]}, {record.normalized_date_ssm[0]}"]
            collection_ssm = record.normalized_title_ssm

            extents = []
            for extent in resource["extents"]:
                extents.append(f"{extent['number']} {extent['extent_type']}")
            record.extent_ssm = extents

            languages_list = []
            for language in resource["lang_materials"]:
                lang_code = language['language_and_script']['language']
                lang = languages.get(bibliographic=lang_code.lower())
                languages_list.append(lang.name)
            record.language_ssm = [", ".join(languages_list)]

            note_translations = {
                "abstract": "abstract_ssm",
                "physloc": "physloc_ssm",
                "processinfo": "processinfo_ssm",
                "bioghist": "bioghist_ssm",
                "scopecontent": "scopecontent_ssm",
                "arrangement": "arrangement_ssm",
                "acqinfo": "acqinfo_ssim",
                "accessrestrict": "accessrestrict_ssm",
                "userestrict": "userestrict_ssm",
                "prefercite": "prefercite_ssm",
                "odd": "odd_ssm",
                "originalsloc": "originalsloc_ssm",
                "altformavail": "altformavail_ssm",
                "separatedmaterial": "separatedmaterial_ssm",
                "relatedmaterial": "relatedmaterial_ssm",
                "custodhist": "custodhist_ssm",
                "phystech": "phystech_ssm",
                "otherfindaid": "otherfindaid_ssm",
                "accruals": "accruals_ssm",
                "appraisal": "appraisal_ssm",
                "fileplan": "fileplan_ssm",
                "materialspec": "materialspec_ssm",
                "bibliography": "bibliography_ssm",
                "dimensions": "dimensions_ssm",
                "note ": "note_ssm"
            }

            for note in resource["notes"]:
                if note['publish'] == True:
                    if note["jsonmodel_type"] == "note_singlepart":
                        setattr(record, note_translations[note["type"]], note["content"])
                    else:
                        note_text = []
                        for subnote in note["subnotes"]:
                            if subnote['publish'] == True:
                                if "content" in subnote.keys():
                                    note_text.append(subnote["content"])
                                elif subnote['jsonmodel_type'] == "note_chronology":
                                    events = []
                                    for event in subnote["items"]:
                                        events.append(f"{event['event_date']}: {event['events']}")
                                    note_text.append("\n".join(events))
                                elif subnote['jsonmodel_type'] == "note_orderedlist":
                                    note_text.append("\n".join(subnote['items']))
                                else:
                                    #print (note)
                                    raise ValueError(subnote)
                        setattr(record, note_translations[note["type"]], note_text)
                

            """

            
            has_online_content_ssm = fields.ListField(str)
            names_coll_ssim = fields.ListField(str)

             linked_agents
             subjects

            """
            return record
