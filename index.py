import os
import time

import urllib
import spotipy
import requests
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
from flask import Flask, request, send_file
from flask_cors import CORS
from mutagen.mp4 import MP4, MP4Cover
from werkzeug.serving import run_simple
import sentry_sdk
import git
from sentry_sdk.integrations.flask import FlaskIntegration

load_dotenv()

BUILD_SHA: str = "unknown"

try:
    BUILD_SHA = git.Repo(search_parent_directories=True).head.object.hexsha[:7]
except:
    if os.getenv("BUILD_SHA") is not None:
        BUILD_SHA = os.getenv("BUILD_SHA")

SENTRY_DSN: str = os.getenv("SENTRY_DSN")
ENVIRONMENT: str = os.getenv("ENVIRONMENT")

print(f"Running server build {BUILD_SHA} in {ENVIRONMENT} environment")


def traces_sampler(sampling_context):
    return True


if SENTRY_DSN is not None and ENVIRONMENT is not None and BUILD_SHA is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        environment=ENVIRONMENT,
        release=BUILD_SHA,
        integrations=[
            FlaskIntegration(),
        ],
        _experiments={
            "profiles_sample_rate": 1.0,
        },
        traces_sampler=traces_sampler,
    )


SAVE_DIR = os.getenv("SAVE_DIR")
HTTP_SERVER_URL = os.getenv("HTTP_SERVER_URL")
INVIDIOUS_INSTANCE = os.getenv("INVIDIOUS_INSTANCE")

PORT = 5000
try:
    PORT = int(os.getenv("PORT"))
except:
    pass

app = Flask(__name__)
CORS(app)


@app.before_request
def before_request():
    request.start_time = time.time()


spotify_credentials = spotipy.SpotifyClientCredentials(
    client_id=os.getenv("CLIENT_ID"), client_secret=os.getenv("CLIENT_SECRET")
)
spotify = spotipy.Spotify(client_credentials_manager=spotify_credentials)


@app.route("/version")
def version():
    return {
        "version": BUILD_SHA,
    }


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
    try:
        metadata = spotify.track(spotify_track_id)

        title = metadata["name"]
        album = metadata["album"]["name"]
        date = metadata["album"]["release_date"]
        artist = ", ".join([artist["name"] for artist in metadata["artists"]])
        album_artists = ", ".join(
            [artist["name"] for artist in metadata["album"]["artists"]]
        )
        image_url = metadata["album"]["images"][0]["url"]

        yt_video_id = requests.get(
            f"{INVIDIOUS_INSTANCE}/api/v1/search",
            params={"q": f"{artist} {title}"},
        ).json()[0]["videoId"]

        ydl_opts = {
            "outtmpl": SAVE_DIR + "%(id)s.%(ext)s",
            "format": "bestaudio/best",
            "postprocessors": [
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
            ],
        }

        if (PROXY_URL := os.getenv("PROXY_URL")) is not None:
            ydl_opts["proxy"] = PROXY_URL

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
            filename, as_attachment=True, download_name=f"{artist} - {title}.mp4"
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(e)
        return {"error": str(e)}


if __name__ == "__main__":
    run_simple(hostname="0.0.0.0", port=PORT, threaded=True, application=app.wsgi_app)
