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

        print(f"url_params: {url_params}")  # Print the entire dictionary
        print(f"code: {code}")  # Print the retrieved code

        if code:
            if isinstance(code, list):
                code = code[0]
            token_info = sp_oauth.get_access_token(code)
            st.experimental_set_query_params({})
            st.experimental_rerun()
    except Exception as e:
        st.error(f"Error during authorization: {e}")

# --- Spotify API Interaction ---
if token_info:
    sp = spotipy.Spotify(auth=token_info["access_token"])
    user = sp.me()
    st.write(f"Logged in as {user['display_name']}")

    try:
        playlists = sp.current_user_playlists()
        selected_playlists = st.multiselect("Select Playlists to Compare", options=[playlist['name'] for playlist in playlists['items']], default=None)
        playlist_ids = [playlist['id'] for playlist in playlists['items'] if playlist['name'] in selected_playlists]

        if playlist_ids:
            tracks = []
            for playlist_id in playlist_ids:
                results = sp.playlist_items(playlist_id)
                tracks_in_playlist = results['items']
                while results['next']:
                    results = sp.next(results)
                    tracks_in_playlist.extend(results['items'])
                tracks.append(tracks_in_playlist)

            # Comparison Logic
            from thefuzz import fuzz
            def compare_tracks(track1, track2):
                title_similarity = fuzz.ratio(track1['track']['name'].lower(), track2['track']['name'].lower())
                artist_similarity = fuzz.ratio(track1['track']['artists'][0]['name'].lower(), track2['track']['artists'][0]['name'].lower())
                overall_similarity = (title_similarity * 0.6) + (artist_similarity * 0.4)
                return overall_similarity

            if len(tracks) == 2:
                comparison_results = []
                for track1 in tracks[0]:
                    for track2 in tracks[1]:
                        similarity = compare_tracks(track1, track2)
                        if similarity > 50:
                            comparison_results.append({
                                "Track 1": track1['track']['name'],
                                "Track 2": track2['track']['name'],
                                "Similarity": f"{similarity:.2f}%"
                            })
                if comparison_results:  # check if there are any results before creating the dataframe
                    df = pd.DataFrame(comparison_results)
                    st.dataframe(df)
                else:
                    st.write("No similar tracks found above 50%.")
            elif len(tracks) > 2:
                st.write("Please select only two playlists for comparison.")
            else:
                st.write("Please select two playlists for comparison.")

    except spotipy.exceptions.SpotifyException as