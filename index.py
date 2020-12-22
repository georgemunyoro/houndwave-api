from flask import Flask, request, send_from_directory, abort, send_file
from flask_cors import CORS, cross_origin
from ytmusicapi import YTMusic
import spotipy
import json
import urllib
import eyed3
import shutil
from dotenv import load_dotenv
from youtube_search import YoutubeSearch
import youtube_dl
import os

load_dotenv()

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
    search_results = spotify.search(request.args.get("query"))
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

        yt_res = json.loads(YoutubeSearch(f"{artist} {title}", max_results=1).to_json())
        yt_id = yt_res["videos"][0]["id"]

        SAVE_DIR = os.getenv('SAVE_DIR')

        ydl_opts = {
            "outtmpl": SAVE_DIR + "%(id)s.%(ext)s",
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            print(["http://www.youtube.com" + yt_res["videos"][0]["url_suffix"]])
            ydl.download(["http://www.youtube.com" + yt_res["videos"][0]["url_suffix"]])

        track_file = eyed3.load(f"{SAVE_DIR}{yt_id}.mp3")
        track_file.tag.artist = str(artist)
        track_file.tag.album = str(album)
        track_file.tag.album_artist = str(metadata["album"]["artists"][0]["name"])
        track_file.tag.title = str(title)
        track_file.tag.track_num = int(metadata["track_number"])

        data = urllib.request.urlopen(image_url).read()

        track_file.tag.images.set(3, data, "image/jpeg", "")
        track_file.tag.save()

        shutil.move(f"{SAVE_DIR}{yt_id}.mp3", f"{SAVE_DIR}{artist} - {title}.mp3")

        return send_file(f"{SAVE_DIR}{artist} - {title}.mp3")
    except Exception as e:
        print(e)
        abort(404)


if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0")
