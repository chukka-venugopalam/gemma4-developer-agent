# Repository Navigation

Use the cheapest reliable evidence first:
1. git status --short
2. git grep -n for the strongest exact anchor
3. read the relevant definition
4. find nearby callers/tests
5. use graph tools for ambiguous or cross-module relationships
6. patch the smallest production path
7. verify
8. submit

Graph tools are optional evidence, not mandatory ceremony.
If graph retrieval is empty or unhelpful, return to exact source search.
