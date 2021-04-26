
Lexicon Tools
================================

Documentation for these `Lexicon Tools` is managed via reStructuredText files and `Sphinx <http://www.sphinx-doc.org/>`_.
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

```
python3 lex_gen.py \
    focusedProblem \
    batch1 \
    sample_problems.csv
```

Leveraging RxNorm concepts and relations
---------------------------------------------

```
python3 lex_gen.py \
    focusedAllergen \
    batchA \
    sample_allergens.csv
```

UMLS Engines
================================

Using the UMLS API
---------------------------------------------

Follow instructions on the `User Authentication
<https://documentation.uts.nlm.nih.gov/rest/authentication.html>`_
page about generating an authentication token. You'll need to set the
value of `UMLS_API_TOKEN` to this value in `umls_utils.py`.

Installing a Local UMLS Engine
---------------------------------------------

After installing `py-umls <https://github.com/chb/py-umls>`_, follow
the instructions provided to initialize local repositories for the
different supported ontologies.

If you have checked out `lexicon-tools` as a git repository, then
you'll need to install `py-umls` as a submodule:

```
git submodule add https://github.com/chb/py-umls umls
```

Otherwise, you should be able to down the `py-umls` source code just
as you downloaded the `lexicon-tools` source code. Put the code in a
directory named `umls`.
