import os
import sys
from setuptools import setup, find_packages

if sys.argv[-1] == 'publish':
    # Publish to PyPi.
    os.system('python setup.py sdist upload')
    sys.exit()

long_description = 'Information and documentation at https://github.com/Andrew-Crosio/diff-coverage'

setup(name='diffcoverage',
      version='1.0',
      author='Some guy',
      author_email='some@guy.com',
      url='https://github.com/Andrew-Crosio/diff-coverage',
      license='Unlicense',
      description='Get a difference in coverage with a patch.',
      long_description=long_description,
      packages=find_packages(),
      include_package_data=True,
      platforms=['any'],
      classifiers=[
          'Topic :: Internet',
          'Natural Language :: English',
          'Development Status :: 1.0 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: Freely Distributable',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
      ],
      entry_points={
          'console_scripts': [
              'diffcoverage = diffcoverage.diff_coverage:main',
          ],
      },
      install_requires=[
          'coverage==3.7'
      ],
      tests_require=[],
)
