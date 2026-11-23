from app.modules.journal.manifest import canonical, digest


def seal(evidence):
    return digest(canonical(evidence))


def verifies(evidence, expected):
    return seal(evidence) == expected
