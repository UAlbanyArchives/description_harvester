import os
import sys
from lxml import etree
from io import StringIO
from typing import List
from iso639 import languages
from asnake.client import ASnakeClient
import asnake.logging as logging
from description_harvester.models.description import Component, Date, Extent, Agent, Container, DigitalObject
from description_harvester.utils import iso2DACS
from description_harvester.dao_plugins import DaoSystem, import_dao_plugins

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

        self.repo = repository

        self.repo_name = self.client.get('repositories/' + str(self.repo)).json()['name']

        plugin_basedir = os.environ.get("DESCRIPTION_HARVESTER_PLUGIN_DIR", None)
        # Dao system plugins are loaded from:
        #   1. dao_plugins directory inside the package (built-in)
        #   2. .description_harvester/dao_plugins in user home directory
        #   3. dao_plugins subdirectories in plugin dir set in environment variable
        plugin_dirs = []
        for dirs in plugin_dirs:
            dirs.append(Path(f"~/.description_harvester/dao_plugins").expanduser())
            if plugin_basedir:
                dirs.append((Path(plugin_basedir) / dao_plugins).expanduser())
        import_dao_plugins(plugin_dirs)

        # Instantiate DAO systems
        self.dao_systems = []
        for system in self.dao_system_map.keys():
            dao_system: DaoSystem = self.dao_system_map[system]
            self.dao_systems.append(dao_system)

    @property
    def dao_system_map(self):
        return DaoSystem.registry


    def extract_xpath_text(self, text: str) -> List[str]:
        try:
            # Parse the string as HTML content (allowing lenient parsing with 'recover=True')
            parser = etree.HTMLParser(recover=True)
            tree = etree.parse(StringIO(text), parser)

            # Find all elements, excluding <html> and <body> tags
            elements = tree.xpath("//*[not(self::html or self::body)]")

            # Process elements and split text by newlines
            cleaned_texts = [
                line.strip()  # Strip any leading/trailing whitespace from each line
                for e in elements
                for line in etree.tostring(e, encoding="unicode", method="html").splitlines()  # Split into lines
                if line.strip()  # Only include non-empty lines
            ]

            return cleaned_texts

        except etree.XMLSyntaxError as e:
            # Handle parsing errors by returning text split by newlines
            print(f"Error parsing HTML: {e}")
            return [line.strip() for line in text.splitlines() if line.strip()]  # Handle raw text splitting by lines


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
            record = self.readToModel(resource, eadid, resource['uri'])

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
            
            record = self.readToModel(resource, eadid, resource['uri'])
            
            return record
    
    def read_since(self, last_run_time):
        """
        Reads a resource and its associated archival objects
        Uses URL and login info from ~/.archivessnake.yml
        
        Parameters:
            last_run_time (int): an integer representing POSIX time

        Returns:
            records_uris (list): a list of ASpace resource URIs updated since POSIX time
        """
        records_uris = []
        modifiedList = self.client.get(f'repositories/{str(self.repo)}/resources?all_ids=true&modified_since={str(last_run_time)}').json()
        if len(modifiedList) < 1:
            print ("No collections modified since last run.")
        else:
            #print (modifiedList)
            for collection_uri in modifiedList:
                records_uris.append(int(collection_uri))

        return records_uris

    def readToModel(self, apiObject, eadid, resource_uri, collection_name="", recursive_level=0):
        """
        A recursive function that initally takes a resource from the ASpace API and reads it to a model.
        Then calls itself on any child archival_object records
        
        Parameters:
            apiObject (dict): a resource or archival object from the ASpace API as a JSON dict
            eadid (str): a collection's EADID as a string
            resource_uri (str): The uri to the apiObject's resource
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
        record.title_filing_ssi = apiObject.get("finding_aid_filing_title", None)
        record.repository = self.repo_name
        record.level = apiObject["level"]

        for date in apiObject["dates"]:
            dateObj = Date()
            if "expression" in date.keys():
                dateObj.expression = date['expression']
            elif "begin" in date.keys() and "end" in date.keys():
                dateObj.expression = f"{iso2DACS(date['begin'])} - {iso2DACS(date['end'])}"
            elif "begin" in date.keys():
                dateObj.expression = iso2DACS(date['begin'])
            if "begin" in date.keys():
                dateObj.begin = date['begin']
                if date['date_type'].lower() == "bulk":
                    dateObj.date_type = "bulk"
                elif date['date_type'].lower() == "inclusive":
                    dateObj.date_type = "inclusive"
                if "end" in date.keys():
                    dateObj.end = date['end']
                elif "end" in date.keys():
                    dateObj.expression = f"{iso2DACS(date['begin'])} - {iso2DACS(date['end'])}"
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
                record.agents.append(agentObj)
        # Subjects
        for subject_ref in apiObject['subjects']:
            subject = self.client.get(subject_ref['ref']).json()
            # ASpace allows multiple terms per subject, and each can be geo, topical, etc. so I'm just using the first one.
            if subject['terms'][0]['term_type'] == "genre_form":
                record.genreform.append(subject['title'])
            elif subject['terms'][0]['term_type'] == "geographic":
                record.places.append(subject['title'])
            else:
                record.subjects.append(subject['title'])

        # Notes
        for note in apiObject["notes"]:
            if note['publish'] == True:
                if "label" in note.keys():
                    setattr(record, note["type"] + "_heading", note["label"])
                if note["jsonmodel_type"] == "note_singlepart":
                    setattr(record, note["type"], note["content"])
                else:
                    note_text = []
                    for subnote in note["subnotes"]:
                        if subnote['publish'] == True:
                            if "content" in subnote.keys():
                                note_text.extend(self.extract_xpath_text(subnote["content"]))
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

        has_representative_instance = any(instance.get("is_representative") for instance in apiObject["instances"] if instance.get("instance_type") == "digital_object")
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
                # Skip this instance if another one is marked representative
                if has_representative_instance and not instance.get("is_representative"):
                    continue

                digital_object = self.client.get(instance['digital_object']['ref']).json()
                if digital_object.get('publish', False):
                    if "file_versions" in digital_object and len(digital_object["file_versions"]) > 0:
                        has_representative_file = any(fv.get("is_representative") for fv in digital_object["file_versions"])

                        for file_version in digital_object["file_versions"]:
                            # Skip non-representative file versions if a representative exists
                            if has_representative_file and not file_version.get("is_representative"):
                                continue

                            if file_version.get("publish", False):
                                if "file_uri" in file_version.keys():
                                    dao = DigitalObject()
                                    dao.identifier = file_version["file_uri"]
                                    dao.label = digital_object["title"]

                                    for dao_system in self.dao_systems:
                                        dao = dao_system.read_data(dao)

                                    record.digital_objects.append(dao)

        
        recursive_level += 1
        params = {"published_only": True}
        batch_params = {"published_only": True}
        if apiObject['jsonmodel_type'] == "resource":
            tree = self.client.get(f"{resource_uri}/tree/root", params=params).json()
            max_offset = tree['waypoints']
        else:
            params["node_uri"] = apiObject["uri"]
            tree = self.client.get(f"{resource_uri}/tree/node", params=params).json()
            max_offset = tree['waypoints']
            batch_params["parent_node"] = apiObject["uri"]

        for i in range(max_offset):
            batch_params["offset"] = i
            batch = self.client.get(f"{resource_uri}/tree/waypoint", params=batch_params).json()
            for child in batch:
                record_uri = child['uri']
                component = self.client.get(record_uri).json()    

                subrecord = self.readToModel(component, eadid, resource_uri, collection_name, recursive_level)
                record.components.append(subrecord)

        return record
