import json
import os
import uuid
from subprocess import Popen

import shutil
import urllib
import spotipy
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
from eyed3 import mimetype
from eyed3.core import Date
from flask import abort
from flask import Flask
from flask import request
from flask import send_file
from flask import send_from_directory
from flask_cors import CORS
from flask_cors import cross_origin
from mutagen.mp4 import MP4
from mutagen.mp4 import MP4Cover
from pyyoutube import Api
from youtube_search import YoutubeSearch
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
from flask_prometheus_metrics import register_metrics

load_dotenv()

yt_api = Api(api_key=os.getenv("YT_API_KEY"))
SAVE_DIR = os.getenv("SAVE_DIR")
HTTP_SERVER_URL = os.getenv("HTTP_SERVER_URL")

PORT = int(os.getenv("PORT"))
if (PORT is None): PORT = 5000

app = Flask(__name__)
CORS(app)

spotify_credentials = spotipy.SpotifyClientCredentials(
    client_id=os.getenv("CLIENT_ID"), client_secret=os.getenv("CLIENT_SECRET"))
spotify = spotipy.Spotify(client_credentials_manager=spotify_credentials)


@app.route("/")
def index():
    return {
        "message": "ok",
    }


@app.route("/q")
def query():
    search_results = spotify.search(request.args.get("query"), limit=50)
    return {"data": search_results}


@app.route("/download/<spotify_track_id>")
def download(spotify_track_id):
    metadata = spotify.track(spotify_track_id)

    title = metadata["name"]
    album = metadata["album"]["name"]
    date = metadata["album"]["release_date"]
    artist = ", ".join([artist["name"] for artist in metadata["artists"]])
    album_artists = ", ".join([artist["name"] for artist in metadata["album"]["artists"]])
    image_url = metadata["album"]["images"][0]["url"]
    track_num = metadata["track_number"]
    total_tracks = metadata["album"]["total_tracks"]
    disc_num = metadata["disc_number"]
    total_discs = metadata["disc_number"]

    yt_video_id = (yt_api.search_by_keywords(q=f"{artist} {title}",
                                             search_type=["video"],
                                             count=1,
                                             limit=1).items[0].id.videoId)

    ydl_opts = {
        "outtmpl":
        SAVE_DIR + "%(id)s.%(ext)s",
        "format":
        "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4"
        }],
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={yt_video_id}"])

    filename = f"{SAVE_DIR}{yt_video_id}.mp4"
    print(filename)

    f = MP4(filename)

    f["\xa9nam"] = str(title)
    f["\xa9alb"] = str(album)
    f["\xa9ART"] = str(artist)
    f["aART"] = str(album_artists)
    f["\xa9day"] = date.split("-")[0]

    img_data = urllib.request.urlopen(image_url).read()
    f["covr"] = [MP4Cover(img_data, imageformat=MP4Cover.FORMAT_JPEG)]

    f.save()

    return send_file(
        filename,
        as_attachment=True,
        download_name=f"{artist} - {title}.mp4"
    )


if __name__ == "__main__":
    register_metrics(app, app_version="0.0.0", app_config="staging")
    dispatcher = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})
    run_simple(hostname="0.0.0.0", port=PORT, threaded=True, application=dispatcher)
