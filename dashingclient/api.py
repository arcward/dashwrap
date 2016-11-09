import requests
from pymarta.pymarta import Rail
from ticketpy.ticketmaster import Ticketmaster

# Config items for the local Dashing instance
config = {
    'url': 'http://localhost:3030/widgets/',
    'auth_token': 'YOUR_AUTH_TOKEN'
}


class DashingClient:
    """Generic class used to make the final API calls to Dashing"""
    def __init__(self):
        self.base_url = config['url']
        self.api_key = config['auth_token']

    def push(self, widget, data):
        requests.post(self.base_url + widget, json=data)
        
        
class MartaWidget:
    """Wrapper for MARTA API client to grab the next arrivals for a particular station."""
    def __init__(self):
        self.marta = Rail()
    
    def push(self, station):
        arrivals = self.marta.arrivals(station=station)
        # The actual enumerated items in the list
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
        self.tmaster = Ticketmaster()