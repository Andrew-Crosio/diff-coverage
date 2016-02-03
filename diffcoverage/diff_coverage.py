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
from __future__ import print_function
from collections import defaultdict
from optparse import OptionParser
import logging
import os
import re
import string
import subprocess
import sys

import coverage

import patch
import settings


PERCENT_COMPARISON = lambda x, y: cmp(y[1]['coverage_percent'], x[1]['coverage_percent'])
NUMCOVERED_COMPARISON = lambda x, y: cmp(y[1]['coverage_executed'],
                                         x[1]['coverage_executed'])
FILENAME_COMPARISON = lambda x, y: cmp(x[0], y[0])
COMPARERS = {
    'filename': FILENAME_COMPARISON,
    'percent': PERCENT_COMPARISON,
    'numcovered': NUMCOVERED_COMPARISON
}
SORT_BY_CHOICES = COMPARERS.keys()
LINE_SEPARATOR_NO_JOIN = '-'
PERCENT_COVERED_HEADER = '% Covered'
TOTAL_LINE_COV_HEADER = 'Total'
COVERAGE_LINE_HEADER = 'Covered'
FILE_NAME_HEADER = 'File name'
GIT_BRANCH_SELECTION_MARKER = '*'
STRIP_GIT_BRANCH_CHARS = GIT_BRANCH_SELECTION_MARKER + string.whitespace
LINE_COVER_SEP = ' / '
LEFTOVER_BAD_CHARS = re.compile('^(?:a|b|ab)/')
TEMPLATE_FOLDER = os.path.abspath(os.path.join(__file__, '..'))
LAYOUT_TEMPLATE_FILE = os.path.join(TEMPLATE_FOLDER, 'templates/cobertura/layout.html')
ROW_TEMPLATE_FILE = os.path.join(TEMPLATE_FOLDER, 'templates/cobertura/row.html')
ADDED_LINE = '+'
REMOVED_LINE = '-'
ROOT_PATH = os.getcwd()
COVERAGE_FILE_PATH = os.path.join(ROOT_PATH, settings.COVERAGE_PATH)
coverage_html_dir = os.path.join(os.getcwd(), settings.OUTPUT_COVERAGE_DOC)
line_end = r'(?:\n|\r\n?)'
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
            result = bool(ignored_portion.search(file_path))
        except AttributeError:
            result = ignored_portion in file_path

        if result:
            return True

    for required_portion in settings.REQUIRED_NAME_PORTIONS:
        try:
            result = bool(required_portion.search(file_path))
        except AttributeError:
            result = required_portion in file_path

        if not result:
            return True

    return False


def get_jenkins_path(file_name, root_package=None, src_file_link_prefix=None):
    file_name_parts = file_name.split('/')
    file_name_parts[-1] = file_name_parts[-1].replace('.py', '_py')
    if src_file_link_prefix:
        file_name_parts.insert(0, src_file_link_prefix)
    if root_package:
        return '%s/%s' % (root_package, '_'.join(file_name_parts))
    else:
        if len(file_name_parts) > 1:
            file_name_parts = ['_'.join(file_name_parts[:2])] + file_name_parts[2:]

        return os.path.sep.join(file_name_parts)


def parse_patch(patch_file):
    """returns a dictionary of {filepath:[lines patched]}"""
    patch_set = patch.fromfile(patch_file)
    target_files = set()
    for changed_file in patch_set.items:
        relative_path = LEFTOVER_BAD_CHARS.sub('', changed_file.target)
        if not is_ignored_file(relative_path):
            absolute_file_path = os.path.join(ROOT_PATH, relative_path)
            if (os.path.exists(absolute_file_path)
                    and not os.path.isdir(absolute_file_path)):
                target_files.add(absolute_file_path)

    target_lines = defaultdict(list)
    for p in patch_set.items:
        source_file = os.path.join(ROOT_PATH, LEFTOVER_BAD_CHARS.sub('', p.target))
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

            target_lines[LEFTOVER_BAD_CHARS.sub('', p.target)].extend(patched_lines)

    return target_lines


def get_current_git_branch():
    process = subprocess.Popen(['git', 'branch'], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    if process.wait():
        raise RuntimeError('Error retrieving current branch: %s'
                           % process.stderr.read() or 'No error available')

    for branch_line in process.stdout.readlines():
        if branch_line.startswith(GIT_BRANCH_SELECTION_MARKER):
            return branch_line.strip(STRIP_GIT_BRANCH_CHARS)

    raise RuntimeError('Impossibru! No git branch selected?')


def diff_coverage(patch_file, show_all=False, coverage_file=settings.COVERAGE_PATH,
                  html_file_path=None, root_package=None,
                  sort_by='filename', link_prefix='',
                  retain_build_no=False):
    assert os.path.exists(coverage_file)

    target_lines = parse_patch(patch_file)
    missing_lines = {}
    targets = []
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

    if not html_file_path:
        return

    with open(html_file_path, 'w') as html_report:
        if report:
            current_branch = get_current_git_branch()
            print('Coverage report for branch "%s" against "%s"' % (
                current_branch, settings.COMPARE_WITH_BRANCH))
            max_filename_size = max(len(key) for key in report.keys())
            max_filename_size = max(max_filename_size, len(FILE_NAME_HEADER))
            max_covered_size = len(str(max(info['coverage_covered']
                                           for info in report.values())))
            max_covered_size = max(max_covered_size, len(COVERAGE_LINE_HEADER))
            max_executed_size = len(str(max(info['coverage_executed']
                                            for info in report.values())))
            max_executed_size = max(max_executed_size, len(TOTAL_LINE_COV_HEADER))
            header_format_string = ('| {0:^%ds} | {1:^9s} | {2:^%ds} / {3:^%ds} |'
                                    % (max_filename_size, max_covered_size,
                                       max_executed_size))
            line_separator = '+-%s-+-%s-+-%s-+' % (
                LINE_SEPARATOR_NO_JOIN * max_filename_size,
                LINE_SEPARATOR_NO_JOIN * 9,
                LINE_SEPARATOR_NO_JOIN * (max_covered_size + max_executed_size + 3),
            )
            print(line_separator)
            print(header_format_string.format(FILE_NAME_HEADER, PERCENT_COVERED_HEADER,
                                              COVERAGE_LINE_HEADER, TOTAL_LINE_COV_HEADER))
            print(line_separator)
            print_format_string = ('| {0:<%ds} | {1:>9s} | {2:>%dd} / {3:<%dd} |'
                                   % (max_filename_size, max_covered_size,
                                      max_executed_size))
            layout_template = FileTemplate(LAYOUT_TEMPLATE_FILE)
            row_template = FileTemplate(ROW_TEMPLATE_FILE)
            rows = []
            try:
                comparer = COMPARERS[sort_by]
            except KeyError:
                raise ValueError('Unknown sort_by option')

            sorted_report = sorted(report.items(), cmp=comparer)
            total_coverage_percent = 0.0
            total_coverage_executed = 0
            total_coverage_covered = 0
            for file_name, coverage_info in sorted_report:
                coverage_percent = '%.1f%%' % coverage_info['coverage_percent']
                coverage_executed = coverage_info['coverage_executed']
                coverage_covered = coverage_info['coverage_covered']
                total_coverage_percent += coverage_info['coverage_percent']
                total_coverage_executed += coverage_executed
                total_coverage_covered += coverage_covered
                jenkins_coverage_path = get_jenkins_path(file_name, root_package, link_prefix)

                if retain_build_no:
                    relative_path = '..'
                else:
                    relative_path = '../..'
                rows.append(row_template.substitute(
                    file_name=file_name, coverage_percent=coverage_percent,
                    coverage_executed=coverage_executed,
                    coverage_covered=coverage_covered,
                    jenkins_coverage_path=jenkins_coverage_path,
                    relative_path=relative_path))
                print(print_format_string.format(file_name, coverage_percent,
                                                 coverage_covered, coverage_executed))

            print(line_separator)
            num_items = len(report)
            total_avg_coverage_percent = '%.1f%%' % (
                float(total_coverage_covered) / total_coverage_executed * 100)
            print(print_format_string.format('TOTAL', total_avg_coverage_percent,
                                             total_coverage_covered,
                                             total_coverage_executed))
            average_coverage_percent = '%.1f%%' % (total_coverage_percent / num_items)
            average_coverage_executed = total_coverage_executed / num_items
            average_coverage_covered = total_coverage_covered / num_items
            avg_print_format_string = ('| {0:<%ds} | {1:>9s} | {2:>%d.1f} / {3:<%d.1f} |'
                                       % (max_filename_size, max_covered_size,
                                          max_executed_size))
            print(avg_print_format_string.format('AVERAGE', average_coverage_percent,
                                                 average_coverage_covered,
                                                 average_coverage_executed))
            print(line_separator)
            all_rows = ''.join(rows)
            html_report_string = layout_template.substitute(coverage_rows=all_rows)
            html_report.write(html_report_string)
        else:
            html_report.write('<html><body><h1>Error! Nothing found!</body></html>')
            print('Error! Nothing found!', file=sys.stderr)


def main():
    opt = OptionParser(usage='usage: %prog diffpatch [options...]')
    opt.add_option('-a', '--show-all', dest='show_all', default=False,
                   action='store_true', help='Show even 100% coveraged files')
    opt.add_option('-c', '--coverage-file', dest='coverage_file',
                   default=settings.COVERAGE_PATH, help='Set the coverage file path')
    opt.add_option('-o', '--output-file', dest='html_file_path',
                   default=None,
                   help='Set the path to save the html diff coverage report.')
    opt.add_option('-r', '--root-package', dest='root_package',
                   default=None, help='Set the root package name for the XML report')
    opt.add_option('-s', '--sort-by', dest='sort_by', default='filename',
                   help='Sort by type: [filename, percentage, numcovered]',
                   choices=SORT_BY_CHOICES)
    opt.add_option('-b', '--retain-build-no', dest='retain_build_no', default=False,
                   action='store_true', help='Set the build number to be used while creating links for source files')
    opt.add_option('-p', '--link-prefix', dest='link_prefix',
                   default='', help='Set link prefix to be used while creating links for source file')
    (options, args) = opt.parse_args()
    if not args:
        print("No patch file provided")
        print()
        opt.print_help()
        sys.exit(1)

    show_all = options.show_all
    coverage_file = options.coverage_file
    html_file_path = options.html_file_path
    root_package = options.root_package
    sort_by = options.sort_by
    retain_build_no = options.retain_build_no
    link_prefix = options.link_prefix

    patch_file = args[0]
    diff_coverage(patch_file, show_all=show_all, coverage_file=coverage_file,
                  html_file_path=html_file_path, root_package=root_package,
                  sort_by=sort_by, retain_build_no=retain_build_no, link_prefix=link_prefix)


if __name__ == "__main__":
    main()
