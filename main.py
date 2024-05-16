#!/usr/bin/python3
import urwid as u
import playsound
import pandas as pd
import requests
import geopandas as gpd
from typing import List
import sys
import asyncio


URL = "https://api.weather.gov/"

# CONFIGURATION
# LIMIT is the cap for number of new alerts. Default is 500
LIMIT = 500
# REGION_TYPE is for whether you want 'land' or 'marine' alerts.
# !! currently not implemented
REGION_TYPE = 'land'
# UPDATE_TIME is the number of seconds between checking for new alerts. Default is 5 minutes
# The NWS API info is here: https://www.weather.gov/documentation/services-web-api#/
UPDATE_TIME = 60
# AREAS is a list of states you want to check for alerts. You can leave it
# empty to recieve alerts for all areas. Use postal codes, ie. 'PA' or 'NM'
AREAS = []
# EVENTS is a list of event types you want to filter for,
# for example 'Red Flag Warning' or 'Tornado Watch'. A complete list of
# Alerts and their definitions can be found here: https://www.weather.gov/lwx/warningsdefined
EVENTS = []
# COLUMNS is a list of columns you wish to appear in the table. The following are available:
VIABLE = ['id', 'areaDesc', 'geocode', 'affectedZones',
          'references', 'sent', 'effective', 'onset', 'expires', 'ends', 'status',
          'messageType', 'category', 'severity', 'certainty', 'urgency', 'event',
          'sender', 'senderName', 'headline', 'description', 'instruction',
          'response', 'parameters', 'geometry']
COLUMNS = ['areaDesc', 'event', 'certainty', 'effective']
# FOCUS_CONTENTS is a list of information you wish to display in the focused alert window.
# The available contents are the same as above for COLUMNS.
FOCUS_CONTENTS = ['effective', 'description']

# COSMETIC
# WEIGHTS are the relative sizes of the Alerts list and the Alert Details reader, respectively:
WEIGHTS = (30, 70)
# COLORS is the palette used to draw the application, using the default 16 colors of your terminal
COLORS = {
    ("bg",               "white", "default"),
    ("alert",          "default", "default"),
    ("alert_selected", "dark blue",       "white"),
    ("header",           "white, bold", "dark blue"),
}

# The UI code was based on this example by Nicolas Seriot:
# https://seriot.ch/urwid/#1_layout_list_details.py


class ListItem(u.WidgetWrap):
    def __init__(self, row: pd.Series):
        self.content = row
        # extract desired data from series and wrap in columns object
        row = u.Columns([u.Text(str(data), align='left', wrap='clip')
                        for data in row[COLUMNS]], dividechars=1)
        r = u.AttrWrap(row, None, 'alert_selected')
        u.WidgetWrap.__init__(self, r)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class ListView(u.WidgetWrap):
    def __init__(self):

        u.register_signal(self.__class__, ['show_details'])
        self.walker = u.SimpleFocusListWalker([])
        lb = u.ListBox(self.walker)
        u.WidgetWrap.__init__(self, lb)

    def modified(self):
        focus_w, _ = self.walker.get_focus()
        u.emit_signal(self, 'show_details', focus_w.content)

    def set_data(self, alerts: pd.DataFrame):
        # account for no alerts
        if len(alerts.index) > 0:
            alert_widgets = [ListItem(r) for i, r in alerts.iterrows()]
        else:
            # create empty dataframe to display
            r1 = pd.DataFrame([['' for i in VIABLE]])
            blank = pd.DataFrame(columns = VIABLE)

            print(blank)
            blank = pd.concat([blank, r1])
            print(blank)
            alert_widgets = [ListItem(r) for i, r in blank.iterrows()]
        u.disconnect_signal(self.walker, 'modified', self.modified)
        while len(self.walker) > 0:
            self.walker.pop()
        self.walker.extend(alert_widgets)
        u.connect_signal(self.walker, "modified", self.modified)
        self.walker.set_focus(0)

    def extend(self, list: List[ListItem]):
        '''retrieve new list of active alerts'''
        # insert each item at beginning of list
        for item in list:
            self.walker.insert(0, item)
        # update walker
        u.connect_signal(self.walker, "modified", self.modified)
        # scroll to top to show new alerts, then return to previous position
        # this exists to keep the detail view on the focused alert after it updates
        _, i = self.walker.get_focus()
        self.walker.set_focus(i)


class DetailView(u.WidgetWrap):
    def __init__(self):
        t = u.Text("")
        u.WidgetWrap.__init__(self, t)

    def set_alert(self, c):
        s = unpack_dictionary(c[FOCUS_CONTENTS])
        self._w.set_text(s)


def unpack_dictionary(d: dict) -> str:
    '''unpacks a dictionary into a long string with headers and bodies'''
    string = ''
    for key in d.keys():
        string += str(key).capitalize() + '\n'
        string += (str(d[key]) + '\n')
        string += ('\n')
    return string


def get_active(area: List[str], event: List[str]) -> pd.DataFrame():
    '''returns list of active alerts from the NWS'''
    # define default api extension
    EXTENSION = f'alerts/active?status=actual&message_type=alert,update&limit={LIMIT}&region_type={REGION_TYPE}'

    # specifying an area is optional
    # if area != []:
    #     EXTENSION += f'&area={",".join(area)}'
    # specifying an event type is optional as well
    # if event != ['']:
    #     EXTENSION += f'&event={",".join(event)}'

    request = requests.get(URL + EXTENSION)
    with open('/dev/null') as sys.stderr:
        df = gpd.read_file(request.text, driver='GeoJSON', utc=True)
    # filter by desired event types:
    if event != []:
        df = df[df.event.isin(event)]
    return df


class App(object):

    def unhandled_input(self, key):
        if key in ('q',):
            raise u.ExitMainLoop()
        if key in ('r',):
            self.set_data()

    def show_details(self, alert):
        self.detail_view.set_alert(alert)

    def __init__(self):

        self.list_view = ListView()
        self.detail_view = DetailView()
        self.alerts = get_active(area=AREAS, event=EVENTS)

        u.connect_signal(self.list_view, 'show_details', self.show_details)

        footer = u.AttrWrap(
            u.Text(" Q to exit - R to clear and refresh - Scroll Up to view new alerts"), "header")

        col_rows = u.raw_display.Screen().get_cols_rows()
        h = col_rows[0] - 2

        f1a = u.Filler(self.list_view, valign='top', height=h)
        f1b = u.AttrWrap(u.Filler(u.Columns([u.Text(str(header).capitalize(
        ), align='left', wrap='clip') for header in COLUMNS], dividechars=1)), 'header')
        f2 = u.ScrollBar(u.Scrollable(self.detail_view))

        f1 = u.Pile([(1, f1b), f1a])
        c_list = u.LineBox(f1, title="Alerts")
        c_details = u.LineBox(f2, title="Alert Details")

        columns = u.Pile([('weight', WEIGHTS[0], c_list),
                         ('weight', WEIGHTS[1], c_details)])

        frame = u.AttrMap(u.Frame(body=columns, footer=footer), 'bg')

        # define loop for requesting updated alerts
        self.asyncloop = asyncio.get_event_loop()

        self.updateloop = u.AsyncioEventLoop(loop=self.asyncloop)
        # self.updateloop.run_in_executor(None, self.update_data)

        self.loop = u.MainLoop(
            frame, COLORS, unhandled_input=self.unhandled_input, event_loop=self.updateloop)
        # create update task
        self.asyncloop.create_task(self.update_data())

    def set_data(self):
        self.list_view.set_data(self.alerts)
        self.loop.screen.clear()

    async def update_data(self):
        '''retrieve new list of active alerts'''
        while True:
            new = await self.asyncloop.run_in_executor(None, get_active, AREAS, EVENTS)
            # compare old and new lists and check for new events
            dif = new[~new.id.isin(self.alerts.id)]
            if len(dif.index) != 0:
                # BELL 0104.wav by zgump -- https://freesound.org/s/83541/ -- License: Creative Commons 0
                playsound.playsound('83541__zgump__bell-0104.wav', block=False)

                # append dif to old alerts list
                self.alerts = pd.concat([dif, self.alerts])
                alert_widgets = [ListItem(r) for i, r in dif.iterrows()]
                self.list_view.extend(alert_widgets)
            self.loop.screen.clear()
            self.loop.draw_screen()

            # wait until update time is over
            await asyncio.sleep(UPDATE_TIME)

    def start(self):

        self.set_data()
        self.list_view.walker.set_focus(0)
        self.loop.run()


if __name__ == '__main__':

    app = App()
    app.start()
