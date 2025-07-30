import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd

SPOTIPY_CLIENT_ID = "4b0c8eeed0da48f69f96f89b7f5507dd"
SPOTIPY_CLIENT_SECRET = "2796f1fefcbc4515872a8c2ac6e0724a"

client_credentials_mgmt = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_mgmt)

artist_uri = 'spotify:artist:2WX2uTcsvV5OnS0inACecP'
artist_uri = "spotify:artist:27LlKWxS3KXW7RRAxN5S8s"

results = sp.artist_albums(artist_uri, album_type='album')
albums = results['items']
while results['next']:
    results = sp.next(results)
    albums.extend(results['items'])

for album in albums:
    print(album['name'])

playlist_link = "https://open.spotify.com/playlist/3KTnYea8wFbVRLYfBeLCLs"

#Peaceful piano
playlist_link = "https://open.spotify.com/playlist/37i9dQZF1DX4sWSpwq3LiO"
playlist_id = "spotify:playlist:37i9dQZF1DX4sWSpwq3LiO"

#Wrapped
playlist_link = "https://open.spotify.com/playlist/37i9dQZF1FoIdd9FX4JNt7"
playlist_id = "spotify:playlist:37i9dQZF1FoIdd9FX4JNt7"

playlist_link = "https://open.spotify.com/playlist/5RIbzhG2QqdkaP24iXLnZX"
playlist_id = "spotify:playlist:5RIbzhG2QqdkaP24iXLnZX"

playlist_link = "https://open.spotify.com/playlist/37i9dQZEVXbLWYFZ5CkSvr"

playlist_id = "spotify:playlist:"+playlist_link.split("/")[-1]

playlist_link = "https://open.spotify.com/playlist/37i9dQZF1DZ06evO03DwPK"

results = sp.playlist_items(playlist_id)

results = sp.playlist_items(pl_id)




# Hent spillelisteinnhold
def get_playlist_items(playlist_id):
    results = sp.playlist_items(playlist_id)
    tracks = results['items']
    #
    # Hent flere spor hvis spillelisten er stor
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    #
    return tracks


def get_track_info(tracks):
    df = pd.DataFrame(columns=['Title', 'Artist'])
    for i, track in enumerate(tracks):
        title = track['track']['name']
        artists = track['track']['artists']
        artists_str = ', '.join([a['name'] for a in artists])
        df.loc[i+1] = [title, artists_str]
    return df
         

tracks = get_playlist_items(playlist_id)
track_info = get_track_info(tracks)
print(track_info)