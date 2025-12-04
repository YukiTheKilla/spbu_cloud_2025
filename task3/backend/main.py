from flask import Flask, jsonify, send_file
from flask_cors import CORS
import sqlite3
import random
import os
import mimetypes

app = Flask(__name__)
CORS(app)

if os.path.exists('/app'):
    # Docker launch
    DB_PATH = '/app/db/music.db'
    TRACKS_DIR = '/app/tracks'
else:
    # Local launch
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'db', 'music.db')
    TRACKS_DIR = os.path.join(BASE_DIR, 'tracks')

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Available formats
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}

# sqlite database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            duration INTEGER,
            file_path TEXT NOT NULL,
            filename TEXT NOT NULL
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM tracks')
    track_count = cursor.fetchone()[0]
    
    if track_count == 0:
        print("Database is empty, scanning tracks directory...")
        
        if os.path.exists(TRACKS_DIR):
            track_files = []
            for filename in sorted(os.listdir(TRACKS_DIR)):
                file_path = os.path.join(TRACKS_DIR, filename)
                _, ext = os.path.splitext(filename)
                
                if os.path.isfile(file_path) and ext.lower() in AUDIO_EXTENSIONS:
                    title = os.path.splitext(filename)[0]
                    if ' - ' in title:
                        artist, track_title = title.split(' - ', 1)
                    else:
                        artist = 'Unknown Artist'
                        track_title = title
                    
                    track_files.append((track_title, artist, 0, file_path, filename))
            
            if track_files:
                cursor.executemany(
                    'INSERT INTO tracks (title, artist, duration, file_path, filename) VALUES (?, ?, ?, ?, ?)',
                    track_files
                )
                print(f"Added {len(track_files)} tracks to database")
            else:
                print("No audio files found in tracks directory")
        else:
            print(f"Tracks directory not found: {TRACKS_DIR}")
    else:
        print(f"Database already contains {track_count} tracks, skipping scan")
    
    conn.commit()
    conn.close()

player_state = {
    'current_index': 0,
    'playlist': [],
    'is_shuffled': False,
    'original_playlist': []
}

def get_all_tracks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tracks ORDER BY id')
    tracks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tracks

def init_playlist():
    if not player_state['playlist']:
        player_state['playlist'] = get_all_tracks()
        player_state['original_playlist'] = player_state['playlist'].copy()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/tracks', methods=['GET'])
def get_tracks():
    tracks = get_all_tracks()
    for track in tracks:
        track['stream_url'] = f"/stream/{track['id']}"
    
    return jsonify({
        'tracks': tracks,
        'total': len(tracks)
    }), 200

@app.route('/current', methods=['GET'])
def get_current():
    init_playlist()
    
    if not player_state['playlist']:
        return jsonify({'error': 'Playlist is empty'}), 404
    
    current_track = player_state['playlist'][player_state['current_index']].copy()
    current_track['stream_url'] = f"/stream/{current_track['id']}"
    
    return jsonify({
        'track': current_track,
        'index': player_state['current_index'],
        'total': len(player_state['playlist']),
        'is_shuffled': player_state['is_shuffled']
    }), 200

@app.route('/next', methods=['GET'])
def next_track():
    init_playlist()
    
    if not player_state['playlist']:
        return jsonify({'error': 'Playlist is empty'}), 404
    
    player_state['current_index'] = (player_state['current_index'] + 1) % len(player_state['playlist'])
    current_track = player_state['playlist'][player_state['current_index']].copy()
    current_track['stream_url'] = f"/stream/{current_track['id']}"
    
    return jsonify({
        'track': current_track,
        'index': player_state['current_index'],
        'total': len(player_state['playlist']),
        'is_shuffled': player_state['is_shuffled']
    }), 200

@app.route('/previous', methods=['GET'])
def previous_track():
    init_playlist()
    
    if not player_state['playlist']:
        return jsonify({'error': 'Playlist is empty'}), 404
    
    player_state['current_index'] = (player_state['current_index'] - 1) % len(player_state['playlist'])
    current_track = player_state['playlist'][player_state['current_index']].copy()
    current_track['stream_url'] = f"/stream/{current_track['id']}"
    
    return jsonify({
        'track': current_track,
        'index': player_state['current_index'],
        'total': len(player_state['playlist']),
        'is_shuffled': player_state['is_shuffled']
    }), 200

@app.route('/shuffle', methods=['POST'])
def shuffle_tracks():
    init_playlist()
    
    if not player_state['playlist']:
        return jsonify({'error': 'Playlist is empty'}), 404
    
    current_track = player_state['playlist'][player_state['current_index']]
    
    player_state['playlist'] = player_state['original_playlist'].copy()
    random.shuffle(player_state['playlist'])
    player_state['is_shuffled'] = True
    
    for i, track in enumerate(player_state['playlist']):
        if track['id'] == current_track['id']:
            player_state['current_index'] = i
            break
    
    response_track = player_state['playlist'][player_state['current_index']].copy()
    response_track['stream_url'] = f"/stream/{response_track['id']}"
    
    return jsonify({
        'message': 'Playlist shuffled',
        'track': response_track,
        'index': player_state['current_index'],
        'total': len(player_state['playlist']),
        'is_shuffled': True
    }), 200

@app.route('/sequential', methods=['POST'])
def sequential_mode():
    init_playlist()
    
    if not player_state['playlist']:
        return jsonify({'error': 'Playlist is empty'}), 404
    
    current_track = player_state['playlist'][player_state['current_index']]
    
    player_state['playlist'] = player_state['original_playlist'].copy()
    player_state['is_shuffled'] = False
    
    for i, track in enumerate(player_state['playlist']):
        if track['id'] == current_track['id']:
            player_state['current_index'] = i
            break
    
    response_track = player_state['playlist'][player_state['current_index']].copy()
    response_track['stream_url'] = f"/stream/{response_track['id']}"
    
    return jsonify({
        'message': 'Sequential mode activated',
        'track': response_track,
        'index': player_state['current_index'],
        'total': len(player_state['playlist']),
        'is_shuffled': False
    }), 200

@app.route('/stream/<int:track_id>', methods=['GET'])
def stream_track(track_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tracks WHERE id = ?', (track_id,))
    track = cursor.fetchone()
    conn.close()
    
    if not track:
        return jsonify({'error': 'Track not found'}), 404
    
    file_path = track['file_path']
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found on disk'}), 404
    
    mimetype = mimetypes.guess_type(file_path)[0] or 'audio/mpeg'
    
    return send_file(file_path, mimetype=mimetype)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000, debug=False)