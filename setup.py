# /usr/bin/env python3
import os
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

def read_version():
    version_file = os.path.join(os.path.dirname(__file__), 'description_harvester', 'version.py')
    with open(version_file) as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"').strip("'")

setuptools.setup(
    name="description_harvester",
    version=read_version(),
    author="Gregory Wiedeman",
    author_email="gwiedeman@albany.edu",
    description="A tool for working with archival description for public access.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/UAlbanyArchives/description_harvester",
    packages=setuptools.find_namespace_packages(exclude=("tests")),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["harvest=description_harvester:harvest"]},
    install_requires=[
        "archivessnake>=0.9.1,<1",
        "beautifulsoup4>=4.12.0",
        "black>=22.1.0",
        "langcodes==3.5.0,<4",
        "lxml>=5.0.0",
        "pysolr>=3.9.0,<4",
        "pyyaml>=6.0,<7",
        "jsonmodels",
        "requests>=2.28.1,<3"
    ],
    python_requires=">=3.9",
)
