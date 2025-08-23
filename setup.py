from setuptools import setup, find_packages
from pathlib import Path

here = Path(__file__).parent

setup(
    name="paopao-cli",
    version="0.1.0",
    packages=find_packages(include=["paopao_cli", "paopao_cli.*"]),
    include_package_data=True,
    entry_points={"console_scripts": ["ppc=paopao_cli.main:main"]},
    install_requires=["rich>=13.0.0", "rich-argparse"],
    author="PaoPaoDev",
    description="🥭 PaoPao CLI Framework - Plugin-based command system",
    long_description=(here / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/PaoPaoDev/paopao-cli",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
