
Lexicon Tools
================================

Documentation for these ``Lexicon Tools`` is managed via reStructuredText files and `Sphinx <http://www.sphinx-doc.org/>`_.
If you don't have Sphinx installed, you should check out a quick primer (`First Steps with Sphinx <http://www.sphinx-doc.org/en/1.7/tutorial.html>`_) or install it as below:

```

  ## If you don't have Sphinx installed already
  pip install Sphinx

  ## Generate a locally viewable HTML version
  cd docs
  make html

```

The latest version of the documentation can be generated as locally viewable HTML:  file:///path/to/git/repository/docs/_build/html/index.html


Leveraging SNOMED_CT concepts and relations
---------------------------------------------

Running ``lex_gen`` with the provided sample problems file should create fairly small dictionary to inspect. Here you can see that we have set the ``--max-distance`` to zero, which will only return strings for the precise CUIs provide. (In contrast, the default -1 does an exhaustive search while 1 goes one relation away, etc.)

```

python3 lex_gen.py \
    --max-distance 0 \
    --source-type problems \
    --batch-name testBatch001 \
    --input-file in/tiny_problems.csv

wc out/*_problems_testBatch001.*
      50     312    2443 out/4waydict_problems_testBatch001.csv
      50     162    1399 out/binarydict_problems_testBatch001.csv
      57     181    2319 out/conceptMapper_problems_testBatch001.dict
      64     190    2307 out/kb_problems_testBatch001.ttl
       2     114     967 out/widedict_problems_testBatch001.csv
     223     959    9435 total
	 
```


Leveraging RxNorm concepts and relations
---------------------------------------------

*TODO:* add ``tiny_allergens``

```
python3 lex_gen.py \
    --max-distance 0 \
    --source-type allergens \
    --batch-name batchA \
    --input-file in/tiny_allergens.csv

```

UMLS Engines
================================

Using the UMLS API
---------------------------------------------

Follow instructions on the `User Authentication
<https://documentation.uts.nlm.nih.gov/rest/authentication.html>`_
page about generating an authentication token. You'll need to set the
value of ``UMLS_API_TOKEN`` to this value in ``umls_utils.py`.

Installing a Local UMLS Engine (Experimental)
---------------------------------------------

After installing `py-umls <https://github.com/chb/py-umls>`_, follow
the instructions provided to initialize local repositories for the
different supported ontologies.

If you have checked out ``lexicon-tools`` as a git repository, then
you'll need to install ``py-umls`` as a submodule:

```
git submodule add https://github.com/chb/py-umls umls

```

Otherwise, you should be able to down the ``py-umls`` source code just
as you downloaded the ``lexicon-tools`` source code. Put the code in a
directory named ``umls`.

Running Tests
================================

Unit tests and code coverage can be verified using ``pytest`` and ``pytest-cov``:

```
python -m pytest --cov-report html:cov_html --cov=./ tests

```

Branches to be merged into ``stable`` and ``develop`` should be verified using ``flake8`` for code quality:

```
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

```

If the above command returns ``0`, then your code does not have any obvious errors.
