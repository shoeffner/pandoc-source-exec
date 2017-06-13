"""pandoc-source-exec is a panflute pandoc filter to execute source code and
add the output to the pandoc document."""

import glob
import os
import subprocess

try:
    from pexpect import replwrap
except ImportError:
    pass
import panflute as pf


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
        child = replwrap.python()
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
            final_code += result.split('\n')
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

    If elem has either the plt attribute (format: plt=width,height) or
    the attributes width=width and/or height=height, the figurewidth and -height
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

    return code + f"""
from matplotlib2tikz import get_tikz_code
tikz = get_tikz_code('', figureheight='{figureheight}', figurewidth='{figurewidth}')
print(tikz)"""


def trimpath(attributes):
    if 'pathdepth' in attributes:
        if attributes['pathdepth'] != 'full':
            pathelements = []
            remainder = attributes['file']
            limit = int(attributes['pathdepth'])
            pf.debug('rem', remainder, 'limit', limit)
            while len(pathelements) < limit and remainder:
                remainder, pe = os.path.split(remainder)
                pathelements.insert(0, pe)
            return os.path.join(*pathelements)
        return attributes['file']
    return os.path.basename(attributes['file'])


def prepare(doc):
    usepackage = '\\usepackage{pgfplots}'
    include = pf.RawInline(usepackage, format='tex')
    try:
        if usepackage not in str(doc.metadata['header-includes']):
            doc.metadata['header-includes']._content.list \
                .insert(0, pf.MetaInlines(include))
    except KeyError:
        doc.metadata['header-includes'] = include


def action(elem, doc):
    if isinstance(elem, pf.CodeBlock):

        elems = [elem] if 'hide' not in elem.classes else []

        if 'file' in elem.attributes.keys():
            elem.text = read_file(elem.attributes['file'])
            elems.insert(0, pf.Para(pf.Emph(pf.Str('File:')),
                                    pf.Space,
                                    pf.Code(trimpath(elem.attributes))))

        if 'exec' in elem.classes:
            if 'interactive' in elem.classes or elem.text[:4] == '>>> ':
                elem.text = execute_interactive_code(elem, doc)
            else:
                result = execute_code_block(elem, doc)

                if 'hideimports' in elem.classes:
                    elem.text = remove_import_statements(elem.text)

                if 'plt' in elem.attributes or 'plt' in elem.classes:
                    result = '\n'.join(['\\begin{center}'] + \
                                       result.splitlines()[10:] + \
                                       ['\\end{center}'])
                    block = pf.RawBlock(result, format='latex')
                else:
                    block = pf.CodeBlock(result, classes=['changelog'])

                elems += [pf.Para(pf.Emph(pf.Str('Output:'))), block]

        return elems


def finalize(doc):
    pass


def main(doc=None):
    return pf.run_filter(action,
                         prepare=prepare,
                         finalize=finalize,
                         doc=doc)


if __name__ == '__main__':
    main()
