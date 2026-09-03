"""Torna `history` importável nos testes sem passar pelo __init__.py do pacote.

O __init__.py importa `krita`, um módulo que só existe dentro do Krita. Como
history.py não tem imports relativos, dá para carregá-lo como módulo de topo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recent_brushes"))
