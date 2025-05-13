from setuptools import setup

setup(
    name="rgit",
    version="1.0",
    packages=["src"], # the src dir
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "rgit=src.cli:main" # if command rgit, call main() inside cli.py inside src/
        ]
    }
)
