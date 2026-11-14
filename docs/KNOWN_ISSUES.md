# Known issues and limitations

Things the tool gets wrong or cannot do yet. Each entry says what happens, why,
and what a fix could look like, as a starting point for later work. Where a
test documents the behaviour, it is named.

## Difficulty scoring

### British spellings look rarer than they are

`wordfreq` scores each spelling separately, and American spellings are more
frequent in its data: "neighbour" 3.69 vs "neighbor" 4.11, "organiser" 3.11 vs
"organizer" 3.57, "kilometre" 3.21 vs "kilometer". With the default threshold
of 4.0, common words in British spelling are offered as if they were rare.

- Test: `test_known_limitation_british_spelling_scores_lower_than_american`
  in `tests/test_difficulty.py`.
- Possible fix: a small British-to-American spelling map (-our/-or, -ise/-ize,
  -re/-er, -lling/-ling, ...) in `difficulty.py`, scoring both spellings and
  keeping the higher score, the same way lemma and written form are combined.

### Typos cannot be told apart from rare words

`wordfreq` was built from real text, which contains typos. Common misspellings
have ordinary-looking scores ("teh" 3.04, "recieve" 2.75), so they pass as rare
words and are offered as candidates. Only words `wordfreq` has never seen get
no score; those are shown last in `vocab list` with a `?`.

- Test: `test_known_limitation_common_typos_have_a_score_like_real_words`
  in `tests/test_difficulty.py`.
- Possible fix: check candidates against a word list or spell checker and flag
  (not delete) the ones that fail; or mark them as ignored by hand, once
  `vocab learn` exists.

### The score is fixed when an item is first seen

An item's score is the highest of its lemma and the forms written in the import
that created it. A later import with a more common form does not update it.

- Possible fix: recompute the score when a new form is seen.

### The CEFR mapping is an estimate

"B2 = 4.0" is a rule of thumb, not an official mapping. Word frequency is also
only a rough stand-in for difficulty: a frequent word can have a rare meaning.

## Words and lemmas

### The small spaCy model makes mistakes

`en_core_web_sm` sometimes picks the wrong lemma ("better" as "well" instead of
"good", "data" as "datum") or the wrong part of speech, and misses or invents
proper names. Name filtering is therefore "where possible", not guaranteed.

One lemma mistake is repaired: nouns that end in "s" without being plurals
("geopolitics", "mathematics", "species") keep their "s" when the shortened
form is unknown or far rarer (`lemma_of` in `nlp/words.py`). The repair cannot
help when the shortened form is itself a common word: "economics" still becomes
"economic".

- Test: `test_known_limitation_economics_becomes_economic` in
  `tests/nlp/test_words.py`.
- Possible fix: try `en_core_web_md` or `en_core_web_trf` and compare on the
  same texts (the model is loaded in one place, `nlp/pipeline.py`); or check
  lemmas against a dictionary word list.

### No word families

Related words are separate items: "geopolitics" and "geopolitical", "decide"
and "decision", "happy" and "unhappiness". Knowing one says nothing about the
others, so a family can be offered several times.

- Possible fix: group items by a shared stem or a word-family list, and show
  the family together in `vocab learn`.

### One item per lemma, whatever the part of speech

"run" as a noun and as a verb share one item. The stored part of speech is the
one from the first time the word was seen.

### Days, months and nationalities are skipped

spaCy treats "Monday", "March" and "Turkish" as names, so they are not offered.

## Spoken text and auto-generated captions

### No punctuation means no real sentences

Auto-generated captions have no punctuation, so spaCy cannot find sentence
boundaries and the parse is worse than on written text. The current workaround
is cosmetic: an example longer than 25 words is cut to a window of about 10
words on each side of the target (`nlp/examples.py`). The cut can fall in the
middle of a clause, and phrasal verb detection still works on the poor parse.

- Possible fix: a punctuation-restoration model run before parsing. This is a
  separate model with its own download, so it should be optional.

### Cleaning is deliberately cautious

`nlp/cleaning.py` removes fillers (uh, um, er), caption markers and immediate
repetitions. It keeps real words that are often used as fillers ("like", "you
know", "I mean"), and it keeps doubled words that can be normal English ("so
so", "no no", "that that"), even when the speaker was only stumbling. Add a
word to `ALLOWED_REPEATS` or `FILLERS` in that file to change this.

### The original text is not kept

Only the cleaned sentence is stored, so an example can differ slightly from
what was said. The source text itself is never stored in the database.

## Importing

### A source cannot be replaced or removed

A text that was already imported is refused, even after the extraction rules
have improved. The only way to re-import today is to delete the database file,
which also discards everything marked as known.

- Possible fix: `vocab add --replace <file>`, which deletes the old source and
  its example sentences, removes items that are left without any example and
  were never marked or learned, and imports the text again. Its own task.

## Phrasal verbs

### The form is recognised, not the meaning

- "He looked up at the sky" is offered as `look up`, although it is literal.
  Test: `test_literal_look_up_at_the_sky_is_not_offered` (xfail).
- "She ran into the kitchen" is offered as `run into`, because the list is
  matched on words. Test: `test_literal_run_into_a_room_is_not_offered` (xfail).

Possible fix: use the object of the verb or preposition (a place vs. a person
or problem) as a hint, or let the user reject single example sentences.

### Listed verbs match literal "verb + preposition" too

"She was taken on a tour of the city" is offered as `take on`. The parser calls
"on" a preposition there, but it does the same in the real phrasal verb "count
on him", so the tool cannot reject one without losing the other. Only one case
is handled: a preposition leading into a date or time ("taken on January the
3rd") is rejected.

- Test: `test_literal_taken_on_a_tour_is_not_offered` (xfail).
- Possible fix: mark each entry of `phrasal_verbs.txt` as particle-type ("take
  on", only accepted when the parser sees a particle) or preposition-type
  ("count on", accepted with a preposition). This needs a small change to the
  file format and a review of every entry.

### Accidental three-part matches

"She put the tent up with her brother" is reported as `put up with` instead of
`put up`, because a later part only has to follow the part before it.
Test: `test_put_a_tent_up_with_someone_is_put_up` (xfail).

### Coverage depends on the list

Verbs with a true particle are found from the parse. Verbs followed by a
preposition or adverb ("look after", "run away") and three-part verbs are only
found if they are in `nlp/data/phrasal_verbs.txt`.

## Idioms

- Idioms with a changing part ("pull someone's leg") cannot be listed.
  Test: `test_idiom_with_a_changing_possessive` (xfail).
- An extra word inside an idiom ("makes perfect sense") breaks the match.
  Test: `test_idiom_with_an_inserted_word` (xfail).
- Literal uses of idiom wording are reported as the idiom.
  Test: `test_literal_use_of_idiom_wording_is_not_offered` (xfail).
- Only idioms in `nlp/data/idioms.txt` are found.

## Marking items as known

`vocab known` needs the base form ("give up", not "gave up"), and a phrase can
only be marked after it has been found in a text.
