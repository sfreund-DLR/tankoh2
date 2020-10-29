"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

import os, sys

from setuptools import setup, find_packages
from distutils import log

log.set_threshold(log.INFO)

here = os.path.abspath(os.path.dirname(__file__))
for sourceDir in ['src', 'test']:
    os.environ['PYTHONPATH'] = os.path.join(here, sourceDir) + ';' + os.environ.get('PYTHONPATH', '')
    sys.path.insert(0, os.path.join(here, sourceDir))

# ===============================================================================
# get project information from __about__.py
# ===============================================================================
projectName = [name for name in os.listdir(os.path.join(here, "src"))
               if os.path.isdir(os.path.join(here, "src", name)) and '.egg-info' not in name][0]
about = {}
with open(os.path.join(here, "src", projectName, "__about__.py")) as f:
    exec(f.read(), about)

version = about['__version__']
description = about['__description__']
author = about['__author__']
author_email = about['__email__']
programLicense = about['__license__']
url = about['__url__']
keywords = about['__keywords__']

with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()


# ===============================================================================
# start setup process
# ===============================================================================
def main():
    setup(
        name=projectName,
        # Versions should comply with PEP 440:
        # https://www.python.org/dev/peps/pep-0440/
        version=version,
        description=description,
        long_description=long_description,
        long_description_content_type='text/markdown',
        # long_description_content_type='text/x-rst',
        # The project's main homepage.
        url=url,
        # Author details
        author=author,
        author_email=author_email,

        # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
        classifiers=[
            # How mature is this project? Common values are
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            'Development Status :: 4 - Beta',

            # Indicate who your project is intended for
            'Intended Audience :: Developers',
            'Topic :: Scientific/Engineering :: Mathematics',

            # Pick your license as you wish (should match "license" above)
            programLicense,

            # Specify the Python versions you support here. In particular, ensure
            # that you indicate whether you support Python 2, Python 3 or both.
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
        ],

        # What does your project relate to?
        keywords=keywords,

        # You can just specify the packages manually here if your project is
        # simple. Or you can use find_packages().
        packages=find_packages('src'),
        package_dir={'': 'src'},

        # Alternatively, if you want to distribute just a my_module.py, uncomment
        # this:
        #   py_modules=["my_module"],

        # Specify which Python versions you support. In contrast to the
        # 'Programming Language' classifiers above, 'pip install' will check this
        # and refuse to install the project if the version does not match. If you
        # do not support Python 2, you can simplify this to '>=3.5' or similar, see
        # https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires
        python_requires='>=3',

        # List run-time dependencies here.  These will be installed by pip when
        # your project is installed. For an analysis of "install_requires" vs pip's
        # requirements files see:
        # https://packaging.python.org/en/latest/requirements.html
        install_requires=['numpy', 'scipy', 'pandas'],

        # List additional groups of dependencies here (e.g. development
        # dependencies). You can install these using the following syntax,
        # for example:
        # $ pip install -e .[dev,test]
        # extras_require={
        # },

        # If there are data files included in your packages that need to be
        # installed, specify them here. 
        package_data={
            # If any package contains *.txt or *.rst files, include them:
            # "": ["*.txt", "*.rst"],
            # And include any *.msg files found in the "hello" package, too:
            # "hello": ["*.msg"],
        },

        # Although 'package_data' is the preferred approach, in some case you may
        # need to place data files outside of your packages. See:
        # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
        # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
        data_files=[
            # ('doc', ['doc/Masterarbeit_kriging.pdf']),
        ],

        # To provide executable scripts, use entry points in preference to the
        # "scripts" keyword. Entry points provide cross-platform support and allow
        # pip to create the appropriate form of executable for the target platform.
        # entry_points={
        #    'console_scripts': [
        #        'sample=sample:main',
        #    ],
        # },

        setup_requires=[  # 'pytest', 'pytest-cov', 'coverage', 'pytest-runner',
        ],
        tests_require=[  # 'pylint', 'sphinx', 'sphinxcontrib-bibtex'
        ],

        # add custom classes and register them as aliases (see setup.cfg)
        cmdclass={

        },
    )


if __name__ == '__main__':
    main()
