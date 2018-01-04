pandoc-source-exec
==================

``pandoc-source-exec`` is a `panflute`_ `pandoc`_ `filter`_.

It executes code annotated code blocks with the proper executables and
adds the output below. `Example <example>`__:

::

    ```{ .python .exec }
    print('Hello World')
    ```

The above can be compiled like this:

.. code-block:: Makefile

    example.pdf: example.md example.py
    	pandoc --filter pandoc-source-exec -o $@ $<

The resulting output will include `Hello World` after the code block.

``pandoc-source-exec`` offers many other features, including tikz plots,
proper figures and code listings as well as including files as code.

For more examples check the `example files`_.


Installation
------------

Just use pip to install it from `pypi`_

.. code-block:: shell

    pip install pandoc-source-exec


.. _`filter`: https://pandoc.org/scripting.html
.. _`pandoc`: https://pandoc.org/index.html
.. _`panflute`: http://scorreia.com/software/panflute/index.html
.. _`pypi`: https://pypi.python.org/pypi/pandoc-source-exec
.. _`example files`: https://github.com/shoeffner/pandoc-source-exec/tree/master/example


Future
------

- Execute code other than python
- Refactor interactive execution, build REPL wrappers.
- Allow configurable pre- and postfixes for the output
