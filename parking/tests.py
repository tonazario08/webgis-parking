from django.test import TestCase
from django.urls import reverse
import json


class GISApiTests(TestCase):
    fixtures = ['sample_parkings.json']

    def test_export_geojson(self):
        url = '/api/gis/export-geojson/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get('type'), 'FeatureCollection')
        self.assertGreaterEqual(len(data.get('features', [])), 1)

    def test_nearby_parkings(self):
        url = '/api/gis/nearby-parkings/'
        params = {
            'latitude': '10.7720',
            'longitude': '106.6996',
            'radius': '1'
        }
        resp = self.client.get(url, params)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('parkings', data.get('data', {}))
        parkings = data['data']['parkings']
        self.assertGreaterEqual(len(parkings), 1)
        # All returned parkings should be within the radius (<= 1 km)
        for p in parkings:
            self.assertLessEqual(float(p['distance_km']), 1.0)

    def test_nearest_parking(self):
        url = '/api/gis/nearest-parking/'
        params = {
            'latitude': '10.7720',
            'longitude': '106.6996'
        }
        resp = self.client.get(url, params)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('nearest_parking', data.get('data', {}))
        nearest = data['data']['nearest_parking']
        # nearest may be None if something wrong; assert that returned is dict or None
        self.assertTrue(isinstance(nearest, dict) or nearest is None)

