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
import string
import sys

import coverage

import patch
import settings


TEMPLATE_FOLDER = os.path.abspath(os.path.join(__file__, '..'))
LAYOUT_TEMPLATE_FILE = os.path.join(TEMPLATE_FOLDER, 'templates/layout.html')
ROW_TEMPLATE_FILE = os.path.join(TEMPLATE_FOLDER, 'templates/row.html')
ADDED_LINE = '+'
REMOVED_LINE = '-'
ROOT_PATH = os.getcwd()
COVERAGE_FILE_PATH = os.path.join(ROOT_PATH, settings.COVERAGE_PATH)
coverage_html_dir = os.path.join(os.getcwd(), settings.OUTPUT_COVERAGE_DOC)
line_end = '(?:\n|\r\n?)'
BORDER_STYLE = 'style="border: 1px solid"'

patch_logger = logging.getLogger('patch')
patch_logger.addHandler(logging.NullHandler())


class FileTemplate(string.Template):
    def __init__(self, file_name):
        with open(file_name, 'r') as template_file:
            super(FileTemplate, self).__init__(template_file.read())


def is_ignored_file(file_path):
    for ignored_portion in settings.IGNORED_NAME_PORTIONS:
        try:
            result = bool(ignored_portion.match(file_path))
        except AttributeError:
            result = ignored_portion in file_path

        if result:
            return True

    return False


def get_jenkins_path(file_name):
    file_name_parts = file_name.split('/')
    if len(file_name_parts) > 1:
        file_name_parts = ['_'.join(file_name_parts[:2])] + file_name_parts[2:]

    file_name_parts[-1].replace('.py', '_py')
    return os.path.sep.join(file_name_parts)


def parse_patch(patch_file):
    """returns a dictionary of {filepath:[lines patched]}"""
    patch_set = patch.fromfile(patch_file)
    target_files = set()
    for changed_file in patch_set.items:
        relative_path = changed_file.target
        if not is_ignored_file(relative_path):
            absolute_file_path = os.path.join(ROOT_PATH, relative_path)
            if (os.path.exists(absolute_file_path)
                    and not os.path.isdir(absolute_file_path)):
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


def diff_coverage(patch_file, show_all=False, coverage_file=settings.COVERAGE_PATH,
                  html_file_path=settings.HTML_DIFF_REPORT_PATH):
    assert os.path.exists(coverage_file)

    target_lines = parse_patch(patch_file)
    missing_lines = {}
    targets = []
    # generate coverage reports
    cov = coverage.coverage(data_file=coverage_file)
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
        coverage_executed = len(target_lines[file_name])
        coverage_covered = coverage_executed - len(missing)
        try:
            missing_percent = float(len(missing)) / coverage_executed * 100
        except ZeroDivisionError:
            missing_percent = 100.0
            
        coverage_percent = 100 - missing_percent
        report[file_name] = {
            'coverage_percent': coverage_percent,
            'coverage_executed': coverage_executed,
            'coverage_covered': coverage_covered
        }
        print '%s: %.1f%% coverage' % (file_name, coverage_percent)

    with open(html_file_path, 'w') as html_report:
        if report:
            layout_template = FileTemplate(LAYOUT_TEMPLATE_FILE)
            row_template = FileTemplate(ROW_TEMPLATE_FILE)
            rows = []
            for file_name, coverage_info in report.iteritems():
                coverage_percent = '%.1f%%' % coverage_info['coverage_percent']
                coverage_executed = coverage_info['coverage_executed']
                coverage_covered = coverage_info['coverage_covered']
                jenkins_coverage_path = get_jenkins_path(file_name)
                rows.append(row_template.substitute(
                    file_name=file_name, coverage_percent=coverage_percent,
                    coverage_executed=coverage_executed,
                    coverage_covered=coverage_covered,
                    jenkins_coverage_path=jenkins_coverage_path))

            all_rows = ''.join(rows)
            html_report_string = layout_template.substitute(coverage_rows=all_rows)
            html_report.write(html_report_string)
        else:
            # TODO stuff
            pass


def main():
    opt = OptionParser(usage='usage: %prog diffpatch [options...]')
    opt.add_option('-a', '--show-all', dest='show_all', default=False,
                   action='store_true', help='Show even 100% coveraged files')
    opt.add_option('-c', '--coverage-file', dest='coverage_file',
                   default=settings.COVERAGE_PATH, help='Set the coverage file path')
    opt.add_option('-o', '--output-file', dest='html_file_path',
                   default=settings.HTML_DIFF_REPORT_PATH,
                   help='Set the path to save the html diff coverage report.')
    (options, args) = opt.parse_args()
    if not args:
        print "No patch file provided"
        print
        opt.print_help()
        sys.exit(1)

    show_all = options.show_all
    coverage_file = options.coverage_file
    html_file_path = options.html_file_path
    patch_file = args[0]
    diff_coverage(patch_file, show_all=show_all, coverage_file=coverage_file,
                  html_file_path=html_file_path)


if __name__ == "__main__":
    main()


