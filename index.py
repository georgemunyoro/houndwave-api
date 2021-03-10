from flask import Flask, request, send_from_directory, abort, send_file
from flask_cors import CORS, cross_origin
import spotipy
import json
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
    search_results = spotify.search(request.args.get("query"), limit=50)
    return {"data": search_results}


@app.route("/download")
def download():
    try:
        artist = request.args.get("artist")
        title = request.args.get("title")

        yt_res = json.loads(YoutubeSearch(f"{artist} {title}", max_results=1).to_json())

        with youtube_dl.YoutubeDL() as ydl:
            return ydl.extract_info("http://www.youtube.com" + yt_res["videos"][0]["url_suffix"], download=False)

    except Exception as e:
        print(e)
        abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", threaded=True, port=5000)
