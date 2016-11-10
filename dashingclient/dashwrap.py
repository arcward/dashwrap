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

import requests
from martapy.martapy import Rail
from ticketpy.ticketmaster import Ticketmaster
from configparser import ConfigParser
import os
import click

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
        self.marta = Rail(api_config('marta', 'api_key'))
    
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
        self.tmaster = Ticketmaster(api_config('ticketmaster', 'api_key'))
    
    def get(self, venue):
        """Match venue name to something in config.ini (prepopulated) and grab the first 7 events."""
        venue_id = api_config('venues', venue)
        return self.tmaster.events(venue_id, size=7)
    
    def push(self, event_list):
        # TODO send to widget
        pass
    
    
@click.group()
def push():
    pass


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
    tw.push(venue)
    
    
if __name__ == '__main__':
    push()

