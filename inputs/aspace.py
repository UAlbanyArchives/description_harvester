import sys
import json
#pip install iso-639
from iso639 import languages
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

    def read(self, id):

        # for URI
        if isinstance(id, int):
            resource_resp = self.client.get(f'repositories/{str(self.repo)}/resources/{id}')
        # for single id_0
        elif isinstance(id, list):
            resources = self.client.get(f'repositories/{str(self.repo)}/find_by_id/resources?identifier[]={id}')
            resource_resp = self.client.get(resources.json()['resources'][0]['ref'])
        # for multiple id_0, id_1, etc.
        else:
            resources = self.client.get(f'repositories/{str(self.repo)}/find_by_id/resources?identifier[]=["{id}"]')
            resource_resp = self.client.get(resources.json()['resources'][0]['ref'])
        resource = resource_resp.json()

        if resource["publish"] != True:
            print ("unpublished record")
        else:

            eadid = resource["ead_id"]
            inherited_data = {}
            inherited_data["collection"] = []
            recursive_level = 0
            inherited_data["parents"] = []
            inherited_data["parent_unittitles"] = []
            inherited_data["parent_access_restrict"] = []
            inherited_data["parent_access_terms"] = []

            tree = self.client.get(resource['tree']['ref']).json()

            record = self.makeSolrDocument(resource, eadid, tree, recursive_level, inherited_data)

            
            
            
            """
            for note in resource['notes']:
                if note['publish'] == True and note['type'] == "accessrestrict":
                    inherited_data["parent_access_restrict"] = []
                    for subnote in note['subnotes']:
                        inherited_data["parent_access_restrict"].append(subnote['content'])
            for note in resource['notes']:
                if note['publish'] == True and note['type'] == "userestrict":
                    inherited_data["parent_access_terms"] = []
                    for subnote in note['subnotes']:
                        inherited_data["parent_access_terms"].append(subnote['content'])

            inherited_data["parent_access_restrict_ssm"] = []
            inherited_data["parent_access_terms_ssm"] = []
            """

            return record
    
    def makeSolrDocument(self, resource, eadid, tree, recursive_level, inherited_data):
        
        indent = recursive_level*"\t"
        print (f"{indent}Indexing {resource['title']}...")

        recursive_level += 1
        
        if resource["level"].lower() == "collection":
            record = Collection()
        else:
            record = Component()
        
        record.title_ssm = [resource["title"]]
        record.ead_ssi = [eadid]
        record.repository_ssm = [self.repo_name] #this is wrong locally
        record.repository_sim = [self.repo_name]

        record.level_ssm = [resource["level"]]
        record.level_sim = [resource["level"]]

        dates = []
        normalized_dates = []
        date_range = []
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
            date_range.append(int(date['begin'].split("-")[0]))
            if "end" in date.keys():
                date_range.append(int(date['end'].split("-")[0]))
            normalized_dates.append(normalized_date)
        record.date_range_sim = date_range
        record.unitdate_ssm = dates
        record.normalized_date_ssm = [", ".join(normalized_dates)]

        record.normalized_title_ssm = [f"{record.title_ssm[0]}, {record.normalized_date_ssm[0]}"]
        
        if resource["level"].lower() == "collection":
            record.id = resource["ead_id"]
            record.unitid_ssm = [resource["ead_id"]]
            record.collection_ssm = record.normalized_title_ssm
            record.collection_sim = record.normalized_title_ssm
            record.collection_ssi = record.normalized_title_ssm
            inherited_data["collection"] = record.collection_ssm
            inherited_data["parents"] = [eadid]
            inherited_data["parent_unittitles"] = record.normalized_title_ssm
        else:
            #record.id = f"{eadid}aspace_{resource['ref_id']}"
            record.id = f"aspace_{resource['ref_id']}"
            record.ref_ssm = [f"aspace_{resource['ref_id']}"]

            #inherited_data["parents"]
            parents = inherited_data["parents"].copy()
            parent_titles = inherited_data["parent_unittitles"].copy()
            print (parent_titles)
                        
            if len(inherited_data["parents"]) > 0:
                #record.parent_ssim = [inherited_data["parents"][-1]]
                #record.parent_ssm = [inherited_data["parents"][-1]]
                record.parent_ssi = [parents[-1]]
            
            record.parent_ssim = parents
            record.parent_ssm = parents
            #record.parent_ssi = parents

            record.parent_unittitles_ssm = parent_titles
            record.component_level_isim = [recursive_level]
            record.child_component_count_isim = [inherited_data["child_component_count"]]
            record.collection_ssm = inherited_data["collection"]
            record.collection_sim = inherited_data["collection"]
            record.collection_ssi = inherited_data["collection"]
            record.parent_access_restrict_ssm = inherited_data["parent_access_restrict"]
            record.parent_access_terms_ssm = inherited_data["parent_access_terms"]
            #"unitid_ssm" order?

            inherited_data["parents"].append(record.id)
            inherited_data["parent_unittitles"].append(record.normalized_title_ssm[0])

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

        creators = []
        names = []
        for agent_ref in resource['linked_agents']:
            agent = self.client.get(agent_ref['ref']).json()
            if agent_ref['role'] == "creator":
                creators.append(agent['title'])
            else:
                names.append(agent['title'])
        record.creator_ssm = creators
        record.creator_ssim = creators
        record.creators_ssim = creators
        record.names_coll_ssim = names
        record.names_ssim = names

        subjects = []
        places = []
        for subject_ref in resource['subjects']:
            subject = self.client.get(subject_ref['ref']).json()
            # ASpace allows multiple terms per subject, and each can be geo, topical, etc. so I'm just using the first one.
            if subject['terms'][0]['term_type'] == "geographic":
                places.append(subject['title'])
            else:
                subjects.append(subject['title'])
        # Seems imprecise, but this is how what the exiting indexer does.
        record.access_subjects_ssm = subjects
        record.access_subjects_ssim = subjects
        record.geogname_ssm = places
        record.geogname_sim = places
        record.places_sim = places
        record.places_ssm = places
        record.places_ssim = places

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
        """

        

        for child in tree['children']:
            component = self.client.get(child['record_uri']).json()            
            inherited_data["child_component_count"] = len(child['children'])
            #if recursive_level < 2:
            subrecord = self.makeSolrDocument(component, eadid, child, recursive_level, inherited_data)
            record._childDocuments_.append(subrecord)

        return record
