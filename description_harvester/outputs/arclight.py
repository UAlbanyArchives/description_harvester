import re
import copy
import pysolr
from bs4 import BeautifulSoup
from description_harvester.utils import extract_years
from description_harvester.models.arclight import SolrCollection, SolrComponent

class Arclight():


    def __init__(self, solr_url, repository_name):
        """
        Connects to an accessible Solr instance with pysolr.

        Parameters:
            solr_url(str): The url for a solr instance, such as http://solr.me.edu:8983/solr/my_core
        """

        self.solr = pysolr.Solr(solr_url, always_commit=True)
        self.solr.ping()

        self.repository_name = repository_name
        

    def convert(self, record):

        has_online_content = set()

        print(f"\tconverting to {record.id} to Solr documents...")
        solrDocument, has_online_content, total_component_count = self.convertCollection(record, has_online_content)
        solrDocument.total_component_count_is = int(total_component_count)
        
        if len(has_online_content) > 0:
            if solrDocument.id in has_online_content:
                solrDocument.has_online_content_ssim = ["true"]                
            solrDocument = self.mark_online_content(solrDocument, has_online_content)
            solrDocument.online_item_count_is = int(len(has_online_content))

        return solrDocument

    def mark_online_content(self, solrComponent, has_online_content):
        
        for component in solrComponent.components:
            if component.ref_ssi in has_online_content:
                component.has_online_content_ssim = ["true"]
            else:
                component.has_online_content_ssim = ["false"]
            childComponent = self.mark_online_content(component, has_online_content)

        return solrComponent


    def strip_text(self, note_text):
        """
        Takes a string or list of strings, strips out any HTML tags, and returns a single clean string.
        
        Args:
            note_text (str or list of str): Input text containing HTML markup.
        
        Returns:
            str: Cleaned text with HTML tags removed.
        """
        if isinstance(note_text, list):
            combined_text = ' '.join(note_text)
        else:
            combined_text = str(note_text)

        soup = BeautifulSoup(f"<html><body>{combined_text}</body></html>", "html.parser")
        return soup.get_text(separator=' ', strip=True)

    def replace_emph_tags(self, text):
        """
        Replaces <emph> tags with corresponding HTML tags based on the 'render' attribute.
        If no 'render' attribute is present, it defaults to italic (<i>).

        Args:
            text (str): The input EAD2002 XML text containing <emph> tags.

        Returns:
            str: The input text with <emph> tags replaced by corresponding HTML tags.
        """

        # Define a dictionary to map 'render' attribute values to HTML tags
        render_to_html = {
            "bold": "b",
            "bolddoublequote": "b",
            "bolditalic": "b",
            "boldsinglequote": "b",
            "boldsmcaps": "b",
            "boldunderline": "b",
            "doublequote": "q",
            "italic": "i",
            "nonproport": "pre",
            "singlequote": "q",
            "smcaps": "span",  # Assuming you'll style it with CSS later
            "sub": "sub",
            "super": "sup",
            "underline": "u"
        }

        def replacer(match):
            """
            Helper function to replace <emph> tags with the corresponding HTML tags.

            Args:
                match (re.Match): The match object containing the full match of <emph> tag.
            
            Returns:
                str: The text with <emph> tag replaced by HTML tags.
            """
            # Try to get the 'render' attribute (group 1) if available
            render = match.group(1) if match.group(1) else None  # 'render' attribute, if present
            content = match.group(2)  # Content inside the <emph> tag
            
            # If render attribute exists, use it to find the correct HTML tag
            if render:
                html_tag = render_to_html.get(render, "i")  # Default to 'i' if render value is unknown
            else:
                # Default to 'italic' if no render attribute is present
                html_tag = "i"
            
            # Return content wrapped in the appropriate HTML tag
            return f"<{html_tag}>{content}</{html_tag}>"

        # Replace <emph> tags with a 'render' attribute
        modified_text = re.sub(r'<emph render="([^"]+)">(.*?)</emph>', replacer, text)

        # Replace <emph> tags without a 'render' attribute (defaults to italics)
        modified_text = re.sub(r'<emph(.*?)>(.*?)</emph>', replacer, modified_text)

        return modified_text




    def convertCollection(self, record, has_online_content, total_component_count=0, recursive_level=0, parents=[], parent_titles=[], parent_levels=[], inherited_data={}):
        """
        A recursive function to convert collection and component objects to Arclight-friendly solr docs.
        It takes a component object and converts it and any child objects to an Arclight-friendly
        array of Solr docs.

        Parameters:
            record (Component): a hierarchical component object containing all public-facing description for a collection
            has_online_content (set):
            total_component_count(int): a running integer of the total components
            recursive_level (int): The level of recursion. Start at 0
            parents (list): A list of parent IDs as strings
            parent_titles (list): A list of parent names as strings
            parent_levels (list): A list of parent levels as strings
            inherited_data(dict): data inherited from upper-level ASpace API objects
                collection_name (list): The resource title
                child_component_count (int): The number of child components
                collection_creator (list): The collection-level creator as a list of strings
                parent_access_restrict (list): A list of access restriction paragraphs from the most immediate parent
                parent_access_terms (list): A list of use restriction paragraphs from the most immediate parent

        Returns:
            solrDocument (SolrCollection): a solr collection document containing nested solr component docs
        """

        if record.level == "collection":
            solrDocument = SolrCollection()
            solrDocument.ead_ssi = [record.collection_id]
        else:
            solrDocument = SolrComponent()

        solrDocument.level_ssm = [record.level.title().lower()]
        solrDocument.level_ssim = [record.level.title()]

        dates = []
        string_dates = []
        date_set = []
        for date in record.dates:
            if getattr(date, "date_type", None) == "bulk":
                string_date = "bulk "
            else:
                string_date = ""
            if getattr(date, "expression", None) != None:
                dates.append(date.expression)
                string_date += date.expression
            elif getattr(date, "date_type", None) != None:
                dates.append(f"{date.begin}-{date.end}")
                string_date = f"{string_date}{date.begin}-{date.end}"
            else:
                dates.append(date.begin)
                string_date += date.begin
            string_dates.append(string_date)
            
            if getattr(date, "begin", None) != None:
                date_set.append(int(date.begin.split("-")[0]))
                if getattr(date, "end", None) != None:
                    date_set.append(int(date.end.split("-")[0]))
            elif getattr(date, "expression", None) != None:
                try:
                    date_set = extract_years(date.expression)
                    date_list = list(range(min(date_set), max(date_set) + 1))
                except:
                    print (f"\tWARNING: Unable to extract year range for expression-only date {date.expression}. Date facet will not work for this component.")

        if len(date_set) > 0:
            solrDocument.date_range_isim = list(range(min(date_set), max(date_set) + 1))
        solrDocument.unitdate_ssm = dates
        solrDocument.normalized_date_ssm = [", ".join(string_dates)]

        if record.title:
            solrDocument.title_ssm = [self.strip_text(record.title)]
            solrDocument.title_tesim = [self.strip_text(record.title)]
            if "<emph" in record.title:
                solrDocument.title_html_tesm = [self.replace_emph_tags(record.title)]
            else:
                solrDocument.title_html_tesm = [record.title]
        # this this empty for components, which I think is fine. v1.4 just uses the title field
        solrDocument.title_filing_ssi = record.title_filing_ssi

        if record.title:
            solrDocument.normalized_title_ssm = [f"{solrDocument.title_ssm[0]}, {solrDocument.normalized_date_ssm[0]}"]
        else:
            solrDocument.normalized_title_ssm = [solrDocument.normalized_date_ssm[0]]
        solrDocument.component_level_isim = [recursive_level]
        #solrDocument.collection_title_tesim = solrDocument.normalized_title_ssm
        if record.level == "collection":
            solrDocument.id = record.id.replace(".", "-")
            solrDocument.unitid_ssm = [record.collection_id]
            solrDocument.unitid_tesim = [record.collection_id]
            solrDocument.collection_ssim = solrDocument.normalized_title_ssm
            solrDocument.sort_isi = 0
            inherited_data['collection_name'] = solrDocument.normalized_title_ssm
            col_creators = []
            for col_creator in record.creators:
                col_creators.append(col_creator.name)
            inherited_data['collection_creator'] = col_creators

            new_parents = [record.collection_id.replace(".", "-")]
            new_parent_titles = solrDocument.normalized_title_ssm
            new_parent_levels = solrDocument.level_ssm
        else:
            record.component_level_isim = [recursive_level]

            #Arclight expects the collection id to be prepended to component ids but not to ref_ssm
            solrDocument.id = record.collection_id.replace(".", "-") + record.id.replace(".", "-")
            solrDocument.ref_ssi = record.id.replace(".", "-")
            # dunno why this is duplicated, but it seems to be like this in the default indexer
            solrDocument.ref_ssm = [record.id.replace(".", "-"), record.id.replace(".", "-")]
            solrDocument.collection_ssm = inherited_data['collection_name']
            solrDocument.collection_sim = inherited_data['collection_name']
            solrDocument.collection_ssi = inherited_data['collection_name']
            solrDocument.collection_ssim = inherited_data['collection_name']
            #v1.4 doesn't appear to store this anymore
            #if "collection_creator" in inherited_data.keys():
            #    solrDocument.collection_creator_ssm = inherited_data['collection_creator']

            # not sure why this is stored twice
            solrDocument.parent_ssim = parents
            solrDocument.parent_ids_ssim = parents
            # parent_ssi appears to be only the immediate parent
            if len(parents) > 0:
                solrDocument.parent_ssi = [parents[-1]]

            solrDocument.parent_unittitles_ssm = parent_titles
            solrDocument.parent_unittitles_tesim = parent_titles
            solrDocument.parent_levels_ssm = parent_levels
            #solrDocument.component_level_isim = [recursive_level]
            solrDocument.child_component_count_isi = [inherited_data["child_component_count"]]
            # for access notes, inherit the note from the most closest parent component
            if "parent_access_restrict" in inherited_data.keys() and len(inherited_data["parent_access_restrict"]) > 0:
                solrDocument.parent_access_restrict_tesm = [inherited_data["parent_access_restrict"][-1]]
            if "parent_access_terms" in inherited_data.keys() and len(inherited_data["parent_access_terms"]) > 0:
                solrDocument.parent_access_terms_tesm = [inherited_data["parent_access_terms"][-1]]

            new_parents = copy.deepcopy(parents)
            new_parents.append(record.id.replace(".", "-"))
            new_parent_titles = copy.deepcopy(parent_titles)
            new_parent_titles.append(solrDocument.normalized_title_ssm[0])
            new_parent_levels = copy.deepcopy(parent_levels)
            new_parent_levels.append(record.level)

        # repository_ssm is empty in stock arclight for components, but I think its fine to set it
        if self.repository_name:
            solrDocument.repository_ssim = [self.repository_name]
            solrDocument.repository_ssm = [self.repository_name]
        else:
            solrDocument.repository_ssm = [record.repository]
            solrDocument.repository_ssim = [record.repository]

        extents = []
        for extent in record.extents:
            extents.append(f"{extent.number} {extent.unit}")
        solrDocument.extent_ssm = extents
        solrDocument.extent_tesim = extents

        if hasattr(record, "languages") and len(record.languages) > 0:
            solrDocument.language_ssim = [", ".join(record.languages)]

        # I think the ASpace Agent updates added many more of these that Arclight doesn't handle atm
        agent_translations = {
            "corporate_entity": "corpname_ssim",
            "family": "famname_ssim",
            "person": "persname_ssim"
        }
        # Agents are wonky in the default indexer which this recreates, but it should probably be thought out better. I don't have great data to do it right
        creators = []
        names = []
        for creator in record.creators:
            creators.append(creator.name)
            if creator.agent_type in agent_translations.keys():
                setattr(solrDocument, agent_translations[creator.agent_type], [creator.name])
                #setattr(solrDocument, "creator_" + agent_translations[creator.agent_type], [creator.name])
                setattr(solrDocument, "creator_" + agent_translations[creator.agent_type].rsplit("_", 1)[0] + "_ssim", [creator.name])
            else:
                names.append(creator.name)
        solrDocument.creator_ssm = creators
        solrDocument.creator_ssim = creators
        solrDocument.creator_sort = min(creators) if creators else ""
        for agent in record.agents:
            names.append(agent.name)
            if agent.agent_type in agent_translations.keys():
                setattr(solrDocument, agent_translations[agent.agent_type], [agent.name])
        solrDocument.names_ssim = names
        solrDocument.names_coll_ssim = names

        solrDocument.access_subjects_ssm = record.subjects
        solrDocument.access_subjects_ssim = record.subjects
        solrDocument.genreform_ssim = record.genreform

        # Seems imprecise, but this is how what the existing indexer does.
        # Still does this as of v1.4
        solrDocument.geogname_ssm = record.places
        solrDocument.geogname_ssim = record.places
        solrDocument.places_ssim = record.places

        # Notes
        notes = [
            "abstract",
            "physloc",
            "processinfo",
            "bioghist",
            "scopecontent",
            "arrangement",
            "acqinfo",
            "accessrestrict",
            "userestrict",
            "prefercite",
            "odd",
            "originalsloc",
            "altformavail",
            "separatedmaterial",
            "relatedmaterial",
            "custodhist",
            "phystech",
            "otherfindaid",
            "accruals",
            "appraisal",
            "fileplan",
            "materialspec",
            "bibliography",
            "dimensions",
            "note"
        ]
        for note in dir(record):
            if note in notes:
                note_text = getattr(record, note)
                if note == "acqinfo":
                    setattr(solrDocument, note + "_ssim", note_text)
                else:
                    stripped_text = [self.strip_text(item) for item in note_text]
                    setattr(solrDocument, note + "_tesim", stripped_text)
                    setattr(solrDocument, note + "_html_tesm", note_text)
                    if getattr(record, note + "_heading", None):
                        setattr(solrDocument, note + "_heading_ssm", [getattr(record, note + "_heading", None)])
                    if note == "accessrestrict":
                        #inherited_data.setdefault("parent_access_restrict", []).extend(stripped_text)
                        inherited_data["parent_access_restrict"] = inherited_data.get("parent_access_restrict", []).copy()
                        inherited_data["parent_access_restrict"].extend(stripped_text)
                    elif note == "userestrict":
                        #inherited_data.setdefault("parent_access_terms", []).extend(stripped_text)
                        inherited_data["parent_access_terms"] = inherited_data.get("parent_access_terms", []).copy()
                        inherited_data["parent_access_terms"].extend(stripped_text)
                        # Dunno why it does this. ¯\_(ツ)_/¯
                        solrDocument.access_terms_ssm = stripped_text

        
        # Containers
        # This is a bit nuts, but it was just as much code as a function so I left it explicit
        containers_ssim = []
        for container in record.containers:
            container_string = []
            if hasattr(container, "top_container") and container.top_container != None:
                container_string.append(container.top_container)
            if hasattr(container, "top_container_indicator") and container.top_container_indicator != None:
                container_string.append(container.top_container_indicator)
            if len(container_string) > 0:
                containers_ssim.append(" ".join(container_string))
            sub_container_string = []
            if hasattr(container, "sub_container") and container.sub_container != None:
                sub_container_string.append(container.sub_container)
            if hasattr(container, "sub_container_indicator") and container.sub_container_indicator != None:
                sub_container_string.append(container.sub_container_indicator)
            if len(sub_container_string) > 0:
                containers_ssim.append(" ".join(sub_container_string))
            sub_sub_container_string = []
            if hasattr(container, "sub_sub_container") and container.sub_sub_container != None:
                sub_sub_container_string.append(container.sub_sub_container)
            if hasattr(container, "sub_sub_container_indicator") and container.sub_sub_container_indicator != None:
                sub_sub_container_string.append(container.sub_sub_container_indicator)
            if len(sub_sub_container_string) > 0:
                containers_ssim.append(" ".join(sub_sub_container_string))
        solrDocument.containers_ssim = containers_ssim

        """
        if len(record.digital_objects) < 1:
            has_dao = False
        elif len(record.digital_objects) == 1 and record.digital_objects.is_representative == True:
            solrDocument.href_sim = record.digital_objects[0].href
            solrDocument.thumbnail_href_sim = record.digital_objects[0].thumbnail_href
            solrDocument.label_ssm = record.digital_objects[0].label
            solrDocument.identifier_sim = record.digital_objects[0].identifier
            solrDocument.is_representative_sim = record.digital_objects[0].is_representative
            solrDocument.filename_sim = record.digital_objects[0].filename
            solrDocument.mime_type_sim = record.digital_objects[0].mime_type
            solrDocument.rights_statement_ssm = record.digital_objects[0].rights_statement
            for field in record.digital_objects[0].metadata.keys():
                setattr(solrDocument, field + "_ssm", record.digital_objects[0].metadata[field])
            #content_ssm
        else:
            for digital_object in record.digital_objects:
                dao_component = SolrComponent()

                solrDocument.components.append(subcomponent)
        """
        has_dao = False
        daos = []
        for digital_object in record.digital_objects:
            has_dao = True
            dao = "{\"label\":\"" + digital_object.label + "\",\"href\":\"" + digital_object.identifier + "\"}"
            daos.append(str(dao))
        solrDocument.digital_objects_ssm = daos
        
        if has_dao:
            has_online_content.add(record.id.replace(".", "-"))
            has_online_content.update(parents)

        # bump recursion level
        recursive_level += 1

        order_counter = 0
        for component in record.components:
            total_component_count += 1
            inherited_data["child_component_count"] = len(component.components)
            subcomponent, has_online_content, total_component_count = self.convertCollection(component, has_online_content, total_component_count, recursive_level, new_parents, new_parent_titles, new_parent_levels, copy.deepcopy(inherited_data))
            order_counter += 1
            subcomponent.sort_isi = order_counter
            solrDocument.components.append(subcomponent)

        return solrDocument, has_online_content, total_component_count

    def post(self, collection):

        print ("\tPOSTing data to Solr...")
        self.solr.add([collection.to_dict()])