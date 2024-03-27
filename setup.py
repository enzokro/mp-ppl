from setuptools import setup, find_packages

setup(
    name="see_mp",
    version="0.1.0",
    description="Counting people and cats.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="cck",
    author_email="christopher.kroenke@gmail.com",
    url="https://github.com/yourusername/mp-ppl",
    license="Apache 2.0",
    packages=find_packages(),
    install_requires=[
    ],
    extras_require={
        "dev": [
        ],
    },
    entry_points={
        "console_scripts": [
            "see=find",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.9",
)
