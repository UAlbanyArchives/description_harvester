# /usr/bin/env python3
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="description_indexer",
    version="0.0.1",
    author="Gregory Wiedeman",
    author_email="gwiedeman@albany.edu",
    description="A tool for working with archival description for public access.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/UAlbanyArchives/description_indexer",
    packages=setuptools.find_namespace_packages(exclude=("tests")),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["to-arclight=description_indexer:index"]},
    install_requires=[
        "archivessnake",
        "black>=22.1.0,<23",
        "iso-639",
        "pysolr",
        "pyyaml"
        "requests"
    ],
    python_requires=">=3.7",
)
