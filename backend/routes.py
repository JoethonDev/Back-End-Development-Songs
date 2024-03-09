from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route('/health')
def get_health():
    return {'status' : 'OK'}, 200

@app.route('/count')
def get_count():
    return {'count' : len(songs_list)}, 200

@app.route('/song')
def songs():
    list_of_songs = db.songs.find({})
    list_of_songs = parse_json(list_of_songs)
    return {'songs' : list_of_songs}, 200

@app.route('/song/<id>')
def get_song_by_id(id):
    try :
        id = int(id)
    except TypeError:
        return {"message": "Invalid ID"}, 404

    song = db.songs.find_one({"id": id})
    if song :
        song = parse_json(song)
        return song, 200
    else :
        return {"message": "song with id not found"}, 404

@app.route('/song', methods=['POST'])
def create_song():
    song = request.get_json()
    try :
        song['id'] = int(song['id'])
    except TypeError :
        return {'message' :  'Invalid ID'}, 302

    exist_song = db.songs.find_one({'id' : song['id']})
    if exist_song :
        return {"Message" : f"song with id {song['id']} already present"}, 302
    else :
        record = db.songs.insert_one(song)
        inserted_id = {
            '$oid' : str(record.inserted_id)
        }
        return {"inserted id" : inserted_id}, 201

@app.route('/song/<id>', methods=['PUT'])
def update_song(id):
    song = request.get_json()
    try :
        id = int(id)
        query = {'id' : id}
    except TypeError :
        return {'message' :  'Invalid ID'}, 302

    current_song = db.songs.find_one(query)
    if not current_song :
        return {"message": "song not found"}, 404
    else :
        current_song = parse_json(current_song)
        is_changed = False
        for key, val in song.items():
            try :
                if current_song[key] != val:
                    is_changed = True
                    break
            except KeyError:
                is_changed = True
                break

        if not is_changed:
            return {"message":"song found, but nothing updated"}, 200

        record = db.songs.update_one(query, {'$set': song})
        updated_song = db.songs.find_one(query)
        updated_song = parse_json(updated_song)

        return updated_song, 200

@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    deleted_song = db.songs.delete_one({'id' : id})
    if deleted_song.deleted_count :
        return "", 204
    else :
        return {"message": "song not found"}, 404