# coding=utf-8
"""Settings file"""
import re


COVERAGE_PATH = '.coverage'
IGNORED_NAME_PORTIONS = ['test', re.compile('docs.*/'), re.compile(r'.gitignore$')]
OUTPUT_COVERAGE_DOC = 'diff_coverage_html'
COMPARE_WITH_BRANCH = 'master'
XML_REPORT_FILE = 'coverage.xml'
HTML_REPORT_DIR = 'coverage_html'


try:
    execfile('globalsettings')
except IOError:
    pass
