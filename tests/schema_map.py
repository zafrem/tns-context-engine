# (glob relative to repo root, schema name -> schemas/<name>.schema.json)
GLOBS = [
    ("reference/meta.yml", "meta"),
    ("reference/registry.yml", "registry"),
    ("reference/released.yml", "registry"),
    ("reference/defamation.yml", "concepts"),
    ("reference/hate.yml", "concepts"),
    ("reference/fraud.yml", "concepts"),
    ("reference/illegal.yml", "concepts"),
    ("reference/cross_cutting.yml", "concepts"),
]

GLOBS += [
    ("lexicon/*/*.yml", "lexicon"),
]

GLOBS += [
    ("normalize/*.yml", "normalize"),
    ("stopwords/*.yml", "stopwords"),
]
