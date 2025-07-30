from setuptools import setup, find_packages

setup(
    name="public_transport_datasets",
    version="0.1.51",
    packages=find_packages(),
    install_requires=[
        "requests",
        "gtfs-realtime-bindings",
        "jsonpath-ng",
        "duckdb",
        "geopandas",
        "shapely",
    ],
    include_package_data=True,
    package_data={
        "public_transport_datasets": ["providers/GTFS/*.json"],
    },
    description="A Python package for public transport datasets for multiple cities.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Max Mazzeschi",
    author_email="max.mazzeschi@gmail.com",
    url="https://github.com/maxmazzeschi/public-transport-datasets",
    license="Apache-2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
