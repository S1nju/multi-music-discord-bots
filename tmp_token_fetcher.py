import sys
import subprocess
try:
    import pytubefix
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "pytubefix"])
    import pytubefix

from pytubefix.innertube import InnerTube
from pytubefix import YouTube

# Fetching token
yt = YouTube('https://www.youtube.com/watch?v=dQw4w9WgXcQ', use_po_token=True)
try:
    print(f"PO_TOKEN: {yt.po_token}")
except:
    pass

try:
    print(f"VISITOR_DATA: {yt.innertube.client['visitorData']}")
except Exception as e:
    print(f"Visitor err: {e}")
