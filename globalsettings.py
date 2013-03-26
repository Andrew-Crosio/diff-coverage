# coding=utf-8
"""Settings file"""
import re


COVERAGE_PATH = '.coverage'
IGNORED_NAME_PORTIONS = ['test', re.compile('docs.*/'), re.compile(r'.gitignore$')]
OUTPUT_COVERAGE_DOC = 'diff_coverage_html'


try:
    execfile('settings')
except IOError:
    pass
