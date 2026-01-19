import pytest
import requests
import time

# Base URLs for the services
STORE1_URL = "http://localhost:5001"
STORE2_URL = "http://localhost:5002"
ORDER_URL = "http://localhost:5003"

# Pet Type payloads 
PET_TYPE1 = {
    "type": "Golden Retriever"
}
PET_TYPE1_VAL = {
    "type": "Golden Retriever",
    "family": "Canidae",
    "genus": "Canis",
    "attributes": [],
    "lifespan": 12
}

PET_TYPE2 = {
    "type": "Australian Shepherd"
}
PET_TYPE2_VAL = {
    "type": "Australian Shepherd",
    "family": "Canidae",
    "genus": "Canis",
    "attributes": ["Loyal", "outgoing", "and", "friendly"],
    "lifespan": 15
}

PET_TYPE3 = {
    "type": "Abyssinian"
}
PET_TYPE3_VAL = {
    "type": "Abyssinian",
    "family": "Felidae",
    "genus": "Felis",
    "attributes": ["Intelligent", "and", "curious"],
    "lifespan": 13
}

PET_TYPE4 = {
    "type": "bulldog"
}
PET_TYPE4_VAL = {
    "type": "bulldog",
    "family": "Canidae",
    "genus": "Canis",
    "attributes": ["Gentle", "calm", "and", "affectionate"],
    "lifespan": None
}

# Pet payloads 
PET1_TYPE1 = {
    "name": "Lander",
    "birthdate": "14-05-2020"
}

PET2_TYPE1 = {
    "name": "Lanky"
}

PET3_TYPE1 = {
    "name": "Shelly",
    "birthdate": "07-07-2019"
}

PET4_TYPE2 = {
    "name": "Felicity",
    "birthdate": "27-11-2011"
}

PET5_TYPE3 = {
    "name": "Muscles"
}

PET6_TYPE3 = {
    "name": "Junior"
}

PET7_TYPE4 = {
    "name": "Lazy",
    "birthdate": "07-08-2018"
}

PET8_TYPE4 = {
    "name": "Lemon",
    "birthdate": "27-03-2020"
}

# Global variables to store IDs
stored_ids = {}


def test_1_and_2_post_pet_types():
    """
    Tests 1-2: Execute POST /pet-types requests to both stores.
    Test 1: 3 POST requests to pet store #1 with PET_TYPE1, PET_TYPE2, PET_TYPE3
    Test 2: 3 POST requests to pet store #2 with PET_TYPE1, PET_TYPE2, PET_TYPE4
    Success: (i) unique ids per store, (ii) status 201, (iii) family/genus match
    """
    # Store #1 - 3 POSTs
    resp1 = requests.post(f"{STORE1_URL}/pet-types", json=PET_TYPE1)
    assert resp1.status_code == 201
    data1 = resp1.json()
    id_1 = data1["id"]
    assert data1["family"] == PET_TYPE1_VAL["family"]
    assert data1["genus"] == PET_TYPE1_VAL["genus"]
    stored_ids["id_1"] = id_1

    resp2 = requests.post(f"{STORE1_URL}/pet-types", json=PET_TYPE2)
    assert resp2.status_code == 201
    data2 = resp2.json()
    id_2 = data2["id"]
    assert data2["family"] == PET_TYPE2_VAL["family"]
    assert data2["genus"] == PET_TYPE2_VAL["genus"]
    stored_ids["id_2"] = id_2

    resp3 = requests.post(f"{STORE1_URL}/pet-types", json=PET_TYPE3)
    assert resp3.status_code == 201
    data3 = resp3.json()
    id_3 = data3["id"]
    assert data3["family"] == PET_TYPE3_VAL["family"]
    assert data3["genus"] == PET_TYPE3_VAL["genus"]
    stored_ids["id_3"] = id_3

    # Check uniqueness for store #1
    assert len({id_1, id_2, id_3}) == 3

    # Store #2 - 3 POSTs
    resp4 = requests.post(f"{STORE2_URL}/pet-types", json=PET_TYPE1)
    assert resp4.status_code == 201
    data4 = resp4.json()
    id_4 = data4["id"]
    assert data4["family"] == PET_TYPE1_VAL["family"]
    assert data4["genus"] == PET_TYPE1_VAL["genus"]
    stored_ids["id_4"] = id_4

    resp5 = requests.post(f"{STORE2_URL}/pet-types", json=PET_TYPE2)
    assert resp5.status_code == 201
    data5 = resp5.json()
    id_5 = data5["id"]
    assert data5["family"] == PET_TYPE2_VAL["family"]
    assert data5["genus"] == PET_TYPE2_VAL["genus"]
    stored_ids["id_5"] = id_5

    resp6 = requests.post(f"{STORE2_URL}/pet-types", json=PET_TYPE4)
    assert resp6.status_code == 201
    data6 = resp6.json()
    id_6 = data6["id"]
    assert data6["family"] == PET_TYPE4_VAL["family"]
    assert data6["genus"] == PET_TYPE4_VAL["genus"]
    stored_ids["id_6"] = id_6

    # Check uniqueness for store #2
    assert len({id_4, id_5, id_6}) == 3


def test_3_post_pets_to_store1_type1():
    """
    Test 3: Execute POST /pet-types/{id_1}/pets to pet-store #1
    with payload PET1_TYPE1 and PET2_TYPE1. 2 POSTs in total.
    Success: all return status 201
    """
    id_1 = stored_ids["id_1"]

    resp1 = requests.post(f"{STORE1_URL}/pet-types/{id_1}/pets", json=PET1_TYPE1)
    assert resp1.status_code == 201

    resp2 = requests.post(f"{STORE1_URL}/pet-types/{id_1}/pets", json=PET2_TYPE1)
    assert resp2.status_code == 201


def test_4_post_pets_to_store1_type3():
    """
    Test 4: Execute POST /pet-types/{id_3}/pets to pet-store #1
    with payload PET5_TYPE3 and PET6_TYPE3. 2 POSTs in total.
    Success: all return status 201
    """
    id_3 = stored_ids["id_3"]

    resp1 = requests.post(f"{STORE1_URL}/pet-types/{id_3}/pets", json=PET5_TYPE3)
    assert resp1.status_code == 201

    resp2 = requests.post(f"{STORE1_URL}/pet-types/{id_3}/pets", json=PET6_TYPE3)
    assert resp2.status_code == 201


def test_5_post_pet_to_store2_type1():
    """
    Test 5: Execute POST /pet-types/{id_4}/pets to pet-store #2
    with payload PET3_TYPE1.
    Success: return status 201
    """
    id_4 = stored_ids["id_4"]

    resp = requests.post(f"{STORE2_URL}/pet-types/{id_4}/pets", json=PET3_TYPE1)
    assert resp.status_code == 201


def test_6_post_pet_to_store2_type2():
    """
    Test 6: Execute POST /pet-types/{id_5}/pets to pet-store #2
    with payload PET4_TYPE2.
    Success: return status 201
    """
    id_5 = stored_ids["id_5"]

    resp = requests.post(f"{STORE2_URL}/pet-types/{id_5}/pets", json=PET4_TYPE2)
    assert resp.status_code == 201


def test_7_post_pets_to_store2_type4():
    """
    Test 7: Execute POST /pet-types/{id_6}/pets to pet-store #2
    with payload PET7_TYPE4 and PET8_TYPE4. 2 POSTs in total.
    Success: all return status 201
    """
    id_6 = stored_ids["id_6"]

    resp1 = requests.post(f"{STORE2_URL}/pet-types/{id_6}/pets", json=PET7_TYPE4)
    assert resp1.status_code == 201

    resp2 = requests.post(f"{STORE2_URL}/pet-types/{id_6}/pets", json=PET8_TYPE4)
    assert resp2.status_code == 201


def test_8_get_pet_type_by_id():
    """
    Test 8: Execute GET /pet-types/{id_2} to pet-store #1.
    Success: (i) JSON matches all fields in PET_TYPE2_VAL, (ii) status 200
    """
    id_2 = stored_ids["id_2"]

    resp = requests.get(f"{STORE1_URL}/pet-types/{id_2}")
    assert resp.status_code == 200

    data = resp.json()
    assert data["type"] == PET_TYPE2_VAL["type"]
    assert data["family"] == PET_TYPE2_VAL["family"]
    assert data["genus"] == PET_TYPE2_VAL["genus"]
    assert data["attributes"] == PET_TYPE2_VAL["attributes"]
    assert data["lifespan"] == PET_TYPE2_VAL["lifespan"]


def test_9_get_pets_by_type():
    """
    Test 9: Execute GET /pet-types/{id_6}/pets to pet-store #2.
    Success: (i) returned array contains pet objects with fields from
    PET7_TYPE4 and PET8_TYPE4, (ii) status 200
    """
    id_6 = stored_ids["id_6"]

    resp = requests.get(f"{STORE2_URL}/pet-types/{id_6}/pets")
    assert resp.status_code == 200

    pets = resp.json()
    assert isinstance(pets, list)
    assert len(pets) == 2

    # Find pets by name
    pet_names = {pet["name"] for pet in pets}
    assert PET7_TYPE4["name"] in pet_names
    assert PET8_TYPE4["name"] in pet_names

    # Verify fields for each pet
    for pet in pets:
        if pet["name"] == PET7_TYPE4["name"]:
            assert pet["birthdate"] == PET7_TYPE4["birthdate"]
        elif pet["name"] == PET8_TYPE4["name"]:
            assert pet["birthdate"] == PET8_TYPE4["birthdate"]
