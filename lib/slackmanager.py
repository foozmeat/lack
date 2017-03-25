import asyncio
import os

import sys
from slackclient import SlackClient
import time


class SlackManager:

    # loglines = [(0, str(index)) for index, x in enumerate(range(100))]
    loglines = []
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

        if self._debug:
            self._add_logline(6, 0, '', 'DEBUGGING ENABLED')

        self._sc = SlackClient(slack_token)
        self._connect()

    def _connect(self):
        if self._sc.rtm_connect():
            self._connected = True
            # print("Connected")
            self._update_member_cache()
            self._update_channel_cache()
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

        for member in members_source:
            self._membercache[member['id']] = member['name']

    def _add_logline(self, color, ts, name, text):
        msg_body = "{} {} {}".format(ts, name, text)
        self.loglines.append((color, msg_body))

    @asyncio.coroutine
    def send_message(self, msg):
        if not self._connected:
            return
        response = self._sc.api_call("chat.postMessage",
                                     channel=self._channel_id,
                                     text=msg,
                                     username=self.username,
                                     )
        self.loglines.append((6, str(response)))

    @asyncio.coroutine
    def update_messages(self):

        if not self._connected:
            return

        evts = self._sc.rtm_read()

        for evt in evts:

            if self._debug:
                self.loglines.append((6, str(evt)))

            try:

                if evt.get('type') and evt['type'] == 'message' and evt['channel'] == self._channel_id:

                    if evt.get('user'):
                        # messages from other users
                        self._add_logline(3, evt['ts'], self._membercache[evt['user']], evt['text'])

                    else:
                        # messages from us
                        self._add_logline(0, evt['ts'], evt['username'], evt['text'])

            except KeyError as e:
                self.loglines.append((1, 'Key Error: {}'.format(e)))

        asyncio.async(self.update_messages())
