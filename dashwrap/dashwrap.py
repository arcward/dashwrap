"""
MIT License

Copyright (c) 2016 - Edward Wells

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import configparser

import requests
from martapy.martapy import Rail
from ticketpy.ticketmaster import Ticketmaster
from configparser import ConfigParser
import os
import click
import datetime
import praw

# config.ini should have all relevant data (api keys, urls, various IDs..)
api_config = ConfigParser()
api_config.read(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'config.ini'
    )
)


class DashingClient:
    """Generic class used to make the final API calls to Dashing"""
    
    def __init__(self):
        """Initialize class with server URL and auth token from config.ini"""
        self.base_url = api_config.get('dashing', 'url')
        self.api_key = api_config.get('dashing', 'auth_token')
    
    def push(self, widget, data):
        """Sends POST request to a Dashing widget

        :param widget: Name of the target widget
        :param data: Data to send
        """
        requests.post(self.base_url + widget, json=data)


class MartaWidget:
    """Wrapper for MARTA API client to grab the next arrivals for a particular station."""
    
    def __init__(self):
        self.marta = Rail(api_config.get('marta', 'api_key'))
        self.dashing_token = api_config.get('dashing', 'auth_token')
        
    def push(self, station):
        """Get station arrivals, parse for widget-relevant information and post to the dashboard.
        :param station: Station name (or partial station name) to search
        """
        arrivals = self.marta.arrivals(station=station)
        # Dashboard will only show the destination and waiting time (ex: "Airport":"Boarding"
        list_items = [{
                          'label': event['DESTINATION'],
                          'value': event['WAITING_TIME']
                      } for event in arrivals]
        # Additional info (list's title, request auth token, 'last updated' is automatic...)
        list_container = {
            'auth_token': self.dashing_token,
            'title': "Station: {}".format(station),
            'items': list_items
        }
        DashingClient().push('marta', list_container)


class TicketWidget:
    """Wrapper for Ticketmaster API client to grab upcoming events for a venue"""
    def __init__(self):
        self.tmaster = Ticketmaster(api_config.get('ticketmaster', 'api_key'))
        self.dashing_token = api_config.get('dashing', 'auth_token')
    
    def get(self, venue):
        """Match venue name to something in config.ini (prepopulated) and grab the first 7 events."""
        if api_config.has_option('venues', venue):
            return self.tmaster.events(api_config.get('venues', venue), size=7)
        else:
            click.echo("Venue: {} not found in config.ini. Typo?")
        
    def push(self, venue_name, event_list, max_name_length=45, widget_name=None):
        """Send event list data to the Dashing widget. By default, assumes the widget's
        name is the same as the venue name.
        :param venue_name: name of the venue in config.ini
        :param event_list: list of events
        :param max_name_length: where to truncate event titles to fit inside widget dimensions
        :param widget_name: name of the widget to send to (defaults to venue_name)
        """
        if widget_name is None:
            widget_name = venue_name
        # Date returned is in format YYYY-MM-DD ('2017-04-28') and converted to Mon-DD ('Apr-28')
        list_items = [{
            'label': event['name'][:max_name_length] + "..."
                if len(event['name']) > max_name_length else event['name'],
            'value': datetime.datetime.strptime(event['start_date'], '%Y-%m-%d').strftime('%b-%d')
        } for event in event_list]
        list_container = {
            'auth_token': self.dashing_token,
            'title': 'Events: {}'.format(venue_name),
            'items': list_items
        }
        DashingClient().push(venue_name, list_container)
        

class AtlRedditBot():
    """Pulls the top post from /r/Atlanta"""
    def __init__(self):
        user_agent = "/r/ATL daily top posts grabber by /u/shhhh"  # TODO update
        self.atlbot = praw.Reddit(user_agent=user_agent)
        self.atl_sub = self.atlbot.get_subreddit('atlanta')
        self.dashing_token = api_config.get('dashing', 'auth_token')
    
    def top_post_daily(self, limit=1):
        posts = self.atlbot.get_subreddit('atlanta').get_top_from_day(limit=limit, fetch=True)
        # TODO update to actually handle >1 post
        for post in posts:
            top_post = {
                'title': str(post),
                'user': "/u/{}".format(str(post.author)),
                'selftext': (str(post.selftext) if post.selftext is not None else '')
            }
        return top_post

    def push(self, post):
        widget_data = {
            'auth_token': self.dashing_token,
            'text': post['title'],
            'moreinfo': '{} ... posted by {}'.format(post['selftext'], post['user'])
        }
        DashingClient().push('reddit', widget_data)


@click.group()
def push():
    pass


@push.command()
def reddit():
    redbot = AtlRedditBot()
    top_post = redbot.top_post_daily()
    redbot.push(top_post)


@push.command()
@click.option('--station', help="MARTA station to return")
def marta(station):
    mw = MartaWidget()
    mw.push(station)


@push.command()
@click.option('--venue', default='tabernacle', help="Venue to look up")
def ticketmaster(venue):
    tw = TicketWidget()
    event_list = tw.get(venue)
    tw.push(venue, event_list)


if __name__ == '__main__':
    push()

