import os
import time

import urllib
import spotipy
import requests
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
from flask import Flask, Response, request, send_file
from flask_cors import CORS
from mutagen.mp4 import MP4, MP4Cover
from pyyoutube import Api
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
from flask_prometheus_metrics import register_metrics
from prometheus_client import multiprocess, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST, Gauge, Counter, Histogram
import flask_monitoringdashboard as dashboard
from pydeezer import Deezer
from pydeezer.constants import track_formats


load_dotenv()

yt_api = Api(api_key=os.getenv("YT_API_KEY"))
SAVE_DIR = os.getenv("SAVE_DIR")
HTTP_SERVER_URL = os.getenv("HTTP_SERVER_URL")
INVIDIOUS_INSTANCE = os.getenv('INVIDIOUS_INSTANCE')
DEEZER_ARL = os.getenv("DEEZER_ARL")

PORT = 4000
try:
    PORT = int(os.getenv("PORT"))
except:
    pass

app = Flask(__name__)
dashboard.config.database_name = os.getenv("MONITORING_DB_FILEPATH")
dashboard.bind(app)
CORS(app)

REQUEST_COUNT = Counter(
    "request_count",
    "App Request Count",
    ["prometheus_app", "method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "request_latency_seconds", "Request latency", ["app_name", "endpoint"]
)
CONTENT_TYPE_LATEST = str("text/plain; version=0.0.4; charset=utf-8")

@app.before_request
def before_request():
    request.start_time = time.time()


@app.after_request
def after_request(response):
    resp_time = time.time() - request.start_time
    REQUEST_COUNT.labels(
        "prometheus_app", request.method, request.path, response.status_code
    ).inc()
    REQUEST_LATENCY.labels("prometheus_app", request.path).observe(resp_time)
    return response


spotify_credentials = spotipy.SpotifyClientCredentials(
    client_id=os.getenv("CLIENT_ID"), client_secret=os.getenv("CLIENT_SECRET"))
spotify = spotipy.Spotify(client_credentials_manager=spotify_credentials)

deezer = Deezer(arl=DEEZER_ARL)

@app.route("/")
def index():
    return {
        "message": "ok",
    }


@app.route("/q")
def query():
    search_results = deezer.search_tracks(request.args.get("query"))
    return {"data": search_results}


@app.route("/download/<spotify_track_id>")
def download(spotify_track_id):
    track = deezer.get_track(int(spotify_track_id))
    track["download"](download_dir=SAVE_DIR, filename=spotify_track_id, quality=track_formats.MP3_320)

    return send_file(
        SAVE_DIR + spotify_track_id + ".mp3",
        as_attachment=True,
        download_name=spotify_track_id + ".mp3"
    )


@app.route("/metrics")
def metrics():
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    data = generate_latest(registry)
    return Response(data, mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    register_metrics(app, app_version="0.0.0", app_config="staging")
    dispatcher = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})
    run_simple(hostname="0.0.0.0", port=PORT, threaded=True, application=dispatcher)
