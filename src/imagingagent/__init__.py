"""ImagingAgent — a quantitative imaging pipeline built to be operated by an agent.

The package is organised as layers with clear boundaries:

- ``config``   : what a run should do (typed, loaded from YAML)
- ``storage``  : where bytes live (local disk now; other backends later)
- ``schemas``  : the data contracts every layer exchanges (validated models)
- ``ledger``   : the run history — who ran what, when, with which config
- ``cli``      : the command line, a thin wrapper over the same functions
             that future HTTP or MCP servers call
"""

__version__ = "0.1.0"
