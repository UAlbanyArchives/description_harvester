import os
import sys
from lxml import etree
from typing import List
from io import StringIO
from typing import List
from pathlib import Path
from iso639 import languages
from asnake.client import ASnakeClient
import asnake.logging as logging
from description_harvester.models.description import Component, Date, Extent, Agent, Container, DigitalObject
from description_harvester.utils import iso2DACS
from description_harvester.plugins import Plugin, import_plugins

logging.setup_logging(stream=sys.stdout, level='INFO')

class ArchivesSpace():
    """This class connects to an ArchivesSpace repository"""

    def __init__(self, repository_id=2):
        """
        Connects to an ASpace repo using ArchivesSnake.
        Uses URL and login info from ~/.archivessnake.yml
        
        Parameters:
            repository (int): The ASpace Repository ID. Defaults to 2.
        """

        self.client = ASnakeClient()
        self.repo = repository_id
        repo_response = self.client.get('repositories/' + str(self.repo))
        if repo_response.status_code == 200:
            self.repo_name = repo_response.json().get('name', 'Unknown')
        else:
            raise Exception(f"Failed to fetch repository {self.repo} data from ArchivesSpace. Status code: {repo_response.status_code}")

        plugin_basedir = os.environ.get("DESCRIPTION_HARVESTER_PLUGIN_DIR", None)
        # Plugins are loaded from:
        #   1. plugins directory inside the package (built-in)
        #   2. .description_harvester in user home directory
        #   3. plugins subdirectories in plugin dir set in environment variable
        plugin_dirs = []
        plugin_dirs.append(Path(f"~/.description_harvester").expanduser())
        if plugin_basedir:
            plugin_dirs.append((Path(plugin_basedir)).expanduser())
        import_plugins(plugin_dirs)

        # Instantiate plugins
        self.plugins = []
        for plugin_cls in Plugin.registry.values():
            plugin_instance = plugin_cls()  # this will call __init__()
            self.plugins.append(plugin_instance)

    @property
    def plugin_map(self):
        return Plugin.registry


    def extract_xpath_text(self, text: str) -> List[str]:
        """
        Extracts textual content from an HTML string while omitting <html> and <body> tags.
        
        This function:
        - Parses the input string as HTML using lxml with error recovery.
        - Extracts all elements except <html> and <body>.
        - Retrieves their textual content, preserving line breaks.
        - Strips leading and trailing whitespace from each line.
        - Ensures that empty lines are not included in the output.

        Args:
            text (str): A string containing HTML content.

        Returns:
            List[str]: A list of cleaned text lines extracted from the HTML.
        
        If an XML parsing error occurs, the function falls back to splitting the raw input 
        text by newlines and removing empty lines.
        """

        try:
            # Parse the HTML content with a lenient parser (recover=True handles broken HTML)
            parser = etree.HTMLParser(recover=True)
            tree = etree.parse(StringIO(text), parser)

            # Extract all elements except <html> and <body>
            elements = tree.xpath("//*[not(self::html or self::body)]")

            # Extract text content while preserving line breaks and removing empty items
            cleaned_texts = [
                line.strip()  # Remove leading/trailing spaces
                for e in elements
                for line in etree.tostring(e, encoding="unicode", method="html").splitlines()  # Split by lines
                if line.strip()  # Ignore empty lines
            ]

            # Ensure we filter out any lingering empty strings
            return [line for line in cleaned_texts if line]

        except etree.XMLSyntaxError as e:
            # Handle cases where the input is not well-formed HTML
            print(f"Error parsing HTML: {e}")
            return [line.strip() for line in text.splitlines() if line.strip()]


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
        # for multiple id_0, id_1, etc.
        else:
            resources = self.client.get(f'repositories/{str(self.repo)}/find_by_id/resources?identifier[]=["{id}"]')
        if len(resources.json()['resources']) != 1:
            raise Exception(f"ERROR: Found {len(resources.json()['resources'])} matching repositories in ArchivesSpace.")
        resource = self.client.get(resources.json()['resources'][0]['ref']).json()

        if resource["publish"] != True:
            print (f"Skipping unpublished resource {resource['id_0']}")
        else:
            if not "ead_id" in resource.keys() or len(resource["ead_id"]) < 1:
                print (f"ERROR: not EAD ID for {resource['id_0']}.")
            else:
                eadid = resource["ead_id"]

                # Allow plugin overrides for repository names
                for plugin in self.plugins:
                    repo_name = plugin.custom_repository(resource)
                    if repo_name:
                        self.repo_name = repo_name

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
            print (f"{resource['id_0']}: {resource['title']} is an Unpublished record")
            return None
        else:
            eadid = resource["ead_id"]

            # Allow plugin overrides for repository names
            for plugin in self.plugins:
                repo_name = plugin.custom_repository(resource)
                if repo_name:
                    self.repo_name = repo_name
            
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
            for collection_uri in modifiedList:
                records_uris.append(int(collection_uri))

        return records_uris

    def all_resource_ids(self):
        print ("Requesting full list of collection IDs...")
        records_ids = []
        fullList = self.client.get(f'repositories/{str(self.repo)}/resources?all_ids=true').json()
        if len(fullList) < 1:
            print ("No collections present.")
        else:
            for collection_uri in fullList:
                resource = self.client.get(f"repositories/{str(self.repo)}/resources/{collection_uri}").json()
                records_ids.append(resource["id_0"])

        return records_ids

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
        print (f"{indent}Reading {apiObject.get('title', None)}...")
        
        record = Component()
        
        #record.title = apiObject["title"]
        record.title = apiObject.get("title", None)
        record.title_filing_ssi = apiObject.get("finding_aid_filing_title", None)
        record.level = apiObject["level"]
        record.repository = self.repo_name

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

        # Set repository. Can be overridden by plugin.
        #record.repository = self.repo_name
        #for plugin in self.plugins:
        #    record.repository = plugin.custom_repository(record)

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
                if "label" in note.keys() and "type" in note.keys():
                    setattr(record, note["type"] + "_heading", note["label"])
                if note["jsonmodel_type"] == "note_singlepart":
                    setattr(record, note["type"], note["content"])
                elif note["jsonmodel_type"] == "note_bibliography":
                    if getattr(record, "bibliography_heading", None):
                        record.bibliography_heading += f"; {note['label']}"
                    else:
                        setattr(record, "bibliography_heading", note["label"])
                    if getattr(record, "bibliography", None):
                        record.bibliography.extend(note["items"])
                    else:
                        setattr(record, "bibliography", note["items"])
                else:
                    note_text = []
                    for subnote in note["subnotes"]:
                        if subnote['publish'] == True:
                            if "content" in subnote.keys():
                                note_text.extend(self.extract_xpath_text(subnote["content"]))
                            elif subnote['jsonmodel_type'] == "note_chronology":
                                events = []
                                for event in subnote["items"]:
                                    event_date = event.get("event_date", "")
                                    event_text = event.get("events", "")
                                    events.append(f"{date}: {event_text}")
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

                                    for plugin in self.plugins:
                                        updated_dao = plugin.read_data(dao)
                                        if updated_dao:
                                            dao = plugin.read_data(dao)

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
