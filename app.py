import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd

# --- Configuration ---
SPOTIPY_CLIENT_ID = st.secrets["SPOTIPY_CLIENT_ID"]
SPOTIPY_CLIENT_SECRET = st.secrets["SPOTIPY_CLIENT_SECRET"]

if "RUNNING_ON_STREAMLIT" in st.secrets:
    SPOTIPY_REDIRECT_URI = st.secrets["STREAMLIT_URL"] + "/callback"
else:
    SPOTIPY_REDIRECT_URI = "http://localhost:8501/callback"

SCOPE = "playlist-read-private playlist-read-collaborative"

# --- OAuth Flow ---
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope=SCOPE)

token_info = sp_oauth.get_cached_token()

if not token_info:
    auth_url = sp_oauth.get_authorize_url()
    st.write(f"[Authorize Spotify]({auth_url})")

    try:
        url_params = st.query_params
        code = url_params.get("code")

        print(f"url_params: {url_params}")
        print(f"code: {code}")

        if code:
            if isinstance(code, list):
                code = code[0]
            token_info = sp_oauth.get_access_token(code)
            st.query_params.clear()
            st.experimental_rerun()
    except Exception as e:
        st.error(f"Error during authorization: {e}")

# --- Spotify API Interaction ---
if token_info:
    sp = spotipy.Spotify(auth=token_info["access_token"])
    user = sp.me()
    st.write(f"Logged in as {user['display_name']}")

    try:  # This try block was missing its closing part
        playlists = sp.current_user_playlists()
        selected_playlists = st.multiselect("Select Playlists to Compare", options=[playlist['name'] for playlist in playlists['items']], default=None)
        playlist_ids = [playlist['id'] for playlist in playlists['items'] if playlist['name'] in selected_playlists]

        if len(playlist_ids) == 2:
            playlist1_tracks = []
            playlist2_tracks = []

            for i, playlist_id in enumerate(playlist_ids):
                results = sp.playlist_items(playlist_id)
                tracks_in_playlist = results['items']
                while results['next']:
                    results = sp.next(results)
                    tracks_in_playlist.extend(results['items'])
                if i == 0:
                    playlist1_tracks = tracks_in_playlist
                else:
                    playlist2_tracks = tracks_in_playlist

            playlist1_track_ids = {track['track']['id']: track['track']['name'] for track in playlist1_tracks if track['track']}
            playlist2_track_ids = {track['track']['id']: track['track']['name'] for track in playlist2_tracks if track['track']}

            # Find tracks only in playlist 1
            only_in_playlist1 = {id: name for id, name in playlist1_track_ids.items() if id not in playlist2_track_ids}

            # Find tracks only in playlist 2
            only_in_playlist2 = {id: name for id, name in playlist2_track_ids.items() if id not in playlist1_track_ids}

            # Find common tracks
            common_tracks = {id: name for id, name in playlist1_track_ids.items() if id in playlist2_track_ids}

            st.write("Tracks only in Playlist 1:")
            if only_in_playlist1:
                for id, name in only_in_playlist1.items():
                    st.write(f"- {name}")
            else:
                st.write("None")

            st.write("\nTracks only in Playlist 2:")
            if only_in_playlist2:
                for id, name in only_in_playlist2.items():
                    st.write(f"- {name}")
            else:
                st.write("None")

            st.write("\nCommon Tracks:")
            if common_tracks:
                for id, name in common_tracks.items():
                    st.write(f"- {name}")
            else:
                st.write("None")

        elif len(playlist_ids) > 2:
            st.write("Please select only two playlists for comparison.")
        else:
            st.write("Please select two playlists for comparison.")

    except spotipy.exceptions.SpotifyException as e:  # Added the except block
        st.error(f"Error during Spotify interaction: {e}")