"""pandoc-source-exec is a panflute pandoc filter to execute source code and
add the output to the pandoc document."""

import glob
import os
import re
import subprocess

__version__ = '0.2.2'

try:
    from pexpect import replwrap
except ImportError:
    pass
try:
    import panflute as pf
except ImportError:
    pass


EXECUTORS = {
    'default': 'echo',
    'perl': '/usr/bin/env perl -e',
    'php': '/usr/bin/env php -r',
    'python': '/usr/bin/env python3 -c',
    'python2': '/usr/bin/env python2 -c',
    'python3': '/usr/bin/env python3 -c',
    'ruby': '/usr/bin/env ruby -e',
}


def select_executor(elem, doc):
    """Determines the executor for the code in `elem.text`.

    The elem attributes and classes select the executor in this order (highest
    to lowest):
        - custom commands (cmd=...)
        - runas (runas=...) takes a key for the executors
        - first element class (.class) determines language and thus executor

    Args:
        elem The AST element.
        doc  The document.

    Returns:
        The command to execute code.
    """
    executor = EXECUTORS['default']

    if 'cmd' in elem.attributes.keys():
        executor = elem.attributes['cmd']
    elif 'runas' in elem.attributes.keys():
        executor = EXECUTORS[elem.attributes['runas']]
    elif elem.classes[0] != 'exec':
        executor = EXECUTORS[elem.classes[0]]

    return executor


def execute_code_block(elem, doc):
    """Executes a code block by passing it to the executor.

    Args:
        elem The AST element.
        doc  The document.

    Returns:
        The output of the command.
    """
    command = select_executor(elem, doc).split(' ')
    code = elem.text
    if 'plt' in elem.attributes or 'plt' in elem.classes:
        code = save_plot(code, elem)
    command.append(code)
    if 'args' in elem.attributes:
        for arg in elem.attributes['args'].split():
            command.append(arg)

    cwd = elem.attributes['wd'] if 'wd' in elem.attributes else None

    return subprocess.run(command,
                          encoding='utf8',
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=cwd).stdout


def execute_interactive_code(elem, doc):
    """Executes code blocks for a python shell.

    Parses the code in `elem.text` into blocks and
    executes them.

    Args:
        elem The AST element.
        doc  The document.

    Return:
        The code with inline results.
    """
    code_lines = [l[4:] for l in elem.text.split('\n')]

    code_blocks = [[code_lines[0]]]
    for line in code_lines[1:]:
        if line.startswith(' ') or line == '':
            code_blocks[-1].append(line)
        else:
            code_blocks.append([line])

    final_code = []
    try:
        child = replwrap.REPLWrapper("python", ">>> ", None)
    except NameError:
        pf.debug('Can not run interactive session. No output produced ' +
                 '(Code was:\n{!s}\n)'
                 .format(elem))
        pf.debug('Please pip install pexpect.')
        return ''
    for code_block in code_blocks:
        result = child.run_command('\n'.join(code_block) + '\n').rstrip('\r\n')
        final_code += [('>>> ' if i == 0 else '... ') + l for i, l in
                       enumerate(code_block)]
        if result:
            final_code += [r for r in result.split('\n')
                           if r.strip() not in code_block]
    return '\n'.join(final_code)


def read_file(filename):
    """Reads a file which matches the pattern `filename`.

    Args:
        filename The filename pattern

    Returns:
        The file content or the empty string, if the file is not found.
    """
    hits = glob.glob('**/{}'.format(filename), recursive=True)
    if not len(hits):
        pf.debug('No file "{}" found.'.format(filename))
        return ''
    elif len(hits) > 1:
        pf.debug('File pattern "{}" ambiguous. Using first.'.format(filename))

    with open(hits[0], 'r') as f:
        return f.read()


def filter_lines(code, line_spec):
    """Removes all lines not matching the line_spec.

    Args:
        code The code to filter
        line_spec The line specification. This should be a comma-separated
                  string of lines or line ranges, e.g. 1,2,5-12,15
                  If a line range starts with -, all lines up to this line are
                  included.
                  If a line range ends with -, all lines from this line on are
                  included.
                  All lines mentioned (ranges are inclusive) are used.
    Returns:
        Only the specified lines.
    """
    code_lines = code.splitlines()

    line_specs = [line_denom.strip() for line_denom in line_spec.split(',')]

    single_lines = set(map(int, filter(lambda line: '-' not in line, line_specs)))
    line_ranges = set(filter(lambda line: '-' in line, line_specs))

    for line_range in line_ranges:
        begin, end = line_range.split('-')
        if not begin:
            begin = 1
        if not end:
            end = len(code_lines)
        single_lines.update(range(int(begin), int(end) + 1))

    keep_lines = []
    for line_number, line in enumerate(code_lines, 1):
        if line_number in single_lines:
            keep_lines.append(line)

    return '\n'.join(keep_lines)




def remove_import_statements(code):
    """Removes lines with import statements from the code.

    Args:
        code: The code to be stripped.

    Returns:
        The code without import statements.
    """
    new_code = []
    for line in code.splitlines():
        if not line.lstrip().startswith('import ') and \
           not line.lstrip().startswith('from '):
            new_code.append(line)

    while new_code and new_code[0] == '':
        new_code.pop(0)
    while new_code and new_code[-1] == '':
        new_code.pop()

    return '\n'.join(new_code)


def save_plot(code, elem):
    """Converts matplotlib plots to tikz code.

    If elem has either the plt attribute (format: plt=width,height) or the
    attributes width=width and/or height=height, the figurewidth and -height
    are set accordingly. If none are given, a height of 4cm and a width of 6cm
    is used as default.

    Args:
        code: The matplotlib code.
        elem: The element.

    Returns:
        The code and some code to invoke matplotlib2tikz.
    """
    if 'plt' in elem.attributes:
        figurewidth, figureheight = elem.attributes['plt'].split(',')
    else:
        try:
            figureheight = elem.attributes['height']
        except KeyError:
            figureheight = '4cm'

        try:
            figurewidth = elem.attributes['width']
        except KeyError:
            figurewidth = '6cm'

    return f"""import matplotlib
matplotlib.use('TkAgg')
{code}
from matplotlib2tikz import get_tikz_code
tikz = get_tikz_code(figureheight='{figureheight}', figurewidth='{figurewidth}')  # noqa
print(tikz)"""


def trimpath(attributes):
    """Simplifies the given path.

    If pathdepth is in attributes, the last pathdepth elements will be
    returned. If pathdepth is "full", the full path will be returned.
    Otherwise the filename only will be returned.

    Args:
        attributes: The element attributes.

    Returns:
        The trimmed path.
    """
    if 'pathdepth' in attributes:
        if attributes['pathdepth'] != 'full':
            pathelements = []
            remainder = attributes['file']
            limit = int(attributes['pathdepth'])
            while len(pathelements) < limit and remainder:
                remainder, pe = os.path.split(remainder)
                pathelements.insert(0, pe)
            return os.path.join(*pathelements)
        return attributes['file']
    return os.path.basename(attributes['file'])


def make_codelisting(inner_elements, caption, label, *,
                     shortcaption=None, above=True):
    r"""Creates a source code listing:

        \begin{codelisting}[hbtp]
        inner_elements
        \caption[caption]{\label{label}caption}
        \end{codelisting}

    and returns the list containing the pandoc elements.

    Args:
        inner_elements: A list of inner pandoc elements, usually a
                        code block and potentially outputs etc.
        caption:        The caption to be used. Will be used below code and in
                        list of code listings.
        label:          The label to use.
        shortcaption:   A short caption to be used in the list of code listings.
                        If None, the normal caption will be used.
        above:          The caption is placed above (True) or below (False)
                        the code listing.

    Returns:
        A list of elements for this codelisting.
    """
    begin = pf.RawBlock(r'\begin{codelisting}[hbtp]', format='tex')
    end = pf.RawBlock(r'\end{codelisting}', format='tex')

    if not shortcaption:
        shortcaption = caption
    cap_begin = f'\\caption[{shortcaption}]{{\\label{{{label}}}'
    caption_elem = pf.RawBlock(cap_begin + caption + '}', format='tex')
    if above:
        return [begin, caption_elem] + inner_elements + [end]
    return [begin] + inner_elements + [caption_elem, end]


def prepare(doc):
    """Sets the caption_found and plot_found variables to False."""
    doc.caption_found = False
    doc.plot_found = False
    doc.listings_counter = 0


def maybe_center_plot(result):
    """Embeds a possible tikz image inside a center environment.

    Searches for matplotlib2tikz last commend line to detect tikz images.

    Args:
        result: The code execution result

    Returns:
        The input result if no tikzpicture was found, otherwise a centered
        version.
    """
    begin = re.search('(% .* matplotlib2tikz v.*)', result)
    if begin:
        result = ('\\begin{center}\n' + result[begin.end():] +
                  '\n\\end{center}')
    return result


def action(elem, doc):  # noqa
    """Processes pf.CodeBlocks.

    For details and a specification of how each command should behave,
    check the example files (especially the md and pdf)!

    Args:
        elem: The element to process.
        doc:  The document.

    Returns:
        A changed element or None.
    """
    if isinstance(elem, pf.CodeBlock):
        doc.listings_counter += 1
        elems = [elem] if 'hide' not in elem.classes else []

        if 'file' in elem.attributes:
            elem.text = read_file(elem.attributes['file'])
            filename = trimpath(elem.attributes)
            prefix = pf.Emph(pf.Str('File:'))

        if 'exec' in elem.classes:
            if 'interactive' in elem.classes or elem.text[:4] == '>>> ':
                elem.text = execute_interactive_code(elem, doc)
            else:
                result = execute_code_block(elem, doc)

                if 'hideimports' in elem.classes:
                    elem.text = remove_import_statements(elem.text)

                if 'plt' in elem.attributes or 'plt' in elem.classes:
                    doc.plot_found = True
                    result = maybe_center_plot(result)
                    block = pf.RawBlock(result, format='latex')
                else:
                    block = pf.CodeBlock(result, classes=['changelog'])

                elems += [pf.Para(pf.Emph(pf.Str('Output:'))), block]

        if 'lines' in elem.attributes:
            elem.text = filter_lines(elem.text, elem.attributes['lines'])

        label = elem.attributes.get('label', f'cl:{doc.listings_counter}')

        if 'caption' in elem.attributes.keys():
            doc.caption_found = True
            cap = pf.convert_text(elem.attributes['caption'], output_format='latex')  # noqa
            if 'shortcaption' in elem.attributes.keys():
                shortcap = pf.convert_text(elem.attributes['shortcaption'], output_format='latex')  # noqa
            else:
                shortcap = cap
            if 'file' in elem.attributes.keys():
                cap += pf.convert_text(f'&nbsp;(`{filename}`)', output_format='latex')  # noqa

            elems = make_codelisting(elems, cap, label, shortcaption=shortcap,
                                     above='capbelow' not in elem.classes)
        elif 'caption' in elem.classes:
            doc.caption_found = True
            cap = ''
            if 'file' in elem.attributes.keys():
                cap = pf.convert_text(f'`{filename}`', output_format='latex')
            elems = make_codelisting(elems, cap, label,
                                     above='capbelow' not in elem.classes)
        else:
            if 'file' in elem.attributes.keys():
                elems.insert(0, pf.Para(prefix, pf.Space,
                                        pf.Code(filename)))

        return elems


def finalize(doc):
    """Adds the pgfplots and caption packages to the header-includes if needed.
    """
    if doc.plot_found:
        pgfplots_inline = pf.MetaInlines(pf.RawInline(
            r'''%
\makeatletter
\@ifpackageloaded{pgfplots}{}{\usepackage{pgfplots}}
\makeatother
\usepgfplotslibrary{groupplots}
''', format='tex'))
        try:
            doc.metadata['header-includes'].append(pgfplots_inline)
        except KeyError:
            doc.metadata['header-includes'] = pf.MetaList(pgfplots_inline)

    if doc.caption_found:
        caption_inline = pf.MetaInlines(pf.RawInline(
            r'''%
\makeatletter
\@ifpackageloaded{caption}{}{\usepackage{caption}}
\@ifpackageloaded{cleveref}{}{\usepackage{cleveref}}
\@ifundefined{codelisting}{%
    \DeclareCaptionType{codelisting}[Code Listing][List of Code Listings]
    \crefname{codelisting}{code listing}{code listings}
    \Crefname{codelisting}{Code Listing}{Code Listings}
    \captionsetup[codelisting]{position=bottom}
}{}
\makeatother
''', format='tex'))
        try:
            doc.metadata['header-includes'].append(caption_inline)
        except KeyError:
            doc.metadata['header-includes'] = pf.MetaList(caption_inline)


def main(doc=None):
    return pf.run_filter(action,
                         prepare=prepare,
                         finalize=finalize,
                         doc=doc)


if __name__ == '__main__':
    main()
