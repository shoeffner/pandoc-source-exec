"""pandoc-source-exec is a panflute pandoc filter to execute source code and
add the output to the pandoc document."""

import glob
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
    command.append(elem.text)

    return subprocess.run(command,
                          encoding='utf8',
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout


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


def prepare(doc):
    pass


def action(elem, doc):
    if isinstance(elem, pf.CodeBlock):
        elems = [elem]

        if 'file' in elem.attributes.keys():
            elem.text = read_file(elem.attributes['file'])
            elems.insert(0, pf.Para(pf.Emph(pf.Str('File:')),
                                    pf.Space,
                                    pf.Code(elem.attributes['file'])))

        if 'exec' in elem.classes:
            if 'interactive' in elem.classes or elem.text[:4] == '>>> ':
                elem.text = execute_interactive_code(elem, doc)
            else:
                result = execute_code_block(elem, doc)

                elems += [
                    pf.Para(pf.Emph(pf.Str('Output:'))),
                    pf.CodeBlock(result, classes=[elem.classes[0]]),
                ]

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
