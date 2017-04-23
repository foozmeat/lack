import asyncio
import html
import logging
import os
import re
import sys

from slackclient import SlackClient
from sortedcontainers import SortedDict


class LackManager:
    # loglines = [(0, str(index)) for index, x in enumerate(range(100))]
    loglines = SortedDict()
    channel_topic = ""

    _membercache = {}
    _channelcache = {}
    _rtm_con = None
    _connected = False
    _channel_id = None

    def __init__(self):
        slack_token = os.environ["SLACK_API_TOKEN"]
        self.username = os.getenv("SLACK_USERNAME", "Anonymous")
        self.channel_name = os.environ["SLACK_CHANNEL"]
        self._debug = bool(os.getenv("SLACK_DEBUG", False))
        self.username_re = re.compile('(U[A-Z0-9]{8})')

        if self._debug:
            self.logger = logging.getLogger('debug')
            self.logger.addHandler(logging.FileHandler('/tmp/lack_debug.log'))
            self.logger.setLevel(logging.DEBUG)

        self._sc = SlackClient(slack_token)
        asyncio.ensure_future(self._connect())

    @asyncio.coroutine
    def _connect(self):
        if self._sc.rtm_connect():
            self._connected = True
            # print("Connected")
            self._update_member_cache()
            self._update_channel_cache()
            self._fetch_history()
            asyncio.ensure_future(self.update_messages())
        else:
            print("Connection Failed, invalid token?")
            sys.exit(1)

    def _update_channel_cache(self):
        if not self._connected:
            return

        response = self._sc.api_call("channels.list", exclude_archived=1)

        for channel in response['channels']:

            if channel['name'] == self.channel_name:
                self._channel_id = channel['id']
                self.channel_topic = channel['topic']['value']

        # If we're using a private group, search for that next
        if not self._channel_id:
            response = self._sc.api_call("groups.list", exclude_archived=1)
            for group in response['groups']:

                if group['name'] == self.channel_name:
                    self._channel_id = group['id']
                    self.channel_topic = group['topic']['value']

    def _update_member_cache(self):
        if not self._connected:
            return

        members_source = self._sc.api_call("users.list")['members']

        color = 1

        for member in members_source:
            self._membercache[member['id']] = {
                'n': member['name'],
                'c': color,
            }

            color += 1
            if color == 7:
                color = 9
            elif color == 15:
                color = 1

    def _fetch_history(self):

        method = "channels.history"

        if self._channel_id[0] == 'G':
            method = "groups.history"

        response = self._sc.api_call(method, channel=self._channel_id)

        history = response['messages']

        for evt in history:
            self._process_event(evt, filter_channel=False)

    def _add_logline(self, color, ts, name, text):

        text = html.unescape(text)

        result = re.findall(self.username_re, text)

        for r in result:
            text = re.sub('<@' + r + '>', '@' + self._membercache[r]['n'], text)

        self.loglines[str(ts)] = (color, name, text)

    def _process_event(self, evt, filter_channel=True):

        if self._debug:
            # ts = float(evt['ts']) - 0.000001  # need to offset the ts or it gets overwritten
            # self._add_logline(6, ts, 'DEBUG', str(evt))
            self.logger.log(logging.DEBUG, str(evt))

        try:

            if evt.get('type') and evt['type'] == 'message':
                if not filter_channel or (filter_channel and evt['channel'] == self._channel_id):

                    if evt.get('message'):  # message has been edited
                        m = evt['message']
                        orig_ts = m['ts']
                        user = m['user']
                        text = m['text'] + " (edited)"
                        self._add_logline(self._membercache[user]['c'],
                                          orig_ts,
                                          self._membercache[user]['n'],
                                          text)

                    elif evt.get('deleted_ts'):
                        del self.loglines[evt['deleted_ts']]

                    elif evt.get('user'):
                        # messages from other users
                        self._add_logline(self._membercache[evt['user']]['c'],
                                          evt['ts'],
                                          self._membercache[evt['user']]['n'],
                                          evt['text'])

                    else:
                        # messages from us
                        self._add_logline(7, evt['ts'], evt['username'], evt['text'])

        except KeyError as e:
            pass
            # self.loglines.append((1, 'Key Error: {}'.format(e)))

    @asyncio.coroutine
    def send_message(self, msg):

        if not self._connected:
            return

        self._sc.api_call("chat.postMessage",
                          channel=self._channel_id,
                          text=msg,
                          username=self.username,
                          )

    @asyncio.coroutine
    def update_messages(self):

        if not self._connected:
            return

        yield from asyncio.sleep(0.025)  # 24 fps
        evts = self._sc.rtm_read()

        for evt in evts:
            self._process_event(evt)

        asyncio.ensure_future(self.update_messages())
