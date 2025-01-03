import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --- Configuration ---
SPOTIPY_CLIENT_ID = st.secrets["SPOTIPY_CLIENT_ID"]
SPOTIPY_CLIENT_SECRET = st.secrets["SPOTIPY_CLIENT_SECRET"]

if "RUNNING_ON_STREAMLIT" in st.secrets:
    SPOTIPY_REDIRECT_URI = st.secrets["STREAMLIT_URL"] + "/callback"
else:
    SPOTIPY_REDIRECT_URI = "http://localhost:8501/callback"

SCOPE = "playlist-read-private playlist-read-collaborative"  # Add other scopes as needed

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
        url_params = st.query_params()
        code = url_params.get("code")
        if code:
            token_info = sp_oauth.get_access_token(code[0]) # get the first element of the list
            st.experimental_set_query_params({}) # clear params so the url doesn't look bad
            st.experimental_rerun() # rerun the app
    except Exception as e:
        st.write(f"Error during authorization: {e}")

# --- Spotify API Interaction (after authorization) ---
if token_info:
    sp = spotipy.Spotify(auth=token_info["access_token"])
    user = sp.me()
    st.write(f"Logged in as {user['display_name']}")

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
        
        #Display Tracks for selected playlists
        for i, playlist_tracks in enumerate(tracks):
            st.write(f"Tracks in {selected_playlists[i]}:")
            for track_item in playlist_tracks:
                track = track_item['track']
                if track:
                    st.write(f"- {track['name']} by {track['artists'][0]['name']}")
        
        #Comparison Logic
        from thefuzz import fuzz
        def compare_tracks(track1, track2):
            title_similarity = fuzz.ratio(track1['track']['name'].lower(), track2['track']['name'].lower())
            artist_similarity = fuzz.ratio(track1['track']['artists'][0]['name'].lower(), track2['track']['artists'][0]['name'].lower())
            overall_similarity = (title_similarity * 0.6) + (artist_similarity * 0.4)
            return overall_similarity

        if len(tracks) == 2: # only compare if two playlists are selected
            st.write("Comparison:")
            for track1 in tracks[0]:
                for track2 in tracks[1]:
                    similarity = compare_tracks(track1, track2)
                    if similarity > 50: # only show similarities above 50%
                        st.write(f"Similarity between {track1['track']['name']} and {track2['track']['name']}: {similarity:.2f}%")
        elif len(tracks) > 2:
            st.write("Please select only two playlists for comparison.")
        else:
            st.write("Please select two playlists for comparison.")