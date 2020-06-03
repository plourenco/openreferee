import os
import re

from setuptools import find_packages, setup


def read_requirements_file(fname):
    with open(fname, "r") as f:
        return [
            dep.strip()
            for dep in f.readlines()
            if not (dep.startswith("-") or "://" in dep)
        ]


def get_requirements():
    return read_requirements_file(
        os.path.join(os.path.dirname(__file__), "requirements.txt")
    )


with open("openreferee_server/__init__.py", encoding="utf8") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setup(
    name="openreferee-reference-server",
    version=version,
    url="https://github.com/indico/openreferee",
    license="MIT",
    author="Indico Team",
    author_email="indico-team@cern.ch",
    description="OpenReferee Reference Server",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.7",
    install_requires=get_requirements(),
)
