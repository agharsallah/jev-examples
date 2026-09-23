"""Everything Jev is asked about a draft message.

Two passes. The first reads the whole draft in one request: what it is trying
to do, how it reads along six dimensions, and a checklist of yes/no findings.
The second pass exists only because it cannot be written until the first has
answered -- which sentence carries the ask depends on whether there is an ask.

Every question in a pass goes out in a single request. Jev reads the state once
and answers all of them in parallel, so twenty-four questions cost barely more
than one.

  choices.py      pass one: what the draft is for, and what could go wrong
  dimensions.py   pass one: the six Score scales
  checks.py       pass one: the yes/no checklist and the speculative questions
  read.py         pass one, assembled into a docket and a state
  probes.py       pass two: the per-sentence questions
"""

from .checks import CHECKS, SPECULATIVE
from .choices import INTENTS, RISKS
from .dimensions import DIMENSIONS
from .probes import CUTTABLE, SENTENCE_PROBES, sentence_docket
from .read import read_docket, read_state

__all__ = [
    "CHECKS",
    "CUTTABLE",
    "DIMENSIONS",
    "INTENTS",
    "RISKS",
    "SENTENCE_PROBES",
    "SPECULATIVE",
    "read_docket",
    "read_state",
    "sentence_docket",
]
