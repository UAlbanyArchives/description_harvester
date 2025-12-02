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
        if "id" in elem.attrib:
            record.id = elem.get("id")
        else:
            uid_el = elem.find("ead:did/ead:unitid", namespaces=ns)
            record.id = self._text_of(uid_el)

        record.collection_id = collection_id or ""
        record.repository = repository or ""
        record.collection_name = collection_name
        record.title = title
        record.level = elem.get("level") or (did.findtext("ead:level", namespaces=ns) if did is not None else "unknown")

        # Parse dates and extents from the element's DID
        if did is not None:
            record.dates = self._parse_dates(did, ns)
            record.extents = self._parse_extents(did, ns)
        
        # Parse child components recursively
        if elem is not None:
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
        
        return record

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
