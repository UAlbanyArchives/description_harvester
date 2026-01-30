import yaml
from pathlib import Path

class Config:
    DEFAULTS = {
        "cache_expiration": 86400,
        "cache_dir": str(Path.home() / ".description_harvester/cache"),
        "metadata": {},
        "last_query": 0,
        "solr_core": "arclight",
        "solr_url": "https://solr.example.com:8984/solr",
        "online_content_label": "Online access",
        "component_id_separator": "_",
    }

    def __init__(self):
        config_path = Path.home() / ".description_harvester/config.yml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Apply defaults, then override
        for k, v in {**self.DEFAULTS, **config}.items():
            if v is None and k not in config:
                v = self.DEFAULTS.get(k)
            setattr(self, k, v)


    def read_repositories(slug, verbose=False):
        """
        Reads the `repositories.yml` configuration file from the user's home directory
        and retrieves the `name` of a repository based on the provided slug.

        Parameters:
        -----------
        slug : str
            The case-insensitive slug to look for within the repository keys in the YAML file.

        Returns:
        --------
        str
            The name of the repository matching the given slug, if found.

        """
        if verbose:
            print(f"Reading repositories configuration using slug: {slug}")
        repositories_path = Path.home() / ".description_harvester/repositories.yml"

        if not repositories_path.exists():
            raise FileNotFoundError(f"The repositories configuration file {repositories_path} does not exist.")

        try:
            with open(repositories_path, "r", encoding='utf-8') as f:
                repositories = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file: {e}")
        
        slug = slug.strip().lower()
        for key, repo_data in repositories.items():
            if key.lower() == slug:
                repo_name = repo_data.get('name', None)
                if verbose:
                    print(f"Setting repository name: {repo_name}")
                return repo_name

        raise ValueError(f"No repository found for the specified slug: '{slug}'")

