import os
import uuid
import re
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import requests
from pymongo import MongoClient
import sys
from bson.binary import Binary
from flask import Response


app = Flask(__name__)

# -----------------------------
# MongoDB Connection 
# -----------------------------

STORE_ID = os.getenv('STORE_ID', '1') 

DB_NAME = f"petstore{STORE_ID}" 


MONGO_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME] 
    pet_types_collection = db['pet_types']
    pictures_collection = db["pictures"]
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}", file=sys.stderr)
    sys.exit(1)



NINJA_API_KEY =os.getenv("NINJA_API_KEY")
NINJA_URL = "https://api.api-ninjas.com/v1/animals"

prev_url_by_pet = {}


def gen_id():
    return str(uuid.uuid4())

def normalize_string(s):
    if isinstance(s, str):
        return s.strip().lower()
    return s

def pick_attributes(ninja_obj: dict) -> list:

    ch = ninja_obj.get("characteristics") or {}
    text = ch.get("temperament") or ch.get("group_behavior") or ""
    words = re.findall(r"[A-Za-z]+", text)
    return words

def parse_lifespan(ninja_obj: dict):
    ch = ninja_obj.get("characteristics") or {}
    text = ch.get("lifespan") or ""
    nums = re.findall(r"\d+", text)
    if not nums:
        return None
    return int(min(nums, key=int))

def extract_family_genus(ninja_obj: dict):
    tax = ninja_obj.get("taxonomy") or {}
    family = tax.get("family")
    genus = tax.get("genus")
    return family, genus

def fetch_ninja_exact_type(type_name: str):

    headers = {"X-Api-Key": NINJA_API_KEY}
    params = {"name": type_name}
    resp = requests.get(NINJA_URL, headers=headers, params=params, timeout=10)
    if resp.status_code != 200:
        return None, f"API response code {resp.status_code}"
    try:
        data = resp.json() or []
    except Exception as e:
        return None, f"API response code {resp.status_code}"
    lower = type_name.strip().lower()
    for item in data:
        if isinstance(item, dict) and (item.get("name", "").strip().lower() == lower):
            return item, None
    return None, None

def parse_birthdate(s):
    try:
        return datetime.strptime(s, "%d-%m-%Y").date()
    except Exception:
        return None

def download_picture(url, pet_type_id, pet_name):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200 or not r.content:
            return None

        content_type = (r.headers.get("Content-Type") or "").lower()

        if "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
            content_type = "image/jpeg"
        elif "png" in content_type:
            ext = ".png"
            content_type = "image/png"
        else:
            return None

        file_name = f"{pet_name}-{pet_type_id}{ext}"

        pictures_collection.replace_one(
            {"_id": file_name},
            {
                "_id": file_name,
                "content_type": content_type,
                "data": Binary(r.content),
            },
            upsert=True
        )

        return file_name
    except Exception:
        return None


def find_pet_index(pets_list, target_name: str):
    low = target_name.strip().lower()
    for i, p in enumerate(pets_list):
        if str(p.get("name", "")).strip().lower() == low:
            return i
    return None



# /pet-types
@app.route('/pet-types', methods=['GET'])
def get_all_pet_types():
    docs = list(pet_types_collection.find({}))
    result = docs[:]

    args = request.args


    for field in ['id', 'type', 'family', 'genus', 'lifespan']:
        if field in args:
            value = args.get(field, '')
            if field == 'lifespan':
                try:
                    wanted = int(value)
                except ValueError:
                    result = []
                else:
                    result = [pt for pt in result if pt.get('lifespan') == wanted]
            else:
                wanted = (value or '').strip().lower()
                result = [
                    pt for pt in result
                    if ((pt.get(field) or '')).strip().lower() == wanted
                ]

    if 'hasAttribute' in args:
        attr = (args.get('hasAttribute') or '').strip().lower()
        result = [
            pt for pt in result
            if any((a or '').strip().lower() == attr for a in pt.get('attributes', []))
        ]

    public_result = []
    for pt in result:
        public_pt = dict(pt)
        public_pt.pop("_id", None)
        public_pt["pets"] = [p.get("name") for p in pt.get("pets", [])]
        public_result.append(public_pt)

    return jsonify(public_result), 200

@app.route('/pet-types', methods=['POST'])
def add_pet_type():
    try:
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return jsonify({"error": "Expected application/json media type"}), 415

        data = request.get_json()
        required_fields = ['type']
        if not data or not all(field in data for field in required_fields):
            return jsonify({"error": "Malformed data"}), 400

        req_type = data['type']

        existing = list(pet_types_collection.find({}))
        if any((pt.get("type", "") or "").strip().lower() == req_type.strip().lower()
               for pt in existing):
            return jsonify({"error": "Malformed data"}), 400


        record, api_err = fetch_ninja_exact_type(req_type)
        if api_err:
            print("Exception (Ninja):", api_err)
            return jsonify({"server error": api_err}), 500
        if record is None:
            return jsonify({"error": "Malformed data"}), 400

        family, genus = extract_family_genus(record)
        attributes = pick_attributes(record)
        lifespan = parse_lifespan(record)

        new_id = gen_id()
        pet_type = {
            "id": new_id,
            "type": req_type,
            "family": family,
            "genus": genus,
            "attributes": attributes,
            "lifespan": lifespan,
            "pets": []
        }
        pet_types_collection.insert_one(pet_type)
        public_pt = dict(pet_type) 
        public_pt.pop("_id", None) 
        return jsonify(public_pt), 201

    except Exception as e:
        print("Exception: ", str(e))
        return jsonify({"server error": str(e)}), 500

# /pet-types/<id>
@app.route('/pet-types/<string:id>', methods=['GET'])
def get_pet_type_by_id(id):
    doc = pet_types_collection.find_one({"id": id})
    if doc is None:
        return jsonify({"error": "Not found"}), 404

    public_pt = dict(doc)
    public_pt.pop("_id", None)
    public_pt["pets"] = [p.get("name") for p in public_pt.get("pets", [])]
    return jsonify(public_pt), 200

@app.route('/pet-types/<string:id>', methods=['DELETE'])
def delete_pet_type_by_id(id):
    doc = pet_types_collection.find_one({"id": id})
    if doc is None:
        return jsonify({"error": "Not found"}), 404

    if doc.get("pets"):
        return jsonify({"error": "Malformed data"}), 400

    pet_types_collection.delete_one({"id": id})
    return '', 204

#  /pet-types/<id>/pets
@app.route('/pet-types/<string:id>/pets', methods=['GET'])
def get_pets_by_type(id):
    doc = pet_types_collection.find_one({"id": id})
    if doc is None:
        return jsonify({"error": "Not found"}), 404

    pets = list(doc.get("pets", []))

    gt_raw = request.args.get("birthdateGT")
    lt_raw = request.args.get("birthdateLT")
    gt_date = parse_birthdate(gt_raw) if gt_raw else None
    lt_date = parse_birthdate(lt_raw) if lt_raw else None

    def pet_date(p):
        d = p.get("birthdate")
        if not d or d == "NA":
            return None
        return parse_birthdate(d)

    if gt_date:
        pets = [p for p in pets if (pet_date(p) and pet_date(p) > gt_date)]
    if lt_date:
        pets = [p for p in pets if (pet_date(p) and pet_date(p) < lt_date)]

    return jsonify(pets), 200

@app.route('/pet-types/<string:id>/pets', methods=['POST'])
def add_pet_under_type(id):
    doc = pet_types_collection.find_one({"id": id})
    if doc is None:
        return jsonify({"error": "Not found"}), 404

    content_type = request.headers.get('Content-Type')
    if content_type != 'application/json':
        return jsonify({"error": "Expected application/json media type"}), 415

    data = request.get_json()
    required_fields = ['name']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Malformed data"}), 400

    name = data['name']
    birthdate = data.get('birthdate', "NA")
    picture_url = data.get('picture-url')

    pets = doc.get("pets", [])

    if any((p.get('name') or '').strip().lower() == name.strip().lower()
           for p in pets):
        return jsonify({"error": "Malformed data"}), 400

    if birthdate != "NA" and parse_birthdate(birthdate) is None:
        return jsonify({"error": "Malformed data"}), 400

    picture_file = "NA"
    if picture_url:
        fn = download_picture(picture_url, id, name)
        if not fn:
            return jsonify({"error": "Malformed data"}), 400
        picture_file = fn
        prev_url_by_pet[(id, name)] = picture_url

    pet = {
        "name": name,
        "birthdate": birthdate,
        "picture": picture_file
    }
    pets.append(pet)
    pet_types_collection.update_one(
        {"id": id},
        {"$set": {"pets": pets}}
    )
    return jsonify(pet), 201


#  /pet-types/<id>/pets/<name>
@app.route('/pet-types/<string:id>/pets/<string:name>', methods=['GET'])
def get_pet_by_name(id, name):
    doc = pet_types_collection.find_one({"id": id})
    if doc is None:
        return jsonify({"error": "Not found"}), 404

    pets = doc.get("pets", [])
    idx = find_pet_index(pets, name)
    if idx is None:
        return jsonify({"error": "Not found"}), 404

    return jsonify(pets[idx]), 200

@app.route('/pet-types/<string:id>/pets/<string:name>', methods=['DELETE'])
def delete_pet_by_name(id, name):
    doc = pet_types_collection.find_one({"id": id})
    if doc is None:
        return jsonify({"error": "Not found"}), 404

    pets = doc.get("pets", [])
    idx = find_pet_index(pets, name)
    if idx is None:
        return jsonify({"error": "Not found"}), 404

    pic = pets[idx].get("picture", "NA")
    if pic and pic != "NA":
        pictures_collection.delete_one({"_id": pic})

    pets.pop(idx)

    pet_types_collection.update_one(
        {"id": id},
        {"$set": {"pets": pets}}
    )

    prev_url_by_pet.pop((id, name), None)
    return '', 204

@app.route('/pet-types/<string:id>/pets/<string:name>', methods=['PUT'])
def update_pet_by_name(id, name):
    doc = pet_types_collection.find_one({"id": id})
    if doc is None:
        return jsonify({"error": "Not found"}), 404

    content_type = request.headers.get('Content-Type')
    if content_type != 'application/json':
        return jsonify({"error": "Expected application/json media type"}), 415

    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Malformed data"}), 400

    pets = doc.get("pets", [])
    idx = find_pet_index(pets, name)
    if idx is None:
        return jsonify({"error": "Not found"}), 404

    current = pets[idx]
    new_name = data['name']
    new_birthdate = data.get('birthdate',"NA")
    if new_birthdate != "NA" and parse_birthdate(new_birthdate) is None:
        return jsonify({"error": "Malformed data"}), 400

    new_picture = "NA"
    old_picture = current.get("picture", "NA")

    if 'picture-url' in data:
        url = data['picture-url']
        last_key_old_name = (id, current.get('name'))
        last_url = prev_url_by_pet.get(last_key_old_name)

        if last_url and str(last_url).strip() == str(url).strip():
            new_picture = current.get('picture', "NA")

        else:
            fn = download_picture(url, id, new_name)
            if not fn:
                return jsonify({"error": "Malformed data"}), 400
            
            if old_picture != "NA" and old_picture != fn:
                pictures_collection.delete_one({"_id": old_picture})

            new_picture = fn
            prev_url_by_pet[(id, new_name)] = url
    else:
        if old_picture != "NA":
            pictures_collection.delete_one({"_id": old_picture})
        prev_url_by_pet.pop((id, current.get('name')),None)

    updated = {
        "name": new_name,
        "birthdate": new_birthdate,
        "picture": new_picture
    }
    pets[idx] = updated

    pet_types_collection.update_one(
        {"id": id},
        {"$set": {"pets": pets}}
    )

    if new_name != name:
        prev_url_by_pet.pop((id, name), None)

    return jsonify(updated), 200


#  /pictures/<file-name>
@app.route('/pictures/<string:filename>', methods=['GET'])
def get_picture(filename):
    doc = pictures_collection.find_one({"_id": filename})
    if not doc:
        return jsonify({"error": "Not found"}), 404

    ct = doc.get("content_type")
    data = doc.get("data")

    if ct not in ("image/jpeg", "image/png") or data is None:
        return jsonify({"error": "Not found"}), 404

    return Response(bytes(data), mimetype=ct), 200




if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    app.run(host='0.0.0.0', port=port)