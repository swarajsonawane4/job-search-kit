# Resume tracks

Two or three complete base CVs, each ready to send on its own. Tailoring for a posting
starts by copying the closest one (tools/newrole.py does this), never from a blank page.

setup.sh creates three placeholder files here. In the first session Claude builds them
from profile/master-profile.yaml, each leading with a different strength, for example:

- ai.tex          agents, LLMs, RAG first
- ml.tex          models, training, evaluation first
- engineering.tex your domain background (mechanical, electrical, ...) plus ML

Your tracks hold your CV, so they are git-ignored like the rest of your details.
Rename tracks to fit you by editing TRACKS in tools/newrole.py. Fix a wrong fact in the
track itself, not only in one role's copy, or it spreads to every later application.
