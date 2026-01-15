#!/usr/bin/env python3
"""
HTTP server with file upload support for save game loading
"""
import sys
import os
import json
import tempfile
import shutil
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.save_game_parser import SaveGameParser
from src.parsers.save_game_comparator import SaveGameComparator

# Get paths first
WEB_DIR = Path(__file__).parent
BASE_DATA_PATH = WEB_DIR.parent / "Input" / "UW1" / "DATA"
BASE_WEB_DATA_PATH = WEB_DIR / "data" / "web_map_data.json"

# Configure Flask to serve static files from current directory
app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path='')
CORS(app)  # Enable CORS for all routes

# Disable request logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


def load_base_game_data() -> dict:
    """Load base game data from web_map_data.json"""
    if not BASE_WEB_DATA_PATH.exists():
        raise FileNotFoundError(f"Base game data not found: {BASE_WEB_DATA_PATH}")
    
    with open(BASE_WEB_DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory(WEB_DIR, 'index.html')


@app.route('/api/base-data', methods=['GET'])
def get_base_data():
    """Return the base game data"""
    try:
        data = load_base_game_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload-save', methods=['POST'])
def upload_save():
    """Handle save game directory upload and return parsed data with changes"""
    try:
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files in upload'}), 400
        
        # Create temporary directory for uploaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save all uploaded files
            lev_ark_path = None
            for file in files:
                if file.filename:
                    # Preserve directory structure from webkitdirectory
                    file_path = temp_path / file.filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file.save(str(file_path))
                    
                    # Check if this is lev.ark
                    if file.filename.lower().endswith('lev.ark'):
                        lev_ark_path = file_path
            
            # If no lev.ark found, try to find it in subdirectories
            if not lev_ark_path:
                for lev_file in temp_path.rglob('lev.ark'):
                    if lev_file.is_file():
                        lev_ark_path = lev_file
                        break
            
            if not lev_ark_path:
                return jsonify({'error': 'lev.ark file not found in uploaded directory'}), 400
            
            # Parse save game - pass the directory containing lev.ark
            save_parser = SaveGameParser(lev_ark_path.parent)
            save_parser.parse(BASE_DATA_PATH)
            save_data = save_parser.get_save_data_for_web(BASE_DATA_PATH)
            
            # Load base game data
            base_data = load_base_game_data()
            
            # Compare save game with base game
            comparator = SaveGameComparator(base_data, save_data)
            changes = comparator.compare()
            
            # Apply change metadata to save data
            save_data_with_changes = comparator.apply_changes_to_save_data()
            
            # Get summary
            summary = comparator.get_changes_summary()
            
            # Return result
            return jsonify({
                'success': True,
                'save_data': save_data_with_changes,
                'changes': {
                    level: {
                        change_type: [
                            {
                                'change_type': c.change_type,
                                'object_id': c.object_id,
                                'level': c.level,
                                'base_data': c.base_data,
                                'save_data': c.save_data,
                            }
                            for c in changes_list
                        ]
                        for change_type, changes_list in level_changes.items()
                    }
                    for level, level_changes in changes.items()
                },
                'summary': summary
            })
    
    except FileNotFoundError as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error processing save game: {str(e)}'}), 500


@app.route('/<path:filename>')
def serve_static_files(filename):
    """Serve static files (CSS, JS, images, data, maps, etc.)"""
    # Don't handle API routes here - they should be handled by specific routes above
    if filename.startswith('api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    
    # Security: prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    file_path = WEB_DIR / filename
    # Only serve files that exist and are within the web directory
    if file_path.exists() and file_path.is_file():
        # Verify the file is within WEB_DIR (security check)
        try:
            file_path.resolve().relative_to(WEB_DIR.resolve())
            return send_from_directory(WEB_DIR, filename)
        except ValueError:
            # File is outside WEB_DIR
            return jsonify({'error': 'Invalid path'}), 403
    
    # For other files, return 404
    return jsonify({'error': 'File not found'}), 404


def main():
    """Main entry point"""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    bind_address = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    
    # Change to web directory
    os.chdir(WEB_DIR)
    
    print(f"Serving HTTP on {bind_address} port {port} (http://{bind_address}:{port}/) ...")
    print(f"Base data path: {BASE_DATA_PATH}")
    print(f"Web data path: {BASE_WEB_DATA_PATH}")
    
    app.run(host=bind_address, port=port, debug=False)


if __name__ == '__main__':
    main()
