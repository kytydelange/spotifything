from flask import Blueprint, render_template, redirect, url_for
from app.features.utils import *
from flask_login import login_required


features = Blueprint('features', __name__)


@features.route('/top')
@login_required
def top():
    return render_template('top.html')


@features.route('/top/make', methods=['POST', 'GET'])
@login_required
def top_make():
    if request.method == 'POST':
        pl_length = request.form.get('pl_length')
        if not pl_length.isnumeric() and pl_length:
            abort(500)
        length = 50 if not pl_length else min(max(int(pl_length), 0), 99)
        term = request.args.get('term')
        profile = get_profile()
        user_id = profile['id']
        pl_name = f'Top songs: {term} term'
        pl_public = 'true'
        pl_description = 'Generated on www.spotifything.com'
        if length <= 50:
            track_uris = [song.uri for song in get_top_tracks(limit=length, offset=0, top_term=f'{term}_term')]
        else:
            tracks_1 = [song.uri for song in get_top_tracks(limit=49, offset=0, top_term=f'{term}_term')]
            tracks_2 = [song.uri for song in get_top_tracks(limit=length-49, offset=49, top_term=f'{term}_term')]
            track_uris = tracks_1 + tracks_2
        make_playlist(user_id, pl_name, pl_public, pl_description, track_uris)
        return render_template('success.html', pl_name=pl_name,
                               back_url=url_for('features.top'))
    else:
        abort(500)


@features.route('/curate')
@login_required
def curate():
    return render_template('curate.html')


@features.route('/curate/make', methods=['POST', 'GET'])
@login_required
def curate_make():
    if request.method == 'POST':
        pl_length = int(request.form.get('pl_length')) if request.form.get('pl_length') else 50
        profile = get_profile()
        term = request.args.get('term')
        user_id = profile['id']
        pl_name = 'Discover'
        pl_public = 'true'
        pl_description = 'Generated on www.spotifything.com'
        tracks = curate_playlist(term, pl_length)
        track_uris = [song.uri for song in tracks]
        post = make_playlist(user_id, pl_name, pl_public, pl_description, track_uris)
        if not post.get('error'):
            return render_template('success.html', pl_name=pl_name,
                                   back_url=url_for('features.curate'))
    abort(500)


@features.route('/analyze')
@login_required
def analyze():
    return render_template('analyze.html')


@features.route('/plot', methods=['POST', 'GET'])
@login_required
def plot():
    if request.method == 'POST':
        pl_id = parse_playlist_id(request.form.get('pl'))
        if not pl_id or not pl_id.isalnum():
            abort(500)
        pl_name = f'{get_playlist_name(pl_id)} ({pl_id})'
        tracks = get_all_playlist_tracks(pl_id)
        audio_features = get_audio_features(tracks)
        names = [track.name for track in tracks]
        danceability = [track['danceability'] for track in audio_features]
        energy = [track['energy'] for track in audio_features]
        instrumentalness = [track['instrumentalness'] for track in audio_features]
        speechiness = [track['speechiness'] for track in audio_features]
        valence = [track['valence'] for track in audio_features]

        violins = create_plot(pl_name, names, danceability, energy, instrumentalness, speechiness, valence)

        return render_template('plot.html', plot=violins)
    else:
        abort(500)


@features.route('/community_playlist')
@login_required
def community_playlist():
    able_to_add = check_user_can_add()
    return render_template('community_playlist.html', able_to_add=able_to_add)


@features.route('/community_playlist/add', methods=['POST', 'GET'])
def community_playlist_add():
    if request.method == 'POST':
        song_uri = parse_song_uri(request.form.get('song'))
        if check_user_can_add():
            success = add_to_community_playlist(song_uri)
            if success:
                reset_add_timer()
                return redirect(url_for('features.community_playlist'))
            else:
                abort(500)
        else:
            abort(403)
            return redirect(url_for('features.community_playlist'))
    abort(403)
