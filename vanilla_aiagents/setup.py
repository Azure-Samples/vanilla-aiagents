from setuptools import setup, find_packages
import sys

# Extract version from arguments named "version"
if "--version" in sys.argv:
    version_index = sys.argv.index("--version") + 1
    version = sys.argv[version_index]
    # Remove the --version argument and its value from sys.argv
    sys.argv.pop(version_index)
    sys.argv.pop(version_index - 1)
else:
    raise ValueError("Version not provided")


setup(
    name='vanilla_aiagents',
    version=version,
    packages=find_packages(),
    install_requires=[
        "openai",
        "pydantic",
        "azure-identity",
    ],
    extras_require={
        'remote': [
            'fastapi',
            'uvicorn',
            'starlette_gzip_request',
            'grpcio-tools',
            'grpcio-reflection'
        ],
        'extras': [
            'llmlingua'
        ]
    },
    entry_points={
        'console_scripts': [
        ],
    },
    author='Riccardo Chiodaroli',
    author_email='ricchi@microsoft.com',
    description='Sample package demonstrating how to create a simple agenting application without using any specific framework',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/azure-samples/genai-vanilla-agents',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.11',
)