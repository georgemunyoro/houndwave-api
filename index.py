from eyed3 import mimetype
from eyed3.core import Date
from mutagen.mp4 import MP4, MP4Cover
from flask import Flask, request, send_from_directory, abort, send_file

from flask_cors import CORS, cross_origin
import spotipy
import json
from dotenv import load_dotenv
from youtube_search import YoutubeSearch
import youtube_dl
import os
from pyyoutube import Api
from subprocess import Popen
import uuid

load_dotenv()

yt_api = Api(api_key=os.getenv("YT_API_KEY"))
SAVE_DIR = os.getenv('SAVE_DIR')
HTTP_SERVER_URL = os.getenv("HTTP_SERVER_URL")

app = Flask(__name__)
CORS(app)


spotify_credentials = spotipy.SpotifyClientCredentials(
    client_id=os.getenv("CLIENT_ID"), client_secret=os.getenv("CLIENT_SECRET")
)
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
    try:
        metadata = spotify.track(spotify_track_id)

        title = metadata["name"]
        album = metadata["album"]["name"]
        date = metadata["album"]["release_date"]
        artist = ", ".join([artist["name"] for artist in metadata["artists"]])
        image_url = metadata["album"]["images"][0]["url"]

        yt_video_id = yt_api.search_by_keywords(q=f"{artist} {title}", search_type=["video"], count=1, limit=1).items[0].id.videoId

        ydl_opts = {
            "outtmpl": SAVE_DIR + "%(id)s.%(ext)s",
            "format": "bestaudio/best",
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }]
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={yt_video_id}"])

        f = MP4(f"{SAVE_DIR}{yt_video_id}.mp4")

        f["\xa9nam"] = str(title)
        f["\xa9alb"] = str(album)
        f["\xa9ART"] = str(artist)
        f["aART"] = str(artist)
        f["\xa9day"] = date.split("-")[0]

        img_data = urllib.request.urlopen(image_url).read()
        f["covr"] = [MP4Cover(img_data, imageformat=MP4Cover.FORMAT_JPEG)]

        f.save()

        shutil.move(f"{SAVE_DIR}{yt_video_id}.mp4", f"{SAVE_DIR}{artist} - {title}.m4a")
        return send_file(f"{SAVE_DIR}{artist} - {title}.m4a", as_attachment=True, mimetype="audio/mp4")

    except Exception as e:
        print(e)
        abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", threaded=True, port=5000)
