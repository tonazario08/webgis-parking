import django
import traceback
django.setup()
from django.test import Client

c = Client()
endpoints = [
    '/api/gis/export-geojson/',
    '/api/gis/nearby-parkings/?latitude=10.7720&longitude=106.6996&radius=1',
    '/api/gis/nearest-parking/?latitude=10.7720&longitude=106.6996'
]
for url in endpoints:
    try:
        r = c.get(url)
        print(url, '->', r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.content[:1000])
    except Exception as e:
        print('Exception calling', url)
        traceback.print_exc()
