from setuptools import setup, find_packages

setup(
    name="wwn",
    version="26.22",
    py_modules=[],
    entry_points={
        "console_scripts": [
            "n2=nitrogen:main",
        ],
    },
    author="Wednesware",
    author_email="wednesware@gmail.com",
    description="Easy, ultra-light-weight installer for Wednesware publications. Built for single-use and multi-use installations.",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/wednesware/nitrogen",
    packages=find_packages(),
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
)
