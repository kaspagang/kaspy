#from kaspy import __version__ as VERSION, __name__ as NAME
import setuptools
from kaspy import __name__, __version__
 
with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt","r") as f:
    dependencies = f.read().splitlines()

setuptools.setup(
    name=__name__,
    version= __version__,
    author="D-Stacks",
    description="Python implementation of a kaspa grpc client",
    long_description = long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    license= 'GPL-3.0 License',
    install_requires= dependencies,
    url= 'https://github.com/kaspagang/kaspy',
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.8', #only version tested
)
