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
    
    scripts=[os.path.join('bin', x) for x in os.listdir('bin') if not x.startswith('.')],

    entry_points={
        'console_scripts': '''

            mmarchive-ingest = mmsystems.archive:ingest_main
            mmbackup-one = mmsystems.backup.one:main
            mmfileservers-status = mmsystems.fileservers.status:main
            mmindex-create = mmsystems.index.create:main
            mmindex-dedup = mmsystems.index.dedup:main
            mmindex-diff = mmsystems.index.diff:main
            mmmetrics-client = mmsystems.metrics.client:main
            mmmetrics-influx-query = mmsystems.metrics.influx:main_query
            mmmetrics-influx-write = mmsystems.metrics.influx:main_write
            
            mminstall-maya = mmsystems.install.apps.maya:main
            
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
