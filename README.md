lack
=====

A single-channel console slack client suitable for kiosks 

Requirements
------------

The following Python versions are supported:

* Python 3.5+ (for asyncio)

The following third-party libraries are used:

* `slackclient`
* `sortedcontainers`
* `pytz`

Installation
------------

pip -r requirements.txt

Usage
-----

    export SLACK_TOKEN='xoxb-111111111111-AAAAAAAAAAAAAAAAAAAAAAAA'
    export SLACK_CHANNEL='kiosk'
    python -m lack.client


Notes
-----

lack is built using a quasi-MVC structure. The LackScreen class is responsible for drawing the client in an event loop while LackManager communicates with the Slack API and holds the message history. LackManager could be reused in another tool that needed to manage a slack message log.
