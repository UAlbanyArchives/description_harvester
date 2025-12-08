from os import listdir, makedirs
from os.path import basename, dirname, exists, isfile, join
import importlib.util

from abc import ABC, abstractmethod

class Plugin(ABC):
    """Base class and registry for customizing description harvesting behavior.
    
    Plugins allow you to add institution-specific logic for:
    - Customizing repository names based on collection data
    - Enriching digital objects with data from external sources (e.g., IIIF manifests)
    
    How to create a plugin:
    1. Copy description_harvester/plugins/default.py to ~/.description_harvester/
    2. Rename the class (e.g., MyInstitutionPlugin) and update plugin_name
    3. Implement custom_repository() and/or update_dao() methods
    4. The plugin will be automatically discovered and loaded
    
    Plugins are loaded from (in order):
    1. Built-in plugins in the package
    2. ~/.description_harvester/ directory
    3. Custom directory set via DESCRIPTION_HARVESTER_PLUGIN_DIR environment variable
    
    All plugin classes must have a 'plugin_name' class variable that uniquely identifies them.
    """

    # Registry of plugins, key = cls.plugin_name, value = cls
    registry = {}

    def __init_subclass__(cls, **kwargs):
        """Enforce plugin descriptive attributes on subclasses, register them"""
        plugin_attrs = ["plugin_name"]
        for attr in plugin_attrs:
            if not hasattr(cls, attr):
                raise RuntimeError("Plugin subclass must have `" + attr + "` attribute")

        super().__init_subclass__(**kwargs)
        __class__.registry[cls.plugin_name] = cls


    def custom_repository(self, resource):
        """Override to customize repository names based on collection data.
        
        Args:
            resource (dict): ArchivesSpace resource API object
            
        Returns:
            str or None: Custom repository name, or None to use default
        """
        pass

    def update_dao(self, dao):
        """Override to enrich digital objects with external data.
        
        Args:
            dao (DigitalObject): Digital object to enrich
            
        Returns:
            DigitalObject: Updated digital object with additional metadata
        """
        pass


def import_plugins(additional_dirs=None):
    if not additional_dirs:
        additional_dirs = []

    dirs = [join(dirname(__file__), "plugins"), *additional_dirs]


    for plugin_dir in dirs:
        if not exists(plugin_dir):
            continue
        for filename in listdir(plugin_dir):
            module = basename(filename)[:-3]
            full_path = join(plugin_dir, filename)
            # skip if not a normal, non underscored file ending in .py
            if module.startswith("_") or not isfile(full_path) or filename[-3:] != ".py":
                continue
            spec = importlib.util.spec_from_file_location(module, full_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
