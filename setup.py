import io
from setuptools import setup

description = 'Version-bump your software with a single command!'

with io.open('README.rst', encoding="utf-8") as f:
    long_description = f.read()


setup(
    name='bump2version',
    version='0.5.9-dev',
    url='https://github.com/c4urself/bump2version',
    author='Christian Verkerk',
    author_email='christianverkerk@ymail.com',
    license='MIT',
    packages=['bumpversion'],
    description=description,
    long_description=long_description,
    entry_points={
        'console_scripts': [
            'bumpversion = bumpversion:main',
            'bump2version = bumpversion:main',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
