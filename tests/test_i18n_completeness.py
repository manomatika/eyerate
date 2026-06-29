"""L1 i18n-completeness check for eyerate (manomatika/eyerate#73, phase 2).

Consumes the ONE canonical checker owned by matika
(``matika.core.i18n_completeness``) — eyerate does not reimplement the merge/scan
logic. Asserts every i18n key eyerate references (templates, routes, and its
menu/manifest/metadata JSON) resolves in EVERY shipped locale (en + es) against the
merged matika-core + eyerate catalogs (R1), and that eyerate's own catalogs are at
locale parity (R2). The matika sibling source is on PYTHONPATH via
``scripts/run-tests.sh``.
"""

import os

from matika.core import i18n_completeness as ic


def _eyerate_root() -> str:
    # this file: <root>/tests/test_i18n_completeness.py -> <root>
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _matika_src() -> str:
    import matika

    return os.path.dirname(os.path.dirname(matika.__file__))


def test_eyerate_i18n_is_complete():
    core = ic.matika_core_component(_matika_src(), audit=False)  # merge base only
    eyerate = ic.applug_component(_eyerate_root(), "eyerate")
    violations = ic.analyze([core, eyerate])
    assert violations == [], "eyerate i18n incomplete:\n" + "\n".join(
        v.render() for v in violations
    )
