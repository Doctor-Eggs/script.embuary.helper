#!/usr/bin/python
# coding: utf-8

########################

import xbmc
import xbmcgui
import random

from resources.lib.utils import split
from resources.lib.helper import *
from resources.lib.player_monitor import PlayerMonitor

# Disable image function for TVOS if ImportError
try:
    from resources.lib.image import *
    PIL_supported = True
except ImportError:
    PIL_supported = False

########################

KODIVERSION = get_kodiversion()

########################


class Main(xbmc.Monitor):

    def __init__(self):
        self.monitor = PlayerMonitor()

        self.service_enabled = get_bool(ADDON.getSetting('service'))
        self.service_interval = xbmc.getInfoLabel('Skin.String(ServiceInterval)') or ADDON.getSetting('service_interval')
        self.service_interval = float(self.service_interval)
        self.restart = False

        self.widget_refresh = 0
        self.get_backgrounds = 200
        self.set_background = xbmc.getInfoLabel('Skin.String(BackgroundInterval)') or ADDON.getSetting('background_interval')
        self.set_background = int(self.set_background)
        self.refresh_audiotracks = 10

        self.blur_background = visible('Skin.HasSetting(BlurEnabled)')
        self.blur_radius = xbmc.getInfoLabel('Skin.String(BlurRadius)') or ADDON.getSetting('blur_radius')
        self.focus_monitor = visible('Skin.HasSetting(FocusMonitor)')

        self.master_lock = None
        self.login_reload = False

        if self.service_enabled:
            self.start()
        else:
            self.keep_alive()


    def onNotification(self, sender, method, data):
        if ADDON_ID in sender and 'restart' in method:
            self.restart = True

        if method == 'VideoLibrary.OnUpdate' or method == 'AudioLibrary.OnUpdate':
            reload_widgets()


    def onSettingsChanged(self):
        log('Service: Addon setting changed', force=True)
        self.restart = True


    def stop(self):
        if self.service_enabled:
            del self.monitor
            log('Service: Stopped', force=True)

        if self.restart:
            log('Service: Applying changes', force=True)
            xbmc.sleep(500) # Give Kodi time to set possible changed skin settings. Just to be sure to bypass race conditions on slower systems.
            DIALOG.notification(ADDON_ID, ADDON.getLocalizedString(32006))
            self.__init__()


    def keep_alive(self):
        log('Service: Disabled')

        while not self.monitor.abortRequested() and not self.restart:
            self.monitor.waitForAbort(5)

        self.stop()


    def start(self):
        log('Service: Started', force=True)

        while not self.monitor.abortRequested() and not self.restart:

            '''Focus monitor to split merged info labels by the default / seperator to properties
            '''
            if self.focus_monitor:
                split({'value': xbmc.getInfoLabel('ListItem.Genre'), 'property': 'ListItem.Genre', 'separator': ' / '})
                split({'value': xbmc.getInfoLabel('ListItem.Country'), 'property': 'ListItem.Country', 'separator': ' / '})
                split({'value': xbmc.getInfoLabel('ListItem.Studio'), 'property': 'ListItem.Studio', 'separator': ' / '})
                split({'value': xbmc.getInfoLabel('ListItem.Director'), 'property': 'ListItem.Director', 'separator': ' / '})
                split({'value': xbmc.getInfoLabel('ListItem.Cast'), 'property': 'ListItem.Cast'})

            ''' Grab fanarts
            '''
            if self.get_backgrounds >= 200:
                log('Start new fanart grabber process')
                movie_fanarts, tvshow_fanarts, artists_fanarts = self.grabfanart()
                self.get_backgrounds = 0

            else:
                self.get_backgrounds += self.service_interval

            ''' Set background properties
            '''
            if self.set_background >= 10:

                if movie_fanarts or tvshow_fanarts or artists_fanarts:
                    winprop('EmbuaryBackground', random.choice(movie_fanarts + tvshow_fanarts + artists_fanarts))
                if movie_fanarts or tvshow_fanarts:
                    winprop('EmbuaryBackgroundVideos', random.choice(movie_fanarts + tvshow_fanarts))
                if movie_fanarts:
                    winprop('EmbuaryBackgroundMovies', random.choice(movie_fanarts))
                if tvshow_fanarts:
                    winprop('EmbuaryBackgroundTVShows', random.choice(tvshow_fanarts))
                if artists_fanarts:
                    winprop('EmbuaryBackgroundMusic', random.choice(artists_fanarts))

                self.set_background = 0

            else:
                self.set_background += self.service_interval

            ''' Blur backgrounds
            '''
            if self.blur_background and PIL_supported:
                image_filter(radius=self.blur_radius)

            ''' Refresh widgets
            '''
            if self.widget_refresh >= 600:
                reload_widgets(instant=True)
                self.widget_refresh = 0

            else:
                self.widget_refresh += self.service_interval

            ''' Workaround for login screen bug
            '''
            if not self.login_reload:
                if visible('System.HasLoginScreen + Skin.HasSetting(ReloadOnLogin)'):
                    log('System has login screen enabled. Reload the skin to load all strings correctly.')
                    execute('ReloadSkin()')
                    self.login_reload = True

            ''' Master lock reload logic for widgets
            '''
            if visible('System.HasLocks'):
                if self.master_lock is None:
                    self.master_lock = visible('System.IsMaster')
                    log('Master mode: %s' % self.master_lock)

                if self.master_lock == True and not visible('System.IsMaster'):
                    log('Left master mode. Reload skin.')
                    self.master_lock = False
                    execute('ReloadSkin()')

                elif self.master_lock == False and visible('System.IsMaster'):
                    log('Entered master mode. Reload skin.')
                    self.master_lock = True
                    execute('ReloadSkin()')

            elif self.master_lock is not None:
                self.master_lock = None

            # Get audio tracks for < Leia
            if PLAYER.isPlayingVideo() and self.refresh_audiotracks >= 10:
                MONITOR.get_audiotracks()
                self.refresh_audiotracks = 0

            elif PLAYER.isPlayingVideo():
                self.refresh_audiotracks += self.service_interval

            else:
                self.refresh_audiotracks += 10

            self.monitor.waitForAbort(self.service_interval)

        self.stop()


    def grabfanart(self):
        movie_fanarts = list()
        tvshow_fanarts = list()
        artists_fanarts = list()

        ''' Movie fanarts
        '''
        try:
            movie_query = json_call('VideoLibrary.GetMovies',
                                properties=['art'],
                                sort={'method': 'random'}, limit=40
                                )

            for art in movie_query['result']['movies']:
                movie_fanart = art['art'].get('fanart')
                if movie_fanart:
                    movie_fanarts.append(movie_fanart)

        except Exception:
            pass

        ''' TV show fanarts
        '''
        try:
            tvshow_query = json_call('VideoLibrary.GetTVShows',
                                properties=['art'],
                                sort={'method': 'random'}, limit=40
                                )
            for art in tvshow_query['result']['tvshows']:
                tvshow_fanart = art['art'].get('fanart')
                if tvshow_fanart:
                    tvshow_fanarts.append(tvshow_fanart)

        except Exception:
            pass

        ''' Music fanarts
        '''
        try:
            artist_query = json_call('AudioLibrary.GetArtists',
                                properties=['fanart'],
                                sort={'method': 'random'}, limit=40
                                )
            for art in artist_query['result']['artists']:
                artist_fanart = art.get('fanart')
                if artist_fanart:
                    artists_fanarts.append(artist_fanart)

        except Exception:
            pass

        return movie_fanarts, tvshow_fanarts, artists_fanarts


if __name__ == '__main__':
    Main()