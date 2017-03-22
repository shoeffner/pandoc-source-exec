pandoc-source-exec
===============

``pandoc-source-exec`` is a `panflute`_ `pandoc`_ `filter`_.

It executes code annotated code blocks with the proper executables and
adds the output below. `Example <example>`__:

::

    ```{ .python .exec }
    print('Hello World')
    ```

The above can be compiled like this:

.. code-block:: Makefile

    main:
    	pandoc --filter pandoc-source-exec -o example.pdf example.md

The resulting output will include `Hello World` after the code block.

Installation
------------

Just use pip to install it from `pypi`_

.. code-block:: shell

    pip install pandoc-code-exec


.. _`filter`: https://pandoc.org/scripting.html
.. _`pandoc`: https://pandoc.org/index.html
.. _`panflute`: http://scorreia.com/software/panflute/index.html
.. _`pypi`: https://pypi.python.org/pypi/pandoc-code-exec

Future
------

- [ ] Execute code other than python
- [ ] Refactor interactive execution, build REPL wrappers.
- [ ] Allow configurable pre- and postfixes for the output
