import os
import re
from pathlib import Path
from lxml import etree
from description_harvester.models.description import Component, Date, Extent, Agent, Container, DigitalObject
from description_harvester.plugins import Plugin, import_plugins

class EAD:
    def __init__(self, path, verbose=False):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"The specified path does not exist: {self.path}")
        self.verbose = verbose

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

    def items(self):
        """Yield each EAD file path (handles file or directory)."""
        if self.path.is_file():
            yield self.path
        else:
            for file in self.path.rglob("*.xml"):
                yield file

    def fetch(self, file_path, use_uri=False):
        """Read and parse a single EAD file and map to `Component` model.

        Returns a `Component` instance representing the top-level collection.
        """
        return self.read(file_path)

    def read(self, file_path):
        """Read a single EAD file and return a Component with full hierarchy.
        
        Parameters:
            file_path: Path to the EAD XML file
            
        Returns:
            Component: The top-level collection component with nested children
        """
        if self.verbose:
            print(f"Parsing EAD-XML file {file_path}")
            
        file_path = Path(file_path)
        xml_text = file_path.read_text(encoding="utf-8")

        # Parse with lxml and handle the default EAD namespace
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
        ns = {"ead": root.nsmap.get(None)}
        
        # Get top-level archdesc
        arch = root.find(".//ead:archdesc", namespaces=ns)
        did = arch.find("ead:did", namespaces=ns) if arch is not None else None
        
        # Extract top-level metadata
        eadid_el = root.find(".//ead:eadheader/ead:eadid", namespaces=ns)
        eadid = self._text_of(eadid_el)
        title = self._text_of(did.find("ead:unittitle", namespaces=ns)) if did is not None else None
        repository = self._text_of(did.find("ead:repository/ead:corpname", namespaces=ns)) if did is not None else None
        
        # Build top-level component using readToModel
        # Pass eadid as both id and collection_id for the top level
        record = self.readToModel(arch, eadid, repository, title, ns)
        
        # Attach raw XML to top-level component only
        try:
            record.raw_xml = xml_text
        except Exception:
            pass
        
        return record

    def readToModel(self, elem, collection_id, repository, collection_name, ns, recursive_level=0):
        """Recursively build a Component from EAD elements.
        
        This handles both the top-level archdesc and component (<c>/<c01>/etc.) elements.
        
        Parameters:
            elem: The element to process (archdesc or component element)
            collection_id: The top-level collection id (constant throughout recursion)
            repository: The repository name
            level: The archival level
            ns: Namespace dict
            collection_name: Collection name for children (set to title for top level)
            recursive_level: Current recursion depth
            
        Returns:
            Component: The built component with children
        """

        did = elem.find("ead:did", namespaces=ns) if elem is not None else None
        title = self._text_of(did.find("ead:unittitle", namespaces=ns)) if did is not None else ""

        # Print the name of the object being read, correctly indented        
        indent = (recursive_level + 1) * "\t"
        if recursive_level == 0:
            print (f"{indent}Reading {title} ({collection_id})...")
        elif self.verbose:
            print (f"{indent}Reading {title}...")
            
        # Build the component
        record = Component()
        record_id = None
        if "id" in elem.attrib:
            record_id = elem.get("id")
        else:
            uid_el = elem.find("ead:did/ead:unitid", namespaces=ns)
            record_id = self._text_of(uid_el)

            if not record_id:
                eadid_el = elem.getroottree().getroot().find(
                    "ead:eadheader/ead:eadid",
                    namespaces=ns
                )
                record_id = self._text_of(eadid_el)
        if not record_id:
            raise ValueError("No identifier found (@id, unitid, or eadid)")
        record.id = record_id

        record.collection_id = collection_id or ""
        record.repository = repository or ""
        record.collection_name = collection_name
        record.title = title
        record.level = elem.get("level") or (did.findtext("ead:level", namespaces=ns) if did is not None else "unknown")

        # Parse dates and extents from the element's DID
        if did is not None:
            record.dates = self._parse_dates(did, ns)
            record.extents = self._parse_extents(did, ns)
            record.languages = self._parse_languages(did, ns)
            record.creators = self._parse_origination(did, ns)
            # Parse notes that may be in the DID (abstract, physloc, materialspec, note)
            self._parse_notes(elem, did, ns, record)
        
        # Parse controlaccess for agents, subjects, genreform, and places
        self._parse_controlaccess(elem, ns, record)

        # Parse physical containers from did or direct children
        self._parse_containers(elem, did, ns, record)

        # Parse digital objects (dao) from did or component
        self._parse_daos(elem, did, ns, record)

        # Dao plugins
        for dao in record.digital_objects:
            for plugin in self.plugins:
                updated_dao = plugin.update_dao(dao)
                if updated_dao:
                    dao = updated_dao
        
        # Parse containers
        self._parse_containers(elem, did, ns, record)
        
        # Parse child components recursively
        # Children can be in either <dsc> (top-level) or directly nested within <c> elements
        if elem is not None:
            # First check for <dsc> (top-level children)
            dsc = elem.find("ead:dsc", namespaces=ns)
            if dsc is not None:
                for child in dsc:
                    try:
                        local = etree.QName(child).localname
                    except Exception:
                        continue
                    if local and local.startswith('c'):
                        # Recursively call readToModel for child component
                        child_comp = self.readToModel(
                            child,
                            collection_id,
                            repository,
                            collection_name,
                            ns,
                            recursive_level=recursive_level + 1
                        )
                        record.components.append(child_comp)
            
            # Also check for nested <c> elements (children within component)
            for child in elem.findall("ead:c", namespaces=ns):
                # Recursively call readToModel for nested child component
                child_comp = self.readToModel(
                    child,
                    collection_id,
                    repository,
                    collection_name,
                    ns,
                    recursive_level=recursive_level + 1
                )
                record.components.append(child_comp)
        
        return record

    def _render_chronlist(self, chronlist_el, ns):
        """ parse <chronlist> into a basic html table as a str"""

        rows = []
        for item in chronlist_el.findall("ead:chronitem", namespaces=ns):
            # Get date text
            date_el = item.find("ead:date", namespaces=ns)
            date_text = date_el.text.strip() if date_el is not None and date_el.text else ""

            # Get all events (prefer eventgrp if present, otherwise direct children)
            events_texts = []
            eventgrp = item.find("ead:eventgrp", namespaces=ns)
            event_parent = eventgrp if eventgrp is not None else item
            
            for ev in event_parent.findall("ead:event", namespaces=ns):
                # Use tostring to preserve inline tags like <emph>
                ev_html = etree.tostring(ev, encoding='unicode', method='html')
                # Remove the <event ...> opening tag (with any attributes) and </event> closing tag
                ev_html = re.sub(r'^<event[^>]*>', '', ev_html)
                ev_html = ev_html.replace('</event>', '', 1)
                ev_html = ev_html.strip()
                if ev_html:
                    events_texts.append(self._normalize_ead_tags(ev_html))

            # Join multiple events with semicolons
            events_combined = "; ".join(events_texts)

            # Add table row
            rows.append(f"<tr><th>{date_text}</th><td>{events_combined}</td></tr>")

        return "<table>\n" + "\n".join(rows) + "\n</table>"


    def _extract_note_paragraphs(self, el, ns):
        """Return a list of paragraph strings for a note element, excluding any <head> content.

        Handles elements with <p> children or plain text mixed content.
        Normalizes EAD formatting tags to HTML, preserving tag content.
        """
        if el is None:
            return []

        paragraphs = []
        # If there are explicit <p> children, use those
        p_els = el.findall("ead:p", namespaces=ns)
        if p_els:
            for p in p_els:
                # Serialize to string to preserve inline tags like <emph>
                text = etree.tostring(p, encoding='unicode', method='html')
                # Remove the <p></p> wrapper that etree.tostring adds
                if text.startswith('<p'):
                    text = text[text.find('>')+1:]
                if text.endswith('</p>'):
                    text = text[:-4]
                text = text.strip()
                if text:
                    text = self._normalize_ead_tags(text)
                    paragraphs.append(text)
            
        chronlists = el.findall("ead:chronlist", namespaces=ns)
        if chronlists:
            for cl in chronlists:
                paragraphs.append(self._render_chronlist(cl, ns))

        return paragraphs

        # Otherwise, collect text of child elements excluding <head>
        if el.text and el.text.strip():
            text = el.text.strip()
            text = self._normalize_ead_tags(text)
            paragraphs.append(text)

        for child in el:
            try:
                local = etree.QName(child).localname
            except Exception:
                local = None
            if local == 'head':
                # skip head content here
                if child.tail and child.tail.strip():
                    text = child.tail.strip()
                    text = self._normalize_ead_tags(text)
                    paragraphs.append(text)
                continue
            # Serialize child to preserve inline tags like <emph>
            text = etree.tostring(child, encoding='unicode', method='html')
            text = text.strip()
            if text:
                text = self._normalize_ead_tags(text)
                paragraphs.append(text)

        # Fallback: if nothing collected, use the element text content without head
        if not paragraphs:
            # remove head text if present
            head = el.find("ead:head", namespaces=ns)
            full = self._text_of(el) or ""
            if head is not None:
                head_text = self._text_of(head) or ""
                full = full.replace(head_text, "", 1).strip()
            if full:
                full = self._normalize_ead_tags(full)
                paragraphs = [full]

        return paragraphs

    def _parse_notes(self, elem, did, ns, record):
        """Populate the Component `record` with note fields from DID and child elements.

        Notes that typically live in the DID are parsed from `did` (e.g. abstract, physloc, materialspec, note).
        Other notes are parsed from direct child elements of `elem`.
        """
        NOTE_FIELDS = [
            'abstract', 'acqinfo', 'physloc', 'accessrestrict', 'accruals', 'altformavail', 'appraisal',
            'arrangement', 'bibliography', 'bioghist', 'custodhist', 'fileplan', 'note', 'odd',
            'originalsloc', 'otherfindaid', 'phystech', 'prefercite', 'processinfo',
            'relatedmaterial', 'scopecontent', 'separatedmaterial', 'userestrict', 'materialspec'
        ]

        # First, handle DID-scoped notes
        if did is not None:
            for field in ('abstract', 'physloc', 'materialspec', 'note'):
                el = did.find(f'ead:{field}', namespaces=ns)
                if el is not None:
                    paras = self._extract_note_paragraphs(el, ns)
                    if paras:
                        setattr(record, field, paras)
                    # heading from head element if present
                    head = el.find('ead:head', namespaces=ns)
                    if head is not None:
                        setattr(record, f"{field}_heading", self._text_of(head))

        # Then handle top-level/child note elements under the component (not in DID)
        for field in NOTE_FIELDS:
            # skip ones already handled in DID above
            if field in ('abstract', 'physloc', 'materialspec', 'note'):
                continue
            els = elem.findall(f'ead:{field}', namespaces=ns)
            collected = []
            for el in els:
                # get heading if present (use first head)
                head = el.find('ead:head', namespaces=ns)
                if head is not None and not getattr(record, f"{field}_heading", None):
                    setattr(record, f"{field}_heading", self._text_of(head))
                paras = self._extract_note_paragraphs(el, ns)
                collected.extend(paras)
            if collected:
                setattr(record, field, collected)

    def _parse_origination(self, did_el, ns):
        """Parse origination elements from a DID element to create Agent objects.
        
        Looks for <origination> elements and creates Agent objects with agent_type="creator".
        Each immediate child element of <origination> becomes a separate Agent.
        """
        creators = []
        if did_el is None:
            return creators
        for orig in did_el.findall("ead:origination", namespaces=ns):
            # For each immediate child element of origination, create an Agent
            for child in orig:
                name = self._text_of(child)
                if name:
                    creators.append(Agent(name=name, agent_type="creator"))
        
        return creators

    def _parse_controlaccess(self, elem, ns, record):
        """Parse controlaccess elements from an archival component.
        
        Extracts agents (corpname, famname, persname, name), subjects, genreform, and geogname.
        Creates Agent objects for name elements with appropriate agent_type.
        Adds subjects, genreform, and places to the corresponding record lists.
        """
        if elem is None:
            return
        
        controlaccess = elem.find("ead:controlaccess", namespaces=ns)
        if controlaccess is None:
            return
        
        # Parse agents from corpname, famname, persname, and name elements
        agent_mapping = {
            'corpname': 'corporate_entity',
            'famname': 'family',
            'persname': 'person',
            'name': 'person'
        }
        
        for element_name, agent_type in agent_mapping.items():
            for el in controlaccess.findall(f"ead:{element_name}", namespaces=ns):
                name = self._text_of(el)
                if name:
                    record.agents.append(Agent(name=name, agent_type=agent_type))
        
        # Parse subjects
        for subject_el in controlaccess.findall("ead:subject", namespaces=ns):
            subject_text = self._text_of(subject_el)
            if subject_text:
                record.subjects.append(subject_text)
        
        # Parse genreform
        for genreform_el in controlaccess.findall("ead:genreform", namespaces=ns):
            genreform_text = self._text_of(genreform_el)
            if genreform_text:
                record.genreform.append(genreform_text)
        
        # Parse geogname (geographic names) and add to places
        for geogname_el in controlaccess.findall("ead:geogname", namespaces=ns):
            geogname_text = self._text_of(geogname_el)
            if geogname_text:
                record.places.append(geogname_text)

    def _parse_containers(self, elem, did, ns, record):
        """Parse <container> elements and attach a single Container object per component.
        Handles <container> under <did> and<container> directly under the component element.

        Sketchy Rules for determining top and sub containers:
        - If a container has @parent, it is a sub_container; the other is top_container.
        - If no @parent and multiple containers:
            * types 'file' or 'folder' -> sub_container
            * type 'box' -> top_container
            * types are case-insensitive
        - Indicators come from the element text.
        """
        containers = []
        if did is not None:
            containers.extend(did.findall("ead:container", namespaces=ns))
        containers.extend(elem.findall("ead:container", namespaces=ns))

        if not containers:
            return

        # Normalize types and collect
        def _ctype(c):
            t = c.get("type")
            return t.lower() if t else None
        top_el = None
        sub_el = None

        # Prefer parent attribute to identify sub container
        for c in containers:
            if c.get("parent") and sub_el is None:
                sub_el = c
            elif not c.get("parent") and top_el is None:
                top_el = c

        # If still ambiguous or none found, use type heuristics
        if top_el is None or (len(containers) > 1 and sub_el is None):
            for c in containers:
                ct = _ctype(c) or ""
                if top_el is None and ct == "box":
                    top_el = c
                if sub_el is None and ct in ("folder", "file"):
                    sub_el = c

        # Fallback: assign first as top, second as sub when multiple
        if top_el is None and containers:
            top_el = containers[0]
        if sub_el is None and len(containers) > 1:
            # pick the next different element than top
            for c in containers:
                if c is not top_el:
                    sub_el = c
                    break

        # Build Container model
        cont = Container()
        if top_el is not None:
            cont.top_container = _ctype(top_el)
            cont.top_container_indicator = self._text_of(top_el)
        if sub_el is not None:
            cont.sub_container = _ctype(sub_el)
            cont.sub_container_indicator = self._text_of(sub_el)

        # Only append if at least one indicator/type present
        if any([cont.top_container, cont.top_container_indicator, cont.sub_container, cont.sub_container_indicator]):
            record.containers.append(cont)

    def _parse_daos(self, elem, did, ns, record):
        """Parse <dao> elements to DigitalObject models.

        Identifier: @href or @xlink:href
        Label: text from <daodesc> (including <p> and others); fallback to @title
        Action: @show or @xlink:show
        Type: @type if present
        """
        dao_elements = []
        if did is not None:
            dao_elements.extend(did.findall('ead:dao', namespaces=ns))
        dao_elements.extend(elem.findall('ead:dao', namespaces=ns))

        for dao_ul in dao_elements:
            href = dao_ul.get('href') or dao_ul.get('{http://www.w3.org/1999/xlink}href')
            if not href:
                # skip invalid DAO without identifier
                continue
            label = None
            # Simplest: join all text inside daodesc (including nested <p>, etc.)
            dd = dao_ul.find('ead:daodesc', namespaces=ns)
            if dd is not None:
                label = self._text_of(dd)
            if not label:
                label = dao_ul.get('title') or dao_ul.get('{http://www.w3.org/1999/xlink}title')

            action = dao_ul.get('show') or dao_ul.get('{http://www.w3.org/1999/xlink}show')
            dtype = dao_ul.get('type')

            dao = DigitalObject(identifier=href)
            if label:
                dao.label = label
            if action:
                dao.action = action
            if dtype:
                dao.type = dtype

            record.digital_objects.append(dao)

    def _text_of(self, el):
        """Extract text content from element."""
        if el is None:
            return None
        return " ".join(el.itertext()).strip()

    def _parse_dates(self, did_el, ns):
        """Parse unitdate elements from a DID element."""
        dates = []
        if did_el is None:
            return dates
        
        for ud in did_el.findall("ead:unitdate", namespaces=ns):
            expr = self._text_of(ud)
            normal = ud.get("normal")
            date_type = ud.get("type")
            begin = None
            end = None
            if normal and "/" in normal:
                parts = normal.split("/")
                if len(parts) >= 1:
                    begin = parts[0]
                if len(parts) >= 2:
                    end = parts[1]
            d = Date(expression=expr or "", begin=begin, end=end, date_type=date_type)
            dates.append(d)
        return dates

    def _parse_extents(self, did_el, ns):
        """Parse extent elements from a DID element."""
        exts = []
        if did_el is None:
            return exts
        
        # First, try explicit <extent> elements under physdesc
        for ext_el in did_el.findall("ead:physdesc/ead:extent", namespaces=ns):
            extent_text = self._text_of(ext_el) or ""
            if not " " in extent_text:
                number = extent_text
                unit = ""
            else:
                number, unit = extent_text.split(" ", 1)
            exts.append(Extent(number=number, unit=unit))
        
        # If no explicit <extent> elements found, fall back to text content of physdesc
        if not exts:
            for phys in did_el.findall("ead:physdesc", namespaces=ns):
                txt = self._text_of(phys) or ""
                # Skip if empty or whitespace
                if not txt.strip():
                    continue
                # The physdesc text may contain multiple pieces; pick the first reasonable token
                if " " in txt:
                    number, unit = txt.split(" ", 1)
                else:
                    number, unit = txt, ""
                exts.append(Extent(number=number.strip(), unit=unit.strip()))
        return exts

    def _parse_languages(self, did_el, ns):
        """Parse language elements from a DID element.

        Looks for `<langmaterial>` elements under the DID and returns their text.
        """
        languages = []
        if did_el is None:
            return languages

        # EAD commonly places languages under <langmaterial><language> elements
        for langmat in did_el.findall("ead:langmaterial", namespaces=ns):
            # Some EADs put <language> children; use the text of langmaterial itself
            lang_text = self._text_of(langmat)
            if lang_text:
                # split if multiple languages appear concatenated by commas
                parts = [p.strip() for p in lang_text.split(',') if p.strip()]
                for p in parts:
                    # remove trailing punctuation/newline characters
                    clean = p.strip(" \n\r\t.,;:")
                    if clean:
                        languages.append(clean)

        # Also look for direct <language> children of DID (less common)
        for lang_el in did_el.findall("ead:language", namespaces=ns):
            lt = self._text_of(lang_el)
            if lt:
                clean = lt.strip(" \n\r\t.,;:")
                if clean:
                    languages.append(clean)

        return languages

    def _normalize_ead_tags(self, text):
        """Convert EAD formatting tags to HTML equivalents.

        Converts:
          <emph render="italic"> or <emph> -> <i>
          <emph render="bold"> -> <b>
          <emph render="underline"> -> <u>
          <title> -> <i>
          <ref> -> <a> (preserve href/xlink:href if present)
        """
        if not text:
            return text

        # Replace <emph render="italic"> and plain <emph> with <i>
        text = re.sub(r'<emph\s+render="italic">', '<i>', text, flags=re.IGNORECASE)
        text = re.sub(r'<emph>', '<i>', text, flags=re.IGNORECASE)
        text = re.sub(r'</emph>', '</i>', text, flags=re.IGNORECASE)

        # Replace <emph render="bold"> with <b>
        text = re.sub(r'<emph\s+render="bold">', '<b>', text, flags=re.IGNORECASE)

        # Replace <emph render="underline"> with <u>
        text = re.sub(r'<emph\s+render="underline">', '<u>', text, flags=re.IGNORECASE)

        # Replace <title> with <i> (archival titles typically italicized)
        text = re.sub(r'<title>', '<i>', text, flags=re.IGNORECASE)
        text = re.sub(r'</title>', '</i>', text, flags=re.IGNORECASE)

        # Replace <ref> with <a> (preserve href or xlink:href if present)
        text = re.sub(r'<ref\s+xlink:href="([^"]*)">', r'<a href="\1">', text, flags=re.IGNORECASE)
        text = re.sub(r'<ref\s+linktype="([^"]*)">', r'<a>', text, flags=re.IGNORECASE)
        text = re.sub(r'<ref>', '<a>', text, flags=re.IGNORECASE)
        text = re.sub(r'</ref>', '</a>', text, flags=re.IGNORECASE)

        return text
