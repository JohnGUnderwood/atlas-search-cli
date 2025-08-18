from setuptools import setup, find_packages

setup(
    name='atlas-search-cli',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'pymongo',
        'voyageai',
    ],
    entry_points={
        'console_scripts': [
            'atlas-search = atlas_search_cli.main:main',
        ],
    },
)
