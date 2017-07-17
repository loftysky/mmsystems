import os

from setuptools import setup, find_packages

setup(
    name='mmsystems',
    version='0.1.dev0',
    description="Lofty Sky's general systems tools.",
    url='',
    
    packages=find_packages(exclude=['build*', 'tests*']),
    include_package_data=True,
    
    author='Mike Boers',
    author_email='mikeb@loftysky.com',
    license='BSD-3',
    
    scripts=[os.path.join('bin', x) for x in os.listdir('bin')],

    entry_points={
        'console_scripts': '''
            mmsystems-fileservers = mmsystems.fileservers:main
            mmarchive-ingest = mmsystems.archive:ingest_main
        ''',
    },

    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    
)
