from setuptools import setup, find_packages

setup(
    name="devopsify",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.1.7",
        "jinja2>=3.1.3",
        "gitpython>=3.1.41",
    ],
    entry_points={
        "console_scripts": [
            "devopsify=devopsify.main:cli",
        ],
    },
    package_data={
        "devopsify": ["templates/**/*"],
    },
)
