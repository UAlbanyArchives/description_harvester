import sys
from iso639 import languages
from asnake.client import ASnakeClient
import asnake.logging as logging
from description_indexer.models.description import Component, Date, Extent, Agent, Container, DigitalObject
from description_indexer.utils import iso2DACS

logging.setup_logging(stream=sys.stdout, level='INFO')

class ArchivesSpace():
    """This class connects to an ArchivesSpace repository"""

    def __init__(self, repository=2):
        """
        Connects to an ASpace repo using ArchivesSnake.
        Uses URL and login info from ~/.archivessnake.yml
        
        Parameters:
            repository (int): The ASpace Repository ID. Defaults to 2.
        """

        self.client = ASnakeClient()
        self.client.authorize()

        self.repo = repository

        self.repo_name = self.client.get('repositories/' + str(self.repo)).json()['name']

    def read(self, id):
        """
        Reads a resource and its associated archival objects
        Uses URL and login info from ~/.archivessnake.yml
        
        Parameters (one of):
            id (list): a set of a resource's id_ fields as strings, such as ["id_0", "id_1", "id_2", "id_3"]
            id (str): a resource's id_0 as a string

        Returns:
            record (Component): a component object containing all description
        """

        # for single id_0
        if isinstance(id, list):
            resources = self.client.get(f'repositories/{str(self.repo)}/find_by_id/resources?identifier[]={id}')
            resource = self.client.get(resources.json()['resources'][0]['ref']).json()
        # for multiple id_0, id_1, etc.
        else:
            resources = self.client.get(f'repositories/{str(self.repo)}/find_by_id/resources?identifier[]=["{id}"]')
            resource = self.client.get(resources.json()['resources'][0]['ref']).json()

        if resource["publish"] != True:
            print (f"Skipping unpublished resource {resource['id_0']}")
        else:
            eadid = resource["ead_id"]
            tree = self.client.get(resource['tree']['ref']).json()
            record = self.readToModel(resource, eadid, tree)

            return record

    def read_uri(self, uri):
        """
        Reads a resource and its associated archival objects
        Uses URL and login info from ~/.archivessnake.yml
        
        Parameters:
            uri (int): a resource's ID from its ASpace URI. Such as 439 for /resources/439

        Returns:
            record (Component): a component object containing all description
        """

        resource = self.client.get(f'repositories/{str(self.repo)}/resources/{str(uri)}').json()
        
        if resource["publish"] != True:
            print ("Unpublished record")
        else:
            eadid = resource["ead_id"]
            
            tree = self.client.get(resource['tree']['ref']).json()
            record = self.readToModel(resource, eadid, tree)
            
            return record
    
    def read_since(self, last_run_time):

        records = []
        modifiedList = self.client.get(f'repositories/{str(self.repo)}/resources?all_ids=true&modified_since={str(last_run_time)}').json()
        if len(modifiedList) < 1:
            print ("No collections modified since last run.")
        else:
            print (modifiedList)
            for collection_uri in modifiedList:
                record = self.read_uri(int(collection_uri))
                records.append(record)

        return records

    def readToModel(self, apiObject, eadid, tree, collection_name="", recursive_level=0):
        """
        A recursive function that initally takes a resource from the ASpace API and reads it to a model.
        Then calls itself on any child archival_object records
        
        Parameters:
            apiObject (dict): a resource or archival object from the ASpace API as a JSON dict
            eadid (str): a collection's EADID as a string
            tree (dict): an ASpace API Tree object for a collection
            collection_name (str): The name of the collection as a string
            recursive_level (int): The level of recursion. Start at 0

        Returns:
            record (Component): a hierarchical component object containing all public-facing description for a collection
        """

        # Print the name of the object being read, correctly indented        
        indent = recursive_level*"\t"
        print (f"{indent}Reading {apiObject['title']}...")
        
        record = Component()
        
        record.title = apiObject["title"]
        record.repository = self.repo_name
        record.level = apiObject["level"]

        for date in apiObject["dates"]:
            dateObj = Date()
            dateObj.begin = date['begin']
            if date['date_type'].lower() == "bulk":
                dateObj.date_type = "bulk"
            elif date['date_type'].lower() == "inclusive":
                dateObj.date_type = "inclusive"
            if "end" in date.keys():
                dateObj.end = date['end']

            if "expression" in date.keys():
                dateObj.expression = date['expression']
            elif "end" in date.keys():
                dateObj.expression = iso2DACS(date['begin']) + " - " + iso2DACS(date['end'])
            else:
                dateObj.expression = iso2DACS(date['begin'])
            record.dates.append(dateObj)
        
        if apiObject["level"].lower() == "collection":
            record.id = apiObject["ead_id"]
            record.collection_id = apiObject["ead_id"]
            record.collection_name = apiObject["title"]
            collection_name = record.collection_name
        else:
            # Prepending aspace_ to be consistent with the ASpace EAD exporter
            record.id = "aspace_" + apiObject["ref_id"]
            record.collection_id = eadid
            record.collection_name = collection_name

        # read extents
        for extent in apiObject["extents"]:
            extentObj = Extent()
            extentObj.number = extent['number']
            extentObj.unit = extent['extent_type']
            record.extents.append(extentObj)

        # languages
        for language in apiObject["lang_materials"]:
            if "language_and_script" in language.keys():
                lang_code = language['language_and_script']['language']
                lang = languages.get(bibliographic=lang_code.lower())
                record.languages.append(lang.name)
            for lang_note in language['notes']:
                record.languages.extend(lang_note['content'])

        # Agents and subjects could be a lot more detailed with their own objects
        # but this is a minimal implementation as I don't have good agent data to work with ¯\_(ツ)_/¯
        # Agents
        for agent_ref in apiObject['linked_agents']:
            agent = self.client.get(agent_ref['ref']).json()
            agentObj = Agent()
            agentObj.name  = agent['title']
            agentObj.agent_type = agent['agent_type'].split("agent_")[1]
            if agent_ref['role'] == "creator":
                record.creators.append(agentObj)
            else:
                record.names.append(agentObj)
        # Subjects
        for subject_ref in apiObject['subjects']:
            subject = self.client.get(subject_ref['ref']).json()
            # ASpace allows multiple terms per subject, and each can be geo, topical, etc. so I'm just using the first one.
            if subject['terms'][0]['term_type'] == "geographic":
                record.places.append(subject['title'])
            else:
                record.subjects.append(subject['title'])

        # Notes
        for note in apiObject["notes"]:
            if note['publish'] == True:
                if note["jsonmodel_type"] == "note_singlepart":
                    setattr(record, note["type"], note["content"])
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
                                raise ValueError(subnote)
                    setattr(record, note["type"], note_text)

        daos = []
        for instance in apiObject["instances"]:
            if "sub_container" in instance.keys():
                container = Container()
                top_container = self.client.get(instance['sub_container']['top_container']['ref']).json()
                if 'type' in top_container.keys():
                    container.top_container = top_container['type']
                if 'indicator' in top_container.keys():
                    container.top_container_indicator = top_container['indicator']
                if 'type_2' in instance['sub_container'].keys():
                    container.sub_container = instance['sub_container']['type_2']
                if 'indicator_2' in instance['sub_container'].keys():
                    container.sub_container_indicator = instance['sub_container']['indicator_2']
                if 'type_3' in instance['sub_container'].keys():
                    container.sub_container = instance['sub_container']['type_3']
                if 'indicator_3' in instance['sub_container'].keys():
                    container.sub_container_indicator = instance['sub_container']['indicator_3']
                record.containers.append(container)
            elif instance['instance_type'] == "digital_object":
                digital_object = self.client.get(instance['digital_object']['ref']).json()
                if digital_object['publish'] == True:
                    if "file_versions" in digital_object.keys() and len(digital_object['file_versions']) > 0:
                        dao = DigitalObject()
                        dao_title = digital_object['title']
                        # So ASpace DAOs can have multiple file versions for some reason so 
                        # I guess I'm making a new dao for each with the same label?
                        for file_version in digital_object['file_versions']:
                            if "publish" in file_version.keys() and file_version != True:
                                pass
                            else:
                                if "file_uri" in file_version.keys():
                                    dao.URI = file_version['file_uri']
                                    dao.label = dao_title
                                    record.digital_objects.append(dao)

        
        recursive_level += 1

        for child in tree['children']:
            component = self.client.get(child['record_uri']).json()            
            subrecord = self.readToModel(component, eadid, child, collection_name, recursive_level)
            record.components.append(subrecord)

        return record
