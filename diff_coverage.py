#!/usr/bin/env python
# coding: utf-8
"""
    diff-coverage

    This module will, in a somewhat inflexible way, compare a diff coverage.py
    data to determine whether lines added or modified in the diff, were executed
    during a coverage session.

    requires http://python-patch.googlecode.com/svn/trunk/patch.py
    which is included in this package with attribution
"""
from collections import defaultdict
from optparse import OptionParser
import logging
import os
import sys

import coverage

import patch
import globalsettings

ADDED_LINE = '+'
REMOVED_LINE = '-'
ROOT_PATH = os.getcwd()
COVERAGE_FILE_PATH = os.path.join(ROOT_PATH, globalsettings.COVERAGE_PATH)
coverage_html_dir = os.path.join(os.getcwd(), globalsettings.OUTPUT_COVERAGE_DOC)
line_end = '(?:\n|\r\n?)'
BORDER_STYLE = 'style="border: 1px solid"'

patch_logger = logging.getLogger('patch')
patch_logger.addHandler(logging.NullHandler())


def is_ignored_file(file_path):
    for ignored_portion in globalsettings.IGNORED_NAME_PORTIONS:
        try:
            result = bool(ignored_portion.match(file_path))
        except AttributeError:
            result = ignored_portion in file_path

        if result:
            return True

    return False


def parse_patch(patch_file):
    """returns a dictionary of {filepath:[lines patched]}"""
    patch_set = patch.fromfile(patch_file)
    target_files = set()
    for changed_file in patch_set.items:
        relative_path = changed_file.target
        if not is_ignored_file(relative_path):
            absolute_file_path = os.path.join(ROOT_PATH, relative_path)
            if os.path.exists(absolute_file_path):
                target_files.add(absolute_file_path)

    target_lines = defaultdict(list)
    for p in patch_set.items:
        source_file = os.path.join(ROOT_PATH, p.target)
        if source_file not in target_files:
            continue

        for hunk in p.hunks:
            patched_lines = []
            line_offset = hunk.starttgt
            for hline in hunk.text:
                if not hline.startswith(REMOVED_LINE):
                    if hline.startswith(ADDED_LINE):
                        patched_lines.append(line_offset)

                    line_offset += 1

            target_lines[p.target].extend(patched_lines)

    return target_lines


def main():
    opt = OptionParser(usage='usage: %prog diffpatch [options...]')
    opt.add_option('-a', '--show-all', dest='show_all', default=False,
                   action='store_true', help='Show even 100% coveraged files')
    (options, args) = opt.parse_args()
    if not args:
        print "No patch file provided"
        sys.exit(1)

    show_all = options.show_all
    patch_file = args[0]
    target_lines = parse_patch(patch_file)
    missing_lines = {}
    targets = []
    # generate coverage reports
    cov = coverage.coverage(data_file=COVERAGE_FILE_PATH)
    cov.load()
    for target_file in target_lines.iterkeys():
        path = os.path.join(ROOT_PATH, target_file)
        filename, executed, excluded, missing, missing_regions = cov.analysis2(path)
        missing_patched = set(missing) & set(target_lines[target_file])
        if missing_patched or show_all:
            targets.append(target_file)
            missing_lines[target_file] = list(missing_patched)

    report = {}
    for file_name, missing in missing_lines.iteritems():
        missing_percent = float(len(missing)) / len(target_lines[file_name]) * 100
        coverage_percent = 100 - missing_percent
        report[file_name] = coverage_percent
        print '%s: %.1f%% coverage' % (file_name, coverage_percent)

    with open('diffcoverage.html', 'w') as html_report:
        html_report.write('<html><body><b>Diff Coverage Report</b><table '
                          '%s>' % BORDER_STYLE)
        for file_name, coverage_percent in report.iteritems():
            html_report.write('<tr %(BORDER_STYLE)s><td %(BORDER_STYLE)s>%(file_name)s'
                              '</td><td %(BORDER_STYLE)s>%(coverage_percent).1f%%</td>'
                              '</tr>' % {
                                  'BORDER_STYLE': BORDER_STYLE,
                                  'file_name': file_name,
                                  'coverage_percent': coverage_percent
                              })

        html_report.write('</table></body></html>')


if __name__ == "__main__":
    main()
