import os
import random
from flask import Flask, url_for, session, request, redirect, render_template # type: ignore
from flask_session import Session # type: ignore
from datetime import timedelta
import spotipy # type: ignore
from spotipy.oauth2 import SpotifyOAuth # type: ignore
from spotipy.cache_handler import FlaskSessionCacheHandler # type: ignore

# IMPORT .ENV VARIABLES
from dotenv import load_dotenv # type: ignore
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = os.getenv("REDIRECT_URI")

# AUTHORIZATION CODE FLOW EXECUTION
app = Flask(__name__)
app.secret_key = "RANDOM"
app.config["SECRET_KEY"] = "spotify-login-session"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=0.5)
cache_handler = FlaskSessionCacheHandler(session)
Session(app)

@app.route("/")
def home():
    sp_oauth = create_spotify_oauth()
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    return redirect(url_for("game"))

@app.route("/authorize")
def authorize():
    sp_oauth = create_spotify_oauth()
    
    sp_oauth.get_access_token(request.args["code"])
    return redirect(url_for("game"))

@app.route("/get_top_tracks")
def get_top_tracks():
    sp_oauth = create_spotify_oauth()
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    tracks = sp.current_user_top_tracks(limit=50, time_range="short_term")
    tracks_info = [
        {
            "name": track["name"],
            "artist": ", ".join(artist["name"] for artist in track["artists"]),
            "image_url": track["album"]["images"][0]["url"],
            "url": track["external_urls"]["spotify"]
        }
        for track in tracks["items"]]

    return render_template(
        "top_tracks.html",
        tracks = tracks_info
    )

@app.route("/game", methods=["GET", "POST"])
def game():
    sp_oauth = create_spotify_oauth()
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    count = 0
    if "tracks" not in session:
        tracks = sp.current_user_top_tracks(limit=50, time_range="short_term")
        session["tracks"] = []
        for track in tracks["items"]:
            session["tracks"].append({
                "name": track["name"],
                "url": track["external_urls"]["spotify"],
                "rank": count,
                "image_url": track["album"]["images"][0]["url"]
            })
            count += 1
        session["score"] = 0

    message = "Begin by guessing the first song:"

    if request.method == "POST":
        song1 = session["song1"]
        song2 = session["song2"]
        choice = request.form.get("choice")
        if (choice == "1" and song1["rank"] <= song2["rank"]):
            session["score"] += 1
            message = "Correct!"
        elif (choice == "2" and song2["rank"] <= song1["rank"]):
            session["score"] += 1
            message = "Correct!"
        else:
            session["score"] = 0
            message = "Incorrect, start over!"

        if session["score"] == 5:
            message = "Correct, you're halfway there!"

        if session["score"] >= 10:
            return render_template("win.html", score=session["score"])

    tracks = session["tracks"]
    session["song1"], session["song2"] = random.sample(tracks, 2)
    session.modified = True
    return render_template(
        "game.html",
        song1=session["song1"],
        song2=session["song2"],
        score=session["score"],
        message=message
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# MANUAL SPOTIFY OAUTH CREATION
def create_spotify_oauth():
    return SpotifyOAuth(
        client_id = client_id,
        client_secret = client_secret,
        redirect_uri = redirect_uri,
        scope = "user-library-read user-top-read",
        cache_handler = cache_handler,
        show_dialog = True
    )

if __name__ == "__app__":
    app.run()