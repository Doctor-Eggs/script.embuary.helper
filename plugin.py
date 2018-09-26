#!/usr/bin/python
import sys
import xbmc
import xbmcgui
import xbmcaddon
import urlparse

from resources.lib.plugin_content import *
from resources.lib.utils import *

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_LANGUAGE = ADDON.getLocalizedString
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
WINDOW = xbmcgui.Window(10000)

class Main:

    def __init__(self):
        self._parse_argv()
        self.info = self.params.get("info")
        self.action = self.params.get("action")
        if self.info:
            self.getinfos()
        if self.action:
            self.actions()

    def _parse_argv(self):
        base_url = sys.argv[0]
        path = sys.argv[2]
        try:
            self.params = dict(urlparse.parse_qsl(path[1:]))
        except Exception:
            self.params = {}

    def getinfos(self):
        li = list()
        plugin = PluginContent(self.params,li)

        if self.info == 'getcast':
            plugin.get_cast()
        elif self.info == 'getsimilar':
            plugin.get_similar()
        elif self.info == 'getgenre':
            plugin.get_genre()
        elif self.info == 'getinprogress':
            plugin.get_inprogress()
        elif self.info == 'jumptoletter':
            plugin.jumptoletter()

        xbmcplugin.addDirectoryItems(int(sys.argv[1]), li)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def actions(self):
        if self.action == "smsjump":
            smsjump(self.params.get("letter"))
        elif self.action == "jumptoshow":
            jumptoshow(self.params)

if __name__ == "__main__":
    Main()