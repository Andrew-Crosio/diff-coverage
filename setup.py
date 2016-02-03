from setuptools import setup
from setuptools import find_packages


setup(
    name='diffcoverage',
    version='1.1',
    author='Andrew Crosio',
    author_email='andrew@andrewcrosio.com',
    url='https://github.com/gxx/diff-coverage',
    license='Unlicensed',
    description='Measure difference in coverage with a difference patch',
    long_description=open('README.md').read(),
    packages=find_packages(),
    package_data={
        'diffcoverage': ['templates/*/*.html']
    },
    include_package_data=True,
    platforms=['any'],
    classifiers=[
      'Topic :: Internet',
      'Natural Language :: English',
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
      'coverage>=3.7'
    ],
    tests_require=[],
)
