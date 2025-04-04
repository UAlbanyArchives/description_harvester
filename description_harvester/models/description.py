from jsonmodels import models, fields, errors, validators

"""
This is designed to be an as-simple-as-possible data model
for public-facing archival description that is neccessary
for an access and discovery system
"""

class Date(models.Base):
    expression = fields.StringField(required=True)
    # begin *should* be required but ASpace doesn't actually require it
    begin = fields.StringField()
    end = fields.StringField()
    date_type = fields.StringField()

class Extent(models.Base):
    number = fields.StringField(required=True)
    unit = fields.StringField(required=True)

class Agent(models.Base):
    # Should be built out more but I don't have access to good agent data
    name = fields.StringField(required=True)
    agent_type = fields.StringField(required=True)

class Container(models.Base):
    top_container = fields.StringField()
    top_container_indicator = fields.StringField()
    sub_container = fields.StringField()
    sub_container_indicator = fields.StringField()
    sub_sub_container = fields.StringField()
    sub_sub_container_indicator = fields.StringField()

class DigitalObject(models.Base):
    identifier = fields.StringField(required=True)
    label = fields.StringField()
    action = fields.StringField()
    type = fields.StringField()
    access_condition = fields.StringField()
    thumbnail_href = fields.StringField()
    rights_statement = fields.StringField()
    metadata = fields.ListField(dict)

class Component(models.Base):
    id = fields.StringField(required=True)
    collection_id = fields.StringField(required=True)
    # title should really be required as it is in DACS, but its not in ASpace/EAD or the existing ArcLight indexer.
    title = fields.StringField()
    title_filing_ssi = fields.StringField()
    repository = fields.StringField(required=True)
    level = fields.StringField(required=True)
    collection_name = fields.StringField(required=True)
    dates = fields.ListField(Date)
    extents = fields.ListField(Extent)
    languages = fields.ListField(str)
    creators = fields.ListField(Agent)
    agents = fields.ListField(Agent)
    subjects = fields.ListField(str)
    genreform = fields.ListField(str)
    places = fields.ListField(str)

    # notes
    abstract = fields.ListField(str)
    abstract_heading = fields.StringField()
    accessrestrict = fields.ListField(str)
    accessrestrict_heading = fields.StringField()
    scopecontent = fields.ListField(str)
    scopecontent_heading = fields.StringField()
    acqinfo = fields.ListField(str)
    acqinfo_heading = fields.StringField()
    accruals = fields.ListField(str)
    accruals_heading = fields.StringField()
    altformavail = fields.ListField(str)
    altformavail_heading = fields.StringField()
    appraisal = fields.ListField(str)
    appraisal_heading = fields.StringField()
    arrangement = fields.ListField(str)
    arrangement_heading = fields.StringField()
    bibliography = fields.ListField(str)
    bibliography_heading = fields.StringField()
    bioghist = fields.ListField(str)
    bioghist_heading = fields.StringField()
    custodhist = fields.ListField(str)
    custodhist_heading = fields.StringField()
    fileplan = fields.ListField(str)
    fileplan_heading = fields.StringField()
    note = fields.ListField(str)
    note_heading = fields.StringField()
    odd = fields.ListField(str)
    odd_heading = fields.StringField()
    originalsloc = fields.ListField(str)
    originalsloc_heading = fields.StringField()
    otherfindaid = fields.ListField(str)
    otherfindaid_heading = fields.StringField()
    phystech = fields.ListField(str)
    phystech_heading = fields.StringField()
    prefercite = fields.ListField(str)
    prefercite_heading = fields.StringField()
    processinfo = fields.ListField(str)
    processinfo_heading = fields.StringField()
    relatedmaterial = fields.ListField(str)
    relatedmaterial_heading = fields.StringField()
    separatedmaterial = fields.ListField(str)
    separatedmaterial_heading = fields.StringField()
    userestrict = fields.ListField(str)
    userestrict_heading = fields.StringField()
    materialspec = fields.ListField(str)
    materialspec_heading = fields.StringField()
    physloc = fields.ListField(str)
    physloc_heading = fields.StringField()
    dimensions = fields.ListField(str)
    dimensions_heading = fields.StringField()
    


    containers = fields.ListField(Container)
    digital_objects = fields.ListField(DigitalObject)
    components = fields.ListField()
