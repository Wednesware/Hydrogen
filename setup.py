from setuptools import setup, find_packages

setup(
    name="wwn",
    version="26.25",
    py_modules=[],
    entry_points={
        "console_scripts": [
            "n2=nitrogen:main",
        ],
    },
    author="Wednesware",
    author_email="wednesware@gmail.com",
    description="Easy, ultra-lightweight installer for Wednesware publications.",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/wednesware/nitrogen",
    packages=find_packages(),
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    license="MIT"
)
