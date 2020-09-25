from app.main.utils import *
from app.models import Master, Adds
from flask import abort, current_app
import requests
import plotly
import plotly.graph_objs as go
import json


class Track:

    def __init__(self, track):
        self.track = track
        self.id = track['id']
        self.uri = track['uri']
        self.name = track['name']
        self.artist = track['artists'][0]['name']

    def __str__(self):
        return f"{self.name} - {self.artist}"

    def __repr__(self):
        return f"Track: {self.name}, {self.id}"


def get_profile():
    token = get_access_token()
    endpoint = 'https://api.spotify.com/v1/me'
    headers = {'Authorization': f'Bearer {token}'}
    me = requests.get(endpoint, headers=headers).json()
    return me


def get_top(top_type, limit=50, offset=0, top_term='long_term'):
    token = get_access_token()
    top_url = f'https://api.spotify.com/v1/me/top/{top_type}'
    top_headers = {
        'Authorization': f'Bearer {token}'
    }
    top_params = {
        'limit': limit,
        'offset': offset,
        'time_range': top_term
    }
    top_endpoint = f'{top_url}?{urlencode(top_params)}'
    user_top = requests.get(top_endpoint, headers=top_headers).json()
    if invalid_request(user_top):
        abort(500)
    else:
        return user_top


def get_top_tracks(limit=50, offset=0, top_term='long_term'):
    tracks = get_top('tracks', limit=limit, offset=offset, top_term=top_term)
    return [Track(track) for track in tracks['items']]


def create_empty_playlist(user_id, pl_name, pl_public, pl_description):
    token = get_access_token()
    url = f'https://api.spotify.com/v1/users/{user_id}/playlists'
    header = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    body = {
        'name': pl_name,
        'public': pl_public,
        'description': pl_description
    }
    body_json = json.dumps(body)
    resp = requests.post(url, headers=header, data=body_json)
    playlist_id = resp.json()['id']
    return playlist_id


def make_playlist(user_id, pl_name, pl_public, pl_description, track_uris):
    token = get_access_token()
    playlist_id = create_empty_playlist(user_id, pl_name, pl_public, pl_description)
    add_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    add_body = json.dumps({
        'uris': track_uris
    })
    res = requests.post(add_url, headers=headers, data=add_body).json()
    return res


def curate_playlist(term, pl_length):
    if pl_length <= 0:
        abort(500)
    batch_size = 4
    pl_length = min(pl_length, 100)
    d, r = divmod(pl_length, batch_size)
    token = get_access_token()
    top = get_top_tracks(limit=(d+1 if r else d), offset=0, top_term=f'{term}_term')
    top_ids = [s.id for s in top]
    headers = {
        'Authorization': f'Bearer {token}'
    }

    def make_url(track_id, limit):
        endpoint = 'https://api.spotify.com/v1/recommendations'

        params = {
            'limit': limit,
            'seed_tracks': f'{track_id}'
        }
        return f'{endpoint}?{urlencode(params)}'

    urls = [make_url(track_id, batch_size) for track_id in top_ids[:-1]] + \
           [make_url(top_ids[-1], (r if r else batch_size))]

    reqs = [requests.get(url, headers=headers).json() for url in urls]
    tracks = [[Track(s) for s in req['tracks']] for req in reqs]
    all_tracks = [track for track_list in tracks for track in track_list]
    return all_tracks


def get_playlist_name(pl_id):
    token = get_access_token()
    endpoint = f'https://api.spotify.com/v1/playlists/{pl_id}'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    url = endpoint
    req = requests.get(url, headers=headers).json()
    if invalid_request(req):
        abort(500)
    return req['name']


def get_playlist_tracks(pl_id, limit=100, offset=0):
    token = get_access_token()
    endpoint = f'https://api.spotify.com/v1/playlists/{pl_id}/tracks'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    params = {
        'limit': limit,
        'offset': offset
    }
    url = f'{endpoint}?{urlencode(params)}'
    req = requests.get(url, headers=headers).json()['items']
    tracks = [Track(s['track']) for s in req if s['track']['id']]
    return tracks


def get_all_playlist_tracks(pl_id):
    offset = 0
    all_tracks = []
    while True:
        track_batch = get_playlist_tracks(pl_id, limit=100, offset=offset)
        if track_batch:
            all_tracks += track_batch
            offset += 100
        else:
            return all_tracks


def get_audio_features(tracks):

    token = get_access_token()
    track_ids = [track.id for track in tracks]

    def make_request(id_list):
        if len(id_list) > 100:
            raise Exception('Track list too large')
        if len(id_list) == 0:
            pass
        id_list = [item for item in id_list]
        endpoint = 'https://api.spotify.com/v1/audio-features'
        headers = {
            'Authorization': f'Bearer {token}'
        }
        params = {
            'ids': f'{",".join(id_list)}'
        }
        url = f'{endpoint}?{urlencode(params)}'
        req = requests.get(url, headers=headers).json()['audio_features']
        return req

    d, r = divmod(len(track_ids), 100)
    loops = d + 1 if r else d
    audio_features = []

    for i in range(loops):
        batch = make_request(track_ids[100*i:100*(i + 1)])
        audio_features += batch

    return audio_features


def create_plot(pl_name, names, danceability, energy, instrumentalness, speechiness, valence):

    fig = go.Figure()

    features = ['danceability', 'energy', 'instrumentalness', 'speechiness', 'valence']
    values = [danceability, energy, instrumentalness, speechiness, valence]

    for i in range(len(features)):
        fig.add_trace(go.Violin(
            y=values[i],
            name=features[i],
            hovertext=names,
            points='all',
            opacity=0.8
        ))

    fig.update_layout(title=pl_name)
    fig.update_yaxes(range=[-0.19, 1.19])
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graph_json


def parse_playlist_id(pl_input):
    if pl_input.isalnum():
        return pl_input
    if 'spotify:playlist:' in pl_input:
        return pl_input.split('spotify:playlist:')[1]
    if 'https://open.spotify.com/playlist/' in pl_input:
        return pl_input.split('https://open.spotify.com/playlist/')[1].split('?si=')[0]
    return None


def parse_song_uri(song_input):
    if song_input.isalnum():
        return f'spotify:track:{song_input}'
    if 'spotify:track:' in song_input:
        return song_input
    if 'https://open.spotify.com/track/' in song_input:
        return f'spotify:track:{song_input.split("https://open.spotify.com/track/")[1].split("?si=")[0]}'
    return None


def query_master():
    master = Master.query.filter_by(session_id='master').first()
    return master


def get_master_token():
    refresh_master()
    master = query_master()
    return master.token


def master_expired(master):
    now = datetime.datetime.now()
    return now > master.expiry


def refresh_master():
    master = query_master()
    if master_expired(master):
        endpoint = 'https://accounts.spotify.com/api/token'
        refresh_params = {
            'grant_type': 'refresh_token',
            'refresh_token': master.refresh_token,
            'client_id': current_app.config['CLIENT_ID']
        }
        response = requests.post(endpoint, data=refresh_params).json()
        if invalid_request(response):
            abort(500)
        else:
            master.token = response['access_token']
            master.refresh_token = response['refresh_token']
            expires_in = response['expires_in']
            now = datetime.datetime.now()
            master.expiry = now + datetime.timedelta(seconds=expires_in)
            db.session.commit()
    pass


def check_user_can_add():
    user = current_user
    in_db = Adds.query.filter_by(user=user.user).first()
    now = datetime.datetime.now()
    if not in_db:
        return True
    else:
        if not in_db.last_add or (now - in_db.last_add).seconds >= 14400:
            return True
        return False


def reset_add_timer():
    user = current_user
    entry = Adds.query.filter_by(user=user.user).first()
    now = datetime.datetime.now()
    if not entry:
        add = Adds(user=user.user, last_add=now)
        db.session.add(add)
    else:
        entry.last_add = now
    db.session.commit()


def add_to_community_playlist(track_uri):
    token = get_master_token()
    playlist_id = current_app.config['COMMUNITY_PLAYLIST_ID']
    add_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    add_body = json.dumps({
        'uris': [track_uri]
    })
    res = requests.post(add_url, headers=headers, data=add_body).json()
    return not res.get('error')
