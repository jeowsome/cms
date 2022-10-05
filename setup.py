from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in church_management/__init__.py
from church_management import __version__ as version

setup(
	name="church_management",
	version=version,
	description="Manage Church Collections and Membership",
	author="Jeomar Bayoguina",
	author_email="jeomar.bayoguina@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
