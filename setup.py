import io
import os
from setuptools import setup

description = 'Version-bump your software with a single command!'

# Import the README and use it as the long-description.
# This requires 'README.md' to be present in MANIFEST.in.
here = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

setup(
    name='bump2version',
    version='0.5.11',
    url='https://github.com/c4urself/bump2version',
    author='Christian Verkerk',
    author_email='christianverkerk@ymail.com',
    license='MIT',
    packages=['bumpversion'],
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    entry_points={
        'console_scripts': [
            'bumpversion = bumpversion.cli:main',
            'bump2version = bumpversion.cli:main',
        ]
    },
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
