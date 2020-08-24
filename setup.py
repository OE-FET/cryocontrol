from setuptools import setup, find_packages

setup(
    name='cryocontrol',
    version='0.1.0',
    description='Drivers and GUI for cryogenic temperature controllers',
    author='Sam Schott',
    author_email='ss2151@cam.ac.uk',
    url='https://github.com/oe-fet/cryocontrol.git',
    license='MIT',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    package_data={
        'cryocontrol': ['**/*.ui', '**/**/*.ui'],
    },
    entry_points={
        'console_scripts': [
            'cryogui=cryocontrol.gui.main:run'
        ],
    },
    install_requires=[
        'pyvisa',
        'numpy',
        'pyqtgraph>=0.11.0',
        'PyQt5>=5.9',
        'setuptools',
    ],
    zip_safe=False,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
