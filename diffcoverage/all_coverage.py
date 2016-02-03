#!/usr/bin/env python
# coding=utf-8
"""Performs all coverage"""
from __future__ import print_function
from optparse import OptionParser
from pkg_resources import load_entry_point
import subprocess
import sys

from coverage import coverage

from diff_coverage import diff_coverage
import settings


CREATE_XML_REPORT = True
CREATE_HTML_REPORT = True


def execute_nosetests():
    """Execute nosetests"""
    try:
        load_entry_point('nose', 'console_scripts', 'nosetests')()
    except SystemExit:
        pass


def measure_test_coverage():
    """Measure the test coverage from executing nosetests"""
    coverage_obj = coverage(settings.COVERAGE_PATH)
    coverage_obj.start()
    execute_nosetests()
    coverage_obj.stop()
    return coverage_obj


def main():
    opt = OptionParser(usage='usage: %prog [options...]')
    opt.add_option('--no-xml', dest='no_xml', default=not CREATE_XML_REPORT,
                   action='store_true', help='Don\'t generate XML coverage report')
    opt.add_option('--no-html', dest='no_html', default=not CREATE_HTML_REPORT,
                   action='store_true', help='Don\'t generate HTML coverage report')
    (options, args) = opt.parse_args()
    if args:
        print('Does not take arguments')
        print()
        opt.print_help()
        sys.exit(1)

    coverage_obj = measure_test_coverage()
    print()
    print('Saving coverage report...')
    coverage_obj.save()
    if not options.no_xml:
        print('Saving Cobertura (XML) report...')
        coverage_obj.xml_report(outfile=settings.XML_REPORT_FILE)

    if not options.no_html:
        print('Saving HTML report...')
        coverage_obj.html_report(directory=settings.HTML_REPORT_DIR)

    print('Creating diff patch...')
    subprocess.call('git diff %s > /tmp/diffpatch' % settings.COMPARE_WITH_BRANCH,
                    shell=True)
    print('Creating diff coverage report...')
    diff_coverage('/tmp/diffpatch')


if __name__ == '__main__':
    main()

