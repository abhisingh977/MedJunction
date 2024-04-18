from flask import (
    Flask,
    url_for,
    render_template,
    request,
    redirect,
    make_response,
    session,
    jsonify,
    abort,
)
import requests

import pathlib
from pip._vendor import cachecontrol
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.cloud import firestore
from uuid import uuid1
from io import BytesIO
from datetime import datetime, timedelta
# from dotenv import load_dotenv
import google.auth.transport.requests
import logging
import os
from google.cloud import storage
from werkzeug.utils import secure_filename
from flask import send_file
import pytz
import json 
from flask_cors import CORS
import google.auth.exceptions

folder_name = "patient_profile_bucket"

# Check if the folder exists
if not os.path.exists(folder_name):
    # If it doesn't exist, create it
    os.makedirs(folder_name)
    print(f"Folder '{folder_name}' created successfully.")
else:
    print(f"Folder '{folder_name}' already exists.")


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper

with open('client_secret.json', 'r') as file:
    # Load the JSON data from the file
    data = json.load(file)

google_client_id = data["web"]["client_id"]
logging.basicConfig(level=logging.INFO)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "medjunction.json" 
GOOGLE_CLIENT_ID = google_client_id
client_secrets_file = "client_secret.json"

# Get current Indian Standard Time (IST)
ist = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist)
formatted_time = current_time.strftime("%d-%m-%Y")
# Specify the allowed file extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}

app = Flask("medjunction")
app.secret_key = "medjunction"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)  # Set session expiry to 30 minutes
# session.regenerate()
CORS(app)
storage_client = storage.Client()
bucket_name = "paitent_profile_bucket"
db = firestore.Client(project="medjunction")
paitent_collection = db.collection("paitent")


flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ],
    redirect_uri="https://medjunction-7dvpsozs3a-uc.a.run.app/callback",
)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/callback")
def callback():
    try:
        # Fetch token
        flow.fetch_token(authorization_response=request.url)

        # Verify state
        if session.get("state") != request.args.get("state"):
            return redirect_with_error("/login", "State does not match!")

        credentials = flow.credentials
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)

        # Verify ID token
        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID
        )

        # Update session
        session["google_id"] = id_info.get("sub")
        session["given_name"] = id_info.get("given_name")
        session["family_name"] = id_info.get("family_name")
        session["email"] = id_info.get("email")
        session["locale"] = id_info.get("locale")

        # Update Firestore
        doc_ref = paitent_collection.document(id_info.get("sub"))
        doc = doc_ref.get()
        if doc.exists:
            field_value = doc.get("count")
            doc_ref.update({"count": field_value + 1})
        else:
            doc_ref.set(
                {
                    "given_name": id_info.get("given_name"),
                    "family_name": id_info.get("family_name"),
                    "email": id_info.get("email"),
                    "locale": id_info.get("locale"),
                    "picture": id_info.get("picture"),
                    "count": 0,
                    "total_profile": "0",
                }
            )

        return redirect("/authed_user")
    except google.auth.exceptions.GoogleAuthError as e:
        logging.error("Google Authentication Error: %s", e)
        return redirect_with_error("/login", "Error occurred during authentication.")
    except Exception as e:
        logging.error("Callback Error: %s", e)
        return redirect_with_error("/login", "An unexpected error occurred.")


@app.route("/authed_user")
def authed_user():
    return render_template("home.html")

@app.route("/login")
def login():
    try:
        authorization_url, state = flow.authorization_url()
        session["state"] = state
        login_error = session.pop("login_error", None)
        return redirect(authorization_url)
    except Exception as e:
        logging.error("Login Error: %s", e)
        return "Error occurred during login."

def redirect_with_error(url, error_message):
    session["login_error"] = error_message
    return redirect(url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/")
def index():

    if "google_id" in session:
        # User is already logged in, redirect to the main page
        doc_ref = paitent_collection.document(session["google_id"])
        doc = doc_ref.get()
        
    return render_template("login_page.html")

@app.route("/get_all_profile")
def get_all_profile():
    user_ref = paitent_collection.document(session["google_id"])
    collections = user_ref.collections()
    patient_data = []
    for collection in collections:
        for doc in collection.stream():
            patient_data.append(doc.to_dict())

    return render_template("all_profile.html", patient_data=patient_data)

@app.route("/create_profile", methods=["GET", "POST"])
def create_profile():

    if request.method == "POST":
        user_ref = paitent_collection.document(session["google_id"])
        doc = user_ref.get()
        if doc.exists:
            total_profile = int(doc.get("total_profile")) + 1
            user_ref.update({"total_profile": str(total_profile)})
        total_profile_str = str(total_profile)
        paitent_ref = user_ref.collection(total_profile_str).document(total_profile_str)

        paitent_ref.set(
        {
        "name": request.form["name"],
        "sex": request.form["sex"],
        "location": request.form["location"],
        "insurance_provider": request.form["insurance"],
        "insurance": request.form["insurance_provider"],
        "collection_id": total_profile_str,
        "complaints_data": [],
        "co_morbidities": [],
        "past_history": [],
        "addiction_history": [],
        "surgery_history": [],
        "reports": [],
        })
        doc = paitent_ref.get()
        if doc.exists:
            patient_data = {"name": doc.get("name"),
            "insurance": doc.get("insurance"),
            "insurance_provider": doc.get("insurance_provider"),
            "location": doc.get("location"),
            "sex": doc.get("sex"),
            "collection_id": total_profile_str,
            }
        # Redirect to the profile page after editing
        return render_template("home.html")
    # If it's a GET request, just render the edit form
    return render_template("create_profile.html")

@app.route("/patient_profile")
def patient_profile():
    collection_id = request.args.get("collection_id")
    if not collection_id:
        return "collection_id is required to view the profile"
    session["collection_id"] = collection_id
    user_ref = paitent_collection.document(session["google_id"])
    paitent_ref = user_ref.collection(collection_id).document(collection_id)
    doc = paitent_ref.get()
    if doc.exists:
        patient_data = {
            "name": doc.get("name"),
            "insurance": doc.get("insurance"),
            "insurance_provider": doc.get("insurance_provider"),
            "location": doc.get("location"),
            "sex": doc.get("sex"),
            "collection_id": doc.get("collection_id"),
        }
        complaints_data = doc.get("complaints_data")
        co_morbidities = doc.get("co_morbidities")
        past_history = doc.get("past_history")
        addiction_history = doc.get("addiction_history")
        surgery_history = doc.get("surgery_history")
        reports = doc.get("reports")


    else:
        return "Profile does not exist"
    return render_template(
        "patient_profile.html",
        patient=patient_data,
        complaints=reversed(complaints_data),
        co_morbidities=reversed(co_morbidities),
        past_history=reversed(past_history),
        addiction_history=reversed(addiction_history),
        surgery_history=reversed(surgery_history),
        reports=reversed(reports),
    )

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if request.method == "POST":
        collection_id = request.form.get("collection_id")
        if not collection_id:
            return "collection_id is required to view the profile", 400  # Return a 400 Bad Request status
        session["collection_id"] = collection_id
        user_ref = paitent_collection.document(session["google_id"])
        paitent_ref = user_ref.collection(collection_id).document(collection_id)
        doc = paitent_ref.get()
        if not doc.exists:
            return "Patient data not found", 404  # Return a 404 Not Found status

        # Update patient data
        paitent_ref.update({
            "name": request.form["name"],
            "sex": request.form["sex"],
            "location": request.form["location"],
            "insurance_provider": request.form["insurance_provider"],
            "insurance": request.form["insurance"],
        })

        # Redirect to the profile page after editing
        return redirect(url_for("patient_profile", collection_id=collection_id))

    elif request.method == "GET":
        collection_id = request.args.get("collection_id")
        if not collection_id:
            return "collection_id is required to view the profile", 400
        user_ref = paitent_collection.document(session["google_id"])
        paitent_ref = user_ref.collection(collection_id).document(collection_id)
        doc = paitent_ref.get()
        if not doc.exists:
            return "Patient data not found", 404

        patient_data = {
            "name": doc.get("name"),
            "insurance": doc.get("insurance"),
            "insurance_provider": doc.get("insurance_provider"),
            "location": doc.get("location"),
            "sex": doc.get("sex"),
            "collection_id": collection_id
        }
        session["collection_id"] = collection_id
        return render_template("edit_profile.html", patient=patient_data)
    else:
        return "Invalid request method", 405  # Method Not Allowed

@app.route("/save_text", methods=["POST"])
def save_text():
    data = request.json
    text = data.get("text")
    text =  formatted_time +":  "+ text
    source = data.get("source")
    user_ref = paitent_collection.document(session["google_id"])
    collection_id = session["collection_id"] 
    print(collection_id)
    paitent_ref = user_ref.collection(collection_id).document(collection_id)
    doc = paitent_ref.get()
    if source == "complaints-new":
        if doc.exists:
            complaints_data=doc.get("complaints_data")
            complaints_data.append(text)
            paitent_ref.update({"complaints_data": complaints_data})
        
    elif source == "co-morbidities-new":
        if doc.exists:
            co_morbidities=doc.get("co_morbidities")
            co_morbidities.append(text)
            paitent_ref.update({"co_morbidities": co_morbidities})
        
    elif source == "surgery-history-new":
        if doc.exists:
            surgery_history=doc.get("surgery_history")
            surgery_history.append(text)
            paitent_ref.update({"surgery_history": surgery_history})
        
    elif source == "past-history-new":
        if doc.exists:
            past_history=doc.get("past_history")
            past_history.append(text)
            paitent_ref.update({"past_history": past_history})
        
    elif source == "addiction-history-new":
        if doc.exists:
            addiction_history=doc.get("addiction_history")
            addiction_history.append(text)
            paitent_ref.update({"addiction_history": addiction_history})
        
    # Here you can save the text to your database or perform any other required action
    print("Received text:", text)
    return jsonify({"success": True})


@app.route("/discard_text", methods=["POST"])
def discard_text():
    data = request.json
    text = data.get("text")
    source = data.get("source")
    user_ref = paitent_collection.document(session["google_id"])
    collection_id = session["collection_id"] 

    paitent_ref = user_ref.collection(collection_id).document(collection_id)
    doc = paitent_ref.get()

    if source == "complaints-new":
        complaints_data=doc.get("complaints_data")
        for i in reversed(range(len(complaints_data))):
            if text in complaints_data[i]:
                complaints_data.pop(i)
        paitent_ref.update({"complaints_data": complaints_data})

    elif source == "co-morbidities-new":
        co_morbidities=doc.get("co_morbidities")
        for i in reversed(range(len(co_morbidities))):
            if text in co_morbidities[i]:
                co_morbidities.pop(i)
        paitent_ref.update({"co_morbidities": co_morbidities})

    elif source == "surgery-history-new":
        surgery_history=doc.get("surgery_history")
        for i in reversed(range(len(surgery_history))):
            if text in surgery_history[i]:
                surgery_history.pop(i)
        paitent_ref.update({"surgery_history": surgery_history})

    elif source == "past-history-new":
        past_history=doc.get("past_history")
        for i in reversed(range(len(past_history))):
            if text in past_history[i]:
                past_history.pop(i)
        paitent_ref.update({"past_history": past_history})

    elif source == "addiction-history-new":
        addiction_history=doc.get("addiction_history")
        for i in reversed(range(len(addiction_history))):
            if text in addiction_history[i]:
                addiction_history.pop(i)
        paitent_ref.update({"addiction_history": addiction_history})

    print("Discarded text:", text)
    return jsonify({"success": True})

@app.route("/upload", methods=["POST"])
def upload_file():
    user_ref = paitent_collection.document(session["google_id"])
    collection_id = session["collection_id"] 
    paitent_ref = user_ref.collection(collection_id).document(collection_id)
    doc = paitent_ref.get()
    if doc.exists:
        patient_data = {
            "name": doc.get("name"),
            "insurance": doc.get("insurance"),
            "insurance_provider": doc.get("insurance_provider"),
            "location": doc.get("location"),
            "sex": doc.get("sex"),
            "collection_id": doc.get("collection_id"),
        }
        complaints_data = doc.get("complaints_data")
        co_morbidities = doc.get("co_morbidities")
        past_history = doc.get("past_history")
        addiction_history = doc.get("addiction_history")
        surgery_history = doc.get("surgery_history")
        reports = doc.get("reports")


    if request.method == "POST":
        file = request.files["file"]
        filename = secure_filename(file.filename)
        file_extension = os.path.splitext(filename)[1]
        file_extension = filename.split(".")[-1]
        custom_filename = request.form["filename"]
        filename = f"{formatted_time} {custom_filename}.{file_extension}"
        reports.append(filename)
        paitent_ref.update({"reports": reports})
        if file:
            # Upload file to Google Cloud Storage
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(filename)
            blob.upload_from_file(file)
            reports.append(filename)  # Append the URL instead of the file object
        else:
            return "Error uploading. Please try again!!!!"
        return redirect(url_for("patient_profile", collection_id=patient_data["collection_id"]))

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    # Here you will fetch the file from Google Cloud Storage
    # You'll need to provide the correct bucket name and implement the logic to retrieve the file
    # For simplicity, I'm assuming you have a storage_client and bucket_name already defined

    # Fetch the blob from Google Cloud Storage
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)

    # Check if the file exists
    if blob.exists():
        # Download the file to a temporary location
        temp_file_path = f"paitent_profile_bucket/{filename}"  # You can adjust this path as needed
        blob.download_to_filename(temp_file_path)

        # Serve the file for download
        return send_file(temp_file_path, as_attachment=True)


    # If the file doesn't exist, return a 404 error
    return "File not found", 404

@app.route('/create_hospital')
def create_hospital():
    return render_template("create_hospital.html")

@app.route('/submit_hospital', methods=['POST'])
def submit_hospital():
    if request.method == "POST":
        hospital_name = request.form.get('hospital_name')
        state = request.form.get('state')
        city = request.form.get('city')
        address = request.form.get('address')
        contact = request.form.get('contact')
        insurance = request.form.getlist('insurance')

        # Push data to Firestore
        hospital_ref = db.collection('hospitals').document()
        hospital_ref.set({
            'hospital_name': hospital_name,
            'address': address,
            'contact': contact,
            'state': state,
            'city': city,
            'insurance': insurance
        })

    return render_template("create_hospital.html")


@app.route('/get_hospital')
def get_hospital():
    hospitals = []
    # Retrieve hospitals from Firestore
    hospitals_ref = db.collection('hospitals').stream()
    for hospital in hospitals_ref:
        hospitals.append(hospital.to_dict())

    return render_template("get_hospital.html", hospitals=hospitals)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=os.getenv("PORT", 8080))
