
Lexicon Tools
================================


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
