lack
=====

A text-only slack client.

Requires Python 3.5+ for asyncio

Installation
------------

pip -r requirements.txt

Usage
-----

lack requires a few environment variables be set.

    export SLACK_TOKEN='xoxb-111111111111-AAAAAAAAAAAAAAAAAAAAAAAA'
    export SLACK_CHANNEL='kiosk'
    export SLACK_TZ=US/Pacific

    python -m lack.client


Notes
-----

lack is built using a quasi-MVC structure. The LackScreen class is responsible for drawing the client in an event loop while LackManager communicates with the Slack API and holds the message history. LackManager could be reused in another tool that needed to manage a slack message log.
