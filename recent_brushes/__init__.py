from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita

from .docker import RecentBrushesDocker
from .tracker import get_tracker

DOCKER_ID = "recent_brushes"

Krita.instance().addExtension(get_tracker())
Krita.instance().addDockWidgetFactory(
    DockWidgetFactory(DOCKER_ID,
                      DockWidgetFactoryBase.DockPosition.DockRight,
                      RecentBrushesDocker))
