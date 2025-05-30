# backend/app.py list of directories
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import shutil
from werkzeug.utils import secure_filename
import mimetypes
import json

app = Flask(__name__, static_folder='../frontend/dist')
CORS(app, resources={r"/*": {"origins": ["https://pic-sort-tau.vercel.app"]}})

# Image extensions to filter by
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff']

@app.route("/")
def index():
    return jsonify({
        "message": "Welcome to the API!",
        "status": "running"
    })


# base_paths = [
#     os.path.expanduser("~"),       # Home directory
#     os.path.expanduser("~/Desktop"),
#     os.path.expanduser("~/Documents"),
#     os.path.expanduser("~/Pictures"),
#     os.path.expanduser("~/Downloads"),
#     "/app",  # Default app directory in Railway/Render
#     "/tmp"   # Writable temporary directory in most cloud environments
# ]

# @app.route('/api/list-directories', methods=['GET'])
# def list_directories():
#     """List available directories for user selection"""
#     try:
#         root_path = request.args.get('root', os.path.expanduser("~"))

#         # Check if the root path exists & is accessible
#         if not os.path.exists(root_path) or not os.path.isdir(root_path):
#             return jsonify({"error": f"Invalid root directory path: {root_path}"}), 400

#         available_dirs = []
#         for item in os.listdir(root_path):
#             try:
#                 full_path = os.path.join(root_path, item)
#                 if os.path.isdir(full_path):
#                     available_dirs.append({"path": full_path, "name": item})
#             except PermissionError:
#                 continue  # Skip directories with permission issues
        
#         # Debugging logs (Check deployment logs in Railway/Render)
#         print(f"HOME DIRECTORY: {os.path.expanduser('~')}")
#         print(f"Directories in '{root_path}':", available_dirs)

#         return jsonify({"directories": available_dirs, "current_path": root_path})
#     except Exception as e:
#         print("Error in list-directories:", str(e))  # Debugging logs
#         return jsonify({"error": str(e)}), 500
@app.route('/api/list-directories', methods=['GET'])
def list_directories():
    """List accessible directories for user selection"""
    try:
        # Define base directories (Check if they exist before listing)
        base_paths = [
            "/opt/render/project",  # Project root (Your Flask app)
            "/tmp",                 # Writable temp directory
            "/app",                 # Default app directory (if available)
            os.path.expanduser("~"),  # Home directory (if accessible)
        ]

        available_dirs = []
        for base in base_paths:
            if os.path.exists(base) and os.path.isdir(base):
                available_dirs.append({"path": base, "name": os.path.basename(base) or "Root"})

        # Debugging Logs - Check Render Logs
        print(f"HOME DIRECTORY: {os.path.expanduser('~')}")
        print(f"Available directories: {available_dirs}")

        return jsonify({"directories": available_dirs})
    except Exception as e:
        print("Error in list-directories:", str(e))  # Log the error in Render logs
        return jsonify({"error": str(e)}), 500


@app.route('/api/list-subdirectories', methods=['POST'])
def list_subdirectories():
    """List subdirectories of a given directory"""
    data = request.json
    parent_dir = data.get('directory')
    
    if not parent_dir or not os.path.isdir(parent_dir):
        return jsonify({"error": "Invalid directory path"}), 400
    
    try:
        subdirs = []
        for item in os.listdir(parent_dir):
            full_path = os.path.join(parent_dir, item)
            if os.path.isdir(full_path):
                subdirs.append({
                    "path": full_path,
                    "name": item
                })
        
        return jsonify({"subdirectories": subdirs})
    except PermissionError:
        return jsonify({"error": "Permission denied. Cannot access the directory."}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/list-images', methods=['POST'])
def list_images():
    """List all images in a specified directory"""
    data = request.json
    folder_path = data.get('folderPath')
    
    if not folder_path or not os.path.isdir(folder_path):
        return jsonify({"error": "Invalid folder path"}), 400
    
    try:
        # Get all files in the directory
        files = os.listdir(folder_path)
        
        # Filter only image files
        image_files = []
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path) and file_ext in IMAGE_EXTENSIONS:
                image_files.append(file)
        
        return jsonify({
            "images": image_files,
            "totalCount": len(image_files),
            "folderPath": folder_path
        })
    except PermissionError:
        return jsonify({"error": "Permission denied. Cannot access the directory."}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/image/<path:folder_path>/<filename>')
def get_image(folder_path, filename):
    """Serve an image file from the specified directory"""
    return send_from_directory(folder_path, filename)

@app.route('/api/save-categorized', methods=['POST'])
def save_categorized():
    """Save categorized images to new folders based on categories"""
    data = request.json
    source_folder = data.get('sourceFolder')
    categorized_images = data.get('categorizedImages')
    
    if not source_folder or not os.path.isdir(source_folder) or not categorized_images:
        return jsonify({"error": "Invalid data provided"}), 400
    
    try:
        # Create destination parent folder (adjacent to source folder)
        dest_parent = os.path.join(os.path.dirname(source_folder), "categorized_images")
        if not os.path.exists(dest_parent):
            os.makedirs(dest_parent)
        
        # Create destination folders for each category
        categories = set([img['category'] for img in categorized_images if 'category' in img])
        category_folders = {}
        
        for category in categories:
            category_folder = os.path.join(dest_parent, category)
            if not os.path.exists(category_folder):
                os.makedirs(category_folder)
            category_folders[category] = category_folder
        
        # Process each image
        results = []
        for img_data in categorized_images:
            if 'filename' not in img_data or 'category' not in img_data:
                continue
                
            filename = img_data['filename']
            category = img_data['category']
            
            # Source and destination paths
            source_path = os.path.join(source_folder, filename)
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_{category}{ext}"
            dest_path = os.path.join(category_folders[category], new_filename)
            
            # Copy and rename the file
            try:
                shutil.copy2(source_path, dest_path)
                results.append({
                    "original": filename,
                    "renamed": new_filename,
                    "category": category,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "original": filename,
                    "error": str(e),
                    "success": False
                })
        
        return jsonify({
            "results": results,
            "categorizedCount": len([r for r in results if r.get('success', False)]),
            "destinationFolder": dest_parent
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve React app in production
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0",  port=8080)
    