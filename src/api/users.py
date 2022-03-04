# -*- coding: utf-8 -*
"""
    src.api.users
    ~~~~~~~~~~~~~
    Functions:
        register_user()
        update_user()
        delete_user()
        get_user()
"""
from flask import Response, request
from src.common.decorators import admin_only, check_token
from werkzeug.exceptions import BadRequest, NotFound
from firebase_admin import storage, auth
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from flask import jsonify

from src.common.database import db
from src.api import Blueprint

users: Blueprint = Blueprint("users", __name__)


@users.post("/register_user")
@check_token
def register_user() -> Response:
    """
    register a new user
    ---
    tags:
        - users
    parameters:
        - in: header
          name: Authorization
          schema:
            type: string
          required: true
    requestBody:
        content:
            application/json:
                schema:
                    $ref: '#/components/schemas/UserRegister'
    responses:
        201:
            description: User registered
        400:
            description: Bad request
        401:
            description: Unauthorized - the provided token is not valid
        404:
            description: NotFound
        500:
            description: Internal API Error
    """
    # check tokens and get uid from token
    token: str = request.headers["Authorization"]
    decoded_token: dict = auth.verify_id_token(token)
    uid: str = decoded_token.get("uid")
    user_data: dict = request.get_json()

    # check if the user is in the table or not
    user_ref = db.collection("User").document(uid)
    if user_ref.get().exists == True:
        return BadRequest("The user already registered")

    # save data to firestore batabase
    entry: dict = dict()
    entry["name"] = user_data.get("name")
    entry["email"] = decoded_token.get("email")
    entry["user_status"] = 1
    entry["dod"] = user_data.get("dod")
    entry["grade"] = user_data.get("grade")
    entry["rank"] = user_data.get("rank")
    entry["branch"] = user_data.get("branch")
    entry["superior"] = user_data.get("superior")
    entry["level"] = user_data.get("level")

    # if user upload the profile picture
    if "profile_picture" in user_data:
        bucket = storage.bucket()
        profile_picture: str = "profile_picture/" + str(uuid4())
        blob = bucket.blob(profile_picture)
        blob.upload_from_string(
            user_data["profile_picture"], content_type="image"
        )
        entry["profile_picture"] = profile_picture

    if "description" in user_data:
        entry["description"] = user_data["description"]
        if "Commander" in entry["description"]:
            entry["commander"] = True
        else:
            entry["commander"] = False

    if "phone" in user_data:
        entry["phone"] = user_data.get("phone")

    if user_data.get("grade")[0:1] == "O" or user_data.get("grade")[0:1] == "W":
        entry["officer"] = True
    else:
        entry["officer"] = False

    # upload to the user table
    db.collection("User").document(uid).set(entry)

    return Response("User registered", 201)


@users.put("/update_user")
@check_token
def update_user() -> Response:
    """
    Update user data
    ---
    tags:
        - users
    parameters:
        - in: header
          name: Authorization
          schema:
            type: string
          required: true
    requestBody:
        content:
            application/json:
                schema:
                    $ref: '#/components/schemas/UserUpdate'
    responses:
        201:
            description: Successfully update user data
        400:
            description: Bad request
        401:
            description: Unauthorized - the provided token is not valid
        404:
            description: NotFound
        415:
            description: Unsupported media type.
        500:
            description: Internal API Error
    """
    # check tokens and get uid from token
    token: str = request.headers["Authorization"]
    decoded_token: dict = auth.verify_id_token(token)
    uid: str = decoded_token.get("uid")
    data: dict = request.get_json()

    # check if the user is in the table or not
    user_ref = db.collection("User").document(uid)
    if user_ref.get().exists == False:
        return NotFound("The user was not found")
    user: dict = user_ref.get().to_dict()
    bucket = storage.bucket()

    # update the user table
    if "grade" in data:
        user_ref.update({"grade": data.get("grade")})
        if data.get("grade")[0:1] == "O" or data.get("grade")[0:1] == "W":
            user_ref.update({"officer": True})
        else:
            user_ref.update({"officer": False})

    if "rank" in data:
        user_ref.update({"rank": data.get("rank")})

    if "branch" in data:
        user_ref.update({"branch": data.get("branch")})

    if "superior" in data:
        user_ref.update({"superior": data.get("superior")})

    if "phone" in data:
        user_ref.update({"phone": data.get("phone")})

    if "level" in data:
        user_ref.update({"level": data.get("level")})

    if "description" in data:
        user_ref.update({"description": data.get("description")})

    if "profile_picture" in data:
        profile_picture_path: str = ""
        if "profile_picture" in user:
            profile_picture_path = user.get("profile_picture")
        else:
            profile_picture_path = "profile_picture/" + str(uuid4())
            user_ref.update({"profile_picture": profile_picture_path})
        blob = bucket.blob(profile_picture_path)
        blob.upload_from_string(
            data.get("profile_picture"), content_type="image"
        )

    if "signature" in data:
        signature_path: str = ""
        if "signature" in user:
            signature_path = user.get("signature")
        else:
            signature_path = "signature/" + str(uuid4())
            user_ref.update({"signature": signature_path})
        blob = bucket.blob(signature_path)
        blob.upload_from_string(data.get("signature"), content_type="image")

    return Response("Successfully update user data", 200)


@users.delete("/delete_user/<uid>")
@check_token
@admin_only
def delete_user(uid: str) -> Response:
    """
    Delete the user from Firebase Storage.
    ---
    tags:
        - users
    summary: Deletes a user
    parameters:
        - in: header
          name: Authorization
          schema:
            type: string
          required: true
    responses:
        200:
            description: User deleted
        400:
            description: Bad request
        401:
            description: Unauthorized - the provided token is not valid
        404:
            description: NotFound
        500:
            description: Internal API Error
    """
    # get the user date from the user table
    user_ref = db.collection("User").document(uid)
    if user_ref.get().exists == False:
        return NotFound("The user was not found")
    user: dict = user_ref.get().to_dict()

    # delete the signature and profile_picture from firebase storage
    bucket = storage.bucket()
    if "signature" in user:
        blob = bucket.blob(user.get("signature"))
        if not blob.exists():
            return NotFound("The signature not found.")
        blob.delete()

    if "profile_picture" in user:
        blob = bucket.blob(user.get("profile_picture"))
        if not blob.exists():
            return NotFound("The profile_picture not found.")
        blob.delete()

    # delete record from user table
    user_ref.delete()

    return Response("User Deleted", 200)


@users.get("/get_user")
@check_token
def get_user() -> Response:
    """
    Get a user info from Firebase Storage.
    ---
    tags:
        - users
    summary: Gets a user
    parameters:
        - in: header
          name: Authorization
          schema:
            type: string
          required: true
    responses:
        200:
            content:
                application/json:
                    schema:
                        '#/components/schemas/User'
        400:
            description: Bad request
        401:
            description: Unauthorized - the provided token is not valid
        404:
            description: NotFound
        415:
            description: Unsupported media type.
        500:
            description: Internal API Error
    """
    token: str = request.headers["Authorization"]
    decoded_token: dict = auth.verify_id_token(token)
    uid: str = decoded_token.get("uid")

    # check if the user exists
    user_ref = db.collection("User").document(uid)
    if user_ref.get().exists == False:
        return NotFound("The user was not found")

    user: dict = user_ref.get().to_dict()

    # get the signature and the profile picture
    bucket = storage.bucket()

    if "signature" in user:
        signature_path: str = user.get("signature")
        blob = bucket.blob(signature_path)

        if not blob.exists():
            return NotFound("The signature not found.")

        # download the signature image
        signature = blob.download_as_bytes()
        user["signature"] = signature.decode("utf-8")

    if "profile_picture" in user:
        profile_picture_path: str = user.get("profile_picture")
        blob = bucket.blob(profile_picture_path)

        if not blob.exists():
            return NotFound("The profile picture not found.")

        # download the profile_picture image
        profile_picture = blob.download_as_bytes()
        user["profile_picture"] = profile_picture.decode("utf-8")

    return jsonify(user), 200


@users.get("/get_users")
@check_token
def get_users() -> Response:
    """
    Get a file from Firebase Storage.
    ---
    tags:
        - users
    summary: Gets a file
    parameters:
        - in: header
          name: Authorization
          schema:
            type: string
          required: true
        - in: query
          name: target
          schema:
            type: string
          required: false
        - in: query
          name: page_limit
          schema:
            type: integer
          required: false
    responses:
        200:
            content:
                application/json:
                    schema:
                        type: array
                        items:
                            $ref: '#/components/schemas/User'
        400:
            description: Bad request
        401:
            description: Unauthorized - the provided token is not valid
        404:
            description: NotFound
        415:
            description: Unsupported media type.
        500:
            description: Internal API Error
    """
    # the default page limits is 10
    page_limit: int = 10
    if "page_limit" in request.args:
        page_limit = request.args.get("page_limit", default=10, type=int)

    user_docs: list = []
    target: str = request.args.get("target", type=str)

    # exact search
    if "target" in request.args:
        if target == "officer":
            user_docs = (
                db.collection("User")
                .where("officer", "==", True)
                .limit(page_limit)
                .stream()
            )
        elif target == "commander":
            user_docs = (
                db.collection("User")
                .where("commander", "==", True)
                .limit(page_limit)
                .stream()
            )
        elif target == "level":
            token: str = request.headers["Authorization"]
            decoded_token: dict = auth.verify_id_token(token)
            uid: str = decoded_token.get("uid")
            # check if the user exists
            user_ref = db.collection("User").document(uid)
            if user_ref.get().exists == False:
                return NotFound("The user was not found")
            level: str = user_ref.get().to_dict().get("level")
            user_docs = (
                db.collection("User")
                .where("level", ">", level)
                .limit(page_limit)
                .stream()
            )
    else:
        user_docs = db.collection("User").limit(page_limit).stream()

    users: list = []
    for user in user_docs:
        users.append(user.to_dict())

    return jsonify(users), 200


@users.get("/search_users")
# @check_token
def search_users() -> Response:
    """
    Search users from Firebase Storage.
    ---
    tags:
        - users
    summary: Searches a user
    parameters:
        - in: header
          name: Authorization
          schema:
            type: string
          required: true
        - in: query
          name: name
          schema:
            type: string
            required: true
    responses:
        200:
            content:
                application/json:
                    schema:
                        type: array
                        items:
                            $ref: '#/components/schemas/User'
        400:
            description: Name is required
        404:
            description: No users found
        500:
            description: Internal API Error
    """
    # token: str = request.headers["Authorization"]
    # decoded_token: dict = auth.verify_id_token(token)
    # uid: str = decoded_token.get("uid")
    res: list = []
    uid = "123"

    if not request.args.get("name"):
        return BadRequest("Name is required")

    user_docs = db.collection("User").stream()

    for user in user_docs:
        user_dict: dict = user.to_dict()

        if user_dict.get("uid") == uid or not user_dict.get("name"):
            continue
        if request.args.get("name") in user_dict.get(
            "name"
        ) or request.args.get("name") == user_dict.get("name"):
            res.append(user_dict)

    if len(res) == 0:
        return NotFound("No users found")

    return jsonify(res), 200
