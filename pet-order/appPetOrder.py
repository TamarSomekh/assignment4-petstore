import os
import sys
import uuid
from flask import Flask,request, jsonify
from pymongo import MongoClient
import random
import requests
import re

app = Flask(__name__)

# -----------------------------
# Environment configuration
# -----------------------------

PET_STORE1_URL = os.getenv("PET_STORE1_URL", "http://pet-store1:8000")
PET_STORE2_URL = os.getenv("PET_STORE2_URL", "http://pet-store2:8000")

OWNER_PC_HEADER = "OwnerPC"
OWNER_PC_SECRET = "LovesPetsL2M3n4"


# -----------------------------
# MongoDB connection
# -----------------------------
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/petorder")

try:
    mongo_client = MongoClient(MONGODB_URI)
    mongo_db = mongo_client.get_database()
    transactions_collection = mongo_db.transactions
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}", file=sys.stderr)
    sys.exit(1)

# -----------------------------
# Helper functions
# -----------------------------
def _generate_purchase_id():
    return str(uuid.uuid4())

def _get_pet_type_id(store_url, pet_type_name):
    
    try:
        resp = requests.get(
            f"{store_url}/pet-types",
            params={"type": pet_type_name},
            timeout=5,
        )
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    try:
        pet_types = resp.json()
    except Exception:
        return None

    if not isinstance(pet_types, list) or len(pet_types) == 0:
        return None

    
    return pet_types[0].get("id")


def _get_pets_in_type(store_url, pet_type_id):
    
    try:
        resp = requests.get(
            f"{store_url}/pet-types/{pet_type_id}/pets",
            timeout=5,
        )
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    try:
        pets = resp.json()
    except Exception:
        return None

    if not isinstance(pets, list):
        return None

    return pets

def _get_single_pet(store_url, pet_type_id, pet_name):
    """
    GET /pet-types/<id>/pets/<name>
    """
    try:
        resp = requests.get(
            f"{store_url}/pet-types/{pet_type_id}/pets/{pet_name}",
            timeout=5,
        )
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    try:
        return resp.json()
    except Exception:
        return None


def _choose_pet_specific_store(store_number, pet_type_name, pet_name=None):
    
    store_url = PET_STORE1_URL if store_number == 1 else PET_STORE2_URL

    pet_type_id = _get_pet_type_id(store_url, pet_type_name)
    if pet_type_id is None:
        return None

    
    if pet_name is not None:
        pet = _get_single_pet(store_url, pet_type_id, pet_name)
        if pet is None:
            return None
        return (store_number, store_url, pet_type_id, pet_name, pet)

    
    pets = _get_pets_in_type(store_url, pet_type_id)
    if pets is None or len(pets) == 0:
        return None

    chosen = random.choice(pets)
    chosen_name = chosen.get("name")
    if not isinstance(chosen_name, str):
        return None

    return (store_number, store_url, pet_type_id, chosen_name, chosen)


def _choose_pet_any_store(pet_type_name):
    candidates = []

    for store_number, store_url in [(1, PET_STORE1_URL), (2, PET_STORE2_URL)]:
        pet_type_id = _get_pet_type_id(store_url, pet_type_name)
        if pet_type_id is None:
            continue

        pets = _get_pets_in_type(store_url, pet_type_id)
        if pets is None:
            continue

        for pet in pets:
            name = pet.get("name")
            if not isinstance(name, str):
                continue
            
            candidates.append((store_number, store_url, pet_type_id, name, pet))

    if not candidates:
        return None

    return random.choice(candidates)

def _delete_pet(store_url, pet_type_id, pet_name):
    
    try:
        resp = requests.delete(
            f"{store_url}/pet-types/{pet_type_id}/pets/{pet_name}",
            timeout=5,
        )
    except Exception:
        return False, None

    if resp.status_code == 204:
        return True, 204

    return False, resp.status_code


@app.route("/purchases", methods=["POST"])
def create_purchase():
    if not request.is_json:
        return {"error": "Expected application/json media type"}, 415

    try:
        data = request.get_json()
    except Exception:
        return {"error": "Malformed data"}, 400

    purchaser = data.get("purchaser")
    pet_type_name = data.get("pet-type")
    store = data.get("store", None)
    pet_name = data.get("pet-name", None)

    if not isinstance(purchaser, str) or not purchaser.strip():
        return {"error": "Malformed data"}, 400
    if not isinstance(pet_type_name, str) or not pet_type_name.strip():
        return {"error": "Malformed data"}, 400

    if pet_name is not None and store is None:
        return {"error": "Malformed data"}, 400

    store_num = None
    if store is not None:
    
        if isinstance(store, str):
            if store not in ["1", "2"]:
                return {"error": "Malformed data"}, 400
            store_num = int(store)
        elif isinstance(store, int):
            if store not in (1, 2):
                return {"error": "Malformed data"}, 400
            store_num = store
        else:
            return {"error": "Malformed data"}, 400
    
    
    if store_num is not None:
        chosen = _choose_pet_specific_store(store_num, pet_type_name, pet_name)
    else:
        chosen = _choose_pet_any_store(pet_type_name)

    if chosen is None:
        return {"error": "No pet of this type is available"}, 400

    chosen_store, chosen_store_url, pet_type_id, chosen_pet_name, chosen_pet = chosen

    deleted, status_code = _delete_pet(chosen_store_url, pet_type_id, chosen_pet_name)
    if not deleted:
        return {"error": "Server error removing pet from store"}, 500

    purchase_id = _generate_purchase_id()

    transaction_doc = {
        "purchaser": purchaser,
        "pet-type": pet_type_name,
        "store": chosen_store,
        "purchase-id": purchase_id,
    }

    try:
        transactions_collection.insert_one(transaction_doc)
    except Exception:
        return {"error": "Server error storing transaction"}, 500

    purchase_json = {
        "purchaser": purchaser,
        "pet-type": pet_type_name,
        "store": chosen_store,
        "pet-name": chosen_pet_name,
        "purchase-id": purchase_id,
    }

    return jsonify(purchase_json), 201


@app.route("/transactions", methods=["GET"])
def get_transactions():
    """
    GET /transactions – רק הבעלים:
    - חייב Header: OwnerPC: LovesPetsL2M3n4!
    - מחזיר רשימת transactions מתוך Mongo
    - תומך בפילטרים דרך query params (purchaser, pet-type, store, purchase-id)
    """

    owner_header = request.headers.get(OWNER_PC_HEADER)
    if owner_header != OWNER_PC_SECRET:
        return {"error": "unauthorized"}, 401

    allowed_fields = {"purchaser", "pet-type", "store", "purchase-id"}
    query_params = request.args

    mongo_filter = {}

    for key, value in query_params.items():
        if key not in allowed_fields:
            continue

        if key == "store":
            try:
                store_int = int(value)
                mongo_filter["store"] = store_int
            except Exception:
                continue
        elif key in ("pet-type", "purchaser"):
            mongo_filter[key] = {"$regex": f"^{re.escape(value)}$", "$options": "i"}
        else:
            mongo_filter[key] = value

    try:
        docs = list(transactions_collection.find(mongo_filter))
    except Exception:
        return {"error": "Server error"}, 500

    result = []
    for doc in docs:
        doc_copy = dict(doc)
        doc_copy.pop("_id", None)
        result.append(doc_copy)

    return jsonify(result), 200



if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)