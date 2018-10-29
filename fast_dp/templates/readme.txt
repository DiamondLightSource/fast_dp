XDS.INP file templates
----------------------

These should be named as ${detector}_INDEX.INP and so on, where the detector
is the name of the detector from ADSC, MAR, SATURN, PILATUS. This will be
populated from the contents of the image headers => if these are wrong, we're
screwed anyway.

DETECTORS=ADSC MAR PILATUS SATURN
STEPS=INDEX INTEGRATE CORRECT
