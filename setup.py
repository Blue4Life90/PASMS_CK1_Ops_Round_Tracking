from setuptools import setup, find_packages

setup(
    name="pasms_ck1_operator_rounds_tracking_draft",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.20.0",
        "pandas>=1.3.0",
        "sqlite3",
        "toml",
    ],
    author="MDGL",
    description="A Streamlit application for tracking operator rounds in industrial facilities",
)