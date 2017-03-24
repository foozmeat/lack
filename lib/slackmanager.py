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

        channel_name = os.environ["SLACK_CHANNEL"]

        response = self._sc.api_call("channels.list", exclude_archived=1)

        for channel in response['channels']:

            if channel['name'] == channel_name:
                self._channel_id = channel['id']
                self.channel_topic = channel['topic']['value']

        # If we're using a private group, search for that next
        if not self._channel_id:
            response = self._sc.api_call("groups.list", exclude_archived=1)
            for group in response['groups']:

                if group['name'] == channel_name:
                    self._channel_id = group['id']
                    self.channel_topic = group['topic']['value']

        if self._channel_id:
            self._sc.api_call("channels.join", channel=self._channel_id)

    def _update_member_cache(self):
        if not self._connected:
            return

        members_source = self._sc.api_call("users.list")['members']

        for member in members_source:
            self._membercache[member['id']] = member['name']

    @asyncio.coroutine
    def send_message(self, msg):
        if not self._connected:
            return
        self._sc.rtm_send_message(self._channel_id, msg)

    @asyncio.coroutine
    def update_messages(self):

        if not self._connected:
            return

        evts = self._sc.rtm_read()

        for evt in evts:
            self.loglines.append((6, str(evt)))

            try:

                if evt.get('type'):

                    if evt['type'] == 'message' and evt['channel'] == self._channel_id:
                        msg_body = "{} {} {}".format(evt['ts'], self._membercache[evt['user']], evt['text'])
                        # print(msg_body)
                        self.loglines.append((3, msg_body))

                elif evt.get('ok') and evt['ok']:

                    msg_body = "{} {} {}".format(evt['ts'], 'me', evt['text'])
                    self.loglines.append((0, msg_body))
            except KeyError:
                self.loglines.append((1, 'Key Error'))

        asyncio.async(self.update_messages())
