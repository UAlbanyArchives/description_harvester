from .model_utils import filter_empty_fields
from jsonmodels import models, fields, errors, validators

"""
This is a data model for the JSON that Arclight expects 
to be POSTed to Solr.
"""

class SolrCollection(models.Base):

    def to_dict(self):
        """
        Convert the model instance to a dictionary with empty fields removed.
        """
        return filter_empty_fields(self.to_struct())

    id = fields.StringField(required=True)
    unitid_ssm = fields.ListField(str)
    unitid_tesim = fields.ListField(str)
    title_ssm = fields.ListField(str)
    title_tesim = fields.ListField(str)
    title_html_tesm = fields.ListField(str)
    title_filing_ssi = fields.StringField()
    ead_ssi = fields.ListField(str)
    total_component_count_is = fields.IntField()
    sort_isi = fields.IntField()

    # this is a list of display dates, i.e. ["1920-1988", "bulk 1956-1976"]
    unitdate_ssm = fields.ListField(str)
    # this is a list of all years
    date_range_isim = fields.ListField(int)
    normalized_date_ssm = fields.ListField(str)
    # We don't need other date fields if we add them as labels withing unidate_ssm
    #unitdate_bulk_ssm = fields.ListField(str)
    #unitdate_inclusive_ssm = fields.ListField(str)
    #unitdate_other_ssim

    component_level_isim = fields.ListField(int)
    level_ssm = fields.ListField(str)
    level_ssim = fields.ListField(str)

    normalized_title_ssm = fields.ListField(str)
    #collection_title_tesim = fields.ListField(str)
    collection_ssim = fields.ListField(str)
    repository_ssm = fields.ListField(str) # really only collection level in v1.4
    repository_ssim = fields.ListField(str)
    
    access_terms_ssm = fields.ListField(str)
    access_subjects_ssim = fields.ListField(str)
    access_subjects_ssm = fields.ListField(str)
    has_online_content_ssim = fields.ListField(str)
    extent_ssm = fields.ListField(str)
    extent_tesim = fields.ListField(str)
    genreform_ssim = fields.ListField(str)

    # note fields
    abstract_heading_ssm = fields.ListField(str)
    abstract_tesim = fields.ListField(str)
    abstract_html_tesm = fields.ListField(str)
    physloc_heading_ssm = fields.ListField(str)
    physloc_tesim = fields.ListField(str)
    physloc_html_tesm = fields.ListField(str)
    processinfo_heading_ssm = fields.ListField(str)
    processinfo_tesim = fields.ListField(str)
    processinfo_html_tesm = fields.ListField(str)
    bioghist_heading_ssm = fields.ListField(str)
    bioghist_tesim = fields.ListField(str)
    bioghist_html_tesm = fields.ListField(str)
    scopecontent_heading_ssm = fields.ListField(str)
    scopecontent_tesim = fields.ListField(str)
    scopecontent_html_tesm = fields.ListField(str)
    arrangement_heading_ssm = fields.ListField(str)
    arrangement_tesim = fields.ListField(str)
    arrangement_html_tesm = fields.ListField(str)
    # This is actually still stored as acqinfo_ssim in v1.4
    acqinfo_ssim = fields.ListField(str)
    #acqinfo_heading_ssm = fields.ListField(str)
    #acqinfo_tesim = fields.ListField(str)
    #acqinfo_html_tesm = fields.ListField(str)
    accessrestrict_heading_ssm = fields.ListField(str)
    accessrestrict_tesim = fields.ListField(str)
    accessrestrict_html_tesm = fields.ListField(str)
    userestrict_heading_ssm = fields.ListField(str)
    userestrict_tesim = fields.ListField(str)
    userestrict_html_tesm = fields.ListField(str)
    prefercite_heading_ssm = fields.ListField(str)
    prefercite_tesim = fields.ListField(str)
    prefercite_html_tesm = fields.ListField(str)
    odd_heading_ssm = fields.ListField(str)
    odd_tesim = fields.ListField(str)
    odd_html_tesm = fields.ListField(str)
    originalsloc_heading_ssm = fields.ListField(str)
    originalsloc_tesim = fields.ListField(str)
    originalsloc_html_tesm = fields.ListField(str)
    altformavail_heading_ssm = fields.ListField(str)
    altformavail_tesim = fields.ListField(str)
    altformavail_html_tesm = fields.ListField(str)
    separatedmaterial_heading_ssm = fields.ListField(str)
    separatedmaterial_tesim = fields.ListField(str)
    separatedmaterial_html_tesm = fields.ListField(str)
    relatedmaterial_heading_ssm = fields.ListField(str)
    relatedmaterial_tesim = fields.ListField(str)
    relatedmaterial_html_tesm = fields.ListField(str)
    custodhist_heading_ssm = fields.ListField(str)
    custodhist_tesim = fields.ListField(str)
    custodhist_html_tesm = fields.ListField(str)
    phystech_heading_ssm = fields.ListField(str)
    phystech_tesim = fields.ListField(str)
    phystech_html_tesm = fields.ListField(str)
    otherfindaid_heading_ssm = fields.ListField(str)
    otherfindaid_tesim = fields.ListField(str)
    otherfindaid_html_tesm = fields.ListField(str)
    accruals_heading_ssm = fields.ListField(str)
    accruals_tesim = fields.ListField(str)
    accruals_html_tesm = fields.ListField(str)
    appraisal_heading_ssm = fields.ListField(str)
    appraisal_tesim = fields.ListField(str)
    appraisal_html_tesm = fields.ListField(str)
    fileplan_heading_ssm = fields.ListField(str)
    fileplan_tesim = fields.ListField(str)
    fileplan_html_tesm = fields.ListField(str)
    materialspec_heading_ssm = fields.ListField(str)
    materialspec_tesim = fields.ListField(str)
    materialspec_html_tesm = fields.ListField(str)
    bibliography_heading_ssm = fields.ListField(str)
    bibliography_tesim = fields.ListField(str)
    bibliography_html_tesm = fields.ListField(str)
    dimensions_heading_ssm = fields.ListField(str)
    dimensions_tesim = fields.ListField(str)
    dimensions_html_tesm = fields.ListField(str)
    note_heading_ssm = fields.ListField(str)
    note_tesim = fields.ListField(str)
    note_html_tesm = fields.ListField(str)


    names_coll_ssim = fields.ListField(str)
    names_ssim = fields.ListField(str)
    corpname_ssim = fields.ListField(str)
    famname_ssim = fields.ListField(str)
    persname_ssim = fields.ListField(str)
    
    creator_ssm = fields.ListField(str)
    creator_ssim = fields.ListField(str)
    creator_sort = fields.StringField()
    creator_corpname_ssim = fields.ListField(str)
    creator_famname_ssim = fields.ListField(str)
    creator_persname_ssim = fields.ListField(str)
    
    language_ssim = fields.ListField(str)
    geogname_ssm = fields.ListField(str)
    geogname_ssim = fields.ListField(str)
    places_ssim = fields.ListField(str)
    
    containers_ssim = fields.ListField(str)
    digital_objects_ssm = fields.ListField(str)
    components = fields.ListField()
    total_component_count_is = fields.IntField()
    online_item_count_is = fields.IntField()

    # I guess collections can have representative DAOs
    href_sim = fields.StringField()
    label_ssm = fields.StringField()
    identifier_sim = fields.StringField()
    is_representative_sim = fields.StringField()
    filename_sim = fields.StringField()
    mime_type_sim = fields.StringField()
    #metadata = fields.ListField(dict)
    thumbnail_href_sim = fields.StringField()
    rights_statement_ssm = fields.StringField()
    #content_ssm = fields.StringField()
    

class SolrComponent(SolrCollection):
    parent_ssim = fields.ListField(str)
    parent_ssi = fields.ListField(str)
    parent_ids_ssim = fields.ListField(str)
    parent_levels_ssm = fields.ListField(str)
    parent_unittitles_ssm = fields.ListField(str)
    parent_unittitles_tesim = fields.ListField(str)
    #collection_creator_ssm = fields.ListField(str)
    child_component_count_isi = fields.ListField(int)
    parent_access_restrict_tesm = fields.ListField(str)
    parent_access_terms_tesm = fields.ListField(str)
    parent_levels_ssm = fields.ListField(str)
    ref_ssm = fields.ListField(str)
    ref_ssi = fields.StringField()
