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
from PIL import Image
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

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper

logging.basicConfig(level=logging.INFO)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "medjunction-8df36356d2d0.json" 
GOOGLE_CLIENT_ID = 
client_secrets_file = "client_secret.json"
print(client_secrets_file)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Get current Indian Standard Time (IST)
ist = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist)
formatted_time = current_time.strftime("%d-%m-%Y")
# Specify the allowed file extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}

app = Flask("medjunction")
app.secret_key = "medjunction"
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
    redirect_uri="http://127.0.0.1:8080/callback",
)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["given_name"] = id_info.get("given_name")
    session["family_name"] = id_info.get("family_name")
    session["email"] = id_info.get("email")
    session["locale"] = id_info.get("locale")

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

@app.route("/authed_user")
def authed_user():
    return render_template("home.html")

@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/protected_area")
@login_is_required
def protected_area():
    return f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"

@app.route("/")
def index():

    if "google_id" in session:
        # User is already logged in, redirect to the main page
        doc_ref = paitent_collection.document(session["google_id"])
        doc = doc_ref.get()
        
    return render_template("login_page.html")

@app.route("/get_all_profile")
def get_all_profile():
    doc_ref = paitent_collection.document(session["google_id"])

    if doc.exists:
        patient_data = {"name": doc.get("name"),
        "insurance": doc.get("insurance"),
        "insurance_provider": doc.get("insurance_provider"),
        "location": doc.get("location"),
        "sex": doc.get("sex"),
        "total_profile": doc.get("total_profile")
        }

    return render_template("all_profile.html", patient_data=patient_data)

@app.route("/create_profile", methods=["GET", "POST"])
def create_profile():

    if request.method == "POST":
        user_ref = paitent_collection.document(session["google_id"])
        doc = user_ref.get()
        if doc.exists:
            total_profile = int(doc.get("total_profile")) + 1
            user_ref.update({"total_profile": str(total_profile)})

        paitent_ref = user_ref.collection(str(total_profile)).document(str(total_profile))
        print(f"{paitent_ref} data")
        paitent_ref.set(
        {
        "name": request.form["name"],
        "sex": request.form["sex"],
        "location": request.form["location"],
        "insurance_provider": request.form["insurance"],
        "insurance": request.form["insurance_provider"],
        })
        doc = paitent_ref.get()
        if doc.exists:
            patient_data = {"name": doc.get("name"),
            "insurance": doc.get("insurance"),
            "insurance_provider": doc.get("insurance_provider"),
            "location": doc.get("location"),
            "sex": doc.get("sex")
            }
        # Redirect to the profile page after editing
        return render_template("home.html")
    # If it's a GET request, just render the edit form
    return render_template("create_profile.html")

@app.route("/patient_profile")
def patient_profile():

    doc_ref = paitent_collection.document(session["google_id"])
    doc = doc_ref.get()
    if doc.exists:
        patient_data = {
            "name": doc.get("name"),
            "insurance": doc.get("insurance"),
            "insurance_provider": doc.get("insurance_provider"),
            "location": doc.get("location"),
            "sex": doc.get("sex"),
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

@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if request.method == "POST":
        doc_ref.update(
        {
        "name": request.form["name"],
        "sex": request.form["sex"],
        "location": request.form["location"],
        "insurance_provider": request.form["insurance"],
        "insurance": request.form["insurance_provider"],
        })
        doc = doc_ref.get()
        if doc.exists:
            patient_data = {"name": doc.get("name"),
            "insurance": doc.get("insurance"),
            "insurance_provider": doc.get("insurance_provider"),
            "location": doc.get("location"),
            "sex": doc.get("sex")
            }
        # Redirect to the profile page after editing
        return redirect(url_for("index"))
    # If it's a GET request, just render the edit form
    return render_template("edit_profile.html", patient=patient_data)

@app.route("/save_text", methods=["POST"])
def save_text():
    data = request.json
    text = data.get("text")
    text =  formatted_time +":  "+ text
    source = data.get("source")
    doc = doc_ref.get()

    if source == "complaints-new":
        if doc.exists:
            complaints_data=doc.get("complaints_data")
            complaints_data.append(text)
            doc_ref.update({"complaints_data": complaints_data})
        
    elif source == "co-morbidities-new":
        if doc.exists:
            co_morbidities=doc.get("co_morbidities")
            co_morbidities.append(text)
            doc_ref.update({"co_morbidities": co_morbidities})
        
    elif source == "surgery-history-new":
        if doc.exists:
            surgery_history=doc.get("surgery_history")
            surgery_history.append(text)
            doc_ref.update({"surgery_history": surgery_history})
        
    elif source == "past-history-new":
        if doc.exists:
            past_history=doc.get("past_history")
            past_history.append(text)
            doc_ref.update({"past_history": past_history})
        
    elif source == "addiction-history-new":
        if doc.exists:
            addiction_history=doc.get("addiction_history")
            addiction_history.append(text)
            doc_ref.update({"addiction_history": addiction_history})
        
    # Here you can save the text to your database or perform any other required action
    print("Received text:", text)
    return jsonify({"success": True})


@app.route("/discard_text", methods=["POST"])
def discard_text():
    data = request.json
    text = data.get("text")
    source = data.get("source")
    doc = doc_ref.get()
    if source == "complaints-new":
        if doc.exists:
            complaints_data=doc.get("complaints_data")
            for i in reversed(range(len(complaints_data))):
                if text in complaints_data[i]:
                    complaints_data.pop(i)
            doc_ref.update({"complaints_data": complaints_data})
    elif source == "co-morbidities-new":
        co_morbidities=doc.get("co_morbidities")
        for i in reversed(range(len(co_morbidities))):
            if text in co_morbidities[i]:
                co_morbidities.pop(i)
        doc_ref.update({"co_morbidities": co_morbidities})
    elif source == "surgery-history-new":
        surgery_history=doc.get("surgery_history")
        for i in reversed(range(len(surgery_history))):
            if text in surgery_history[i]:
                surgery_history.pop(i)
        doc_ref.update({"surgery_history": surgery_history})
    elif source == "past-history-new":
        past_history=doc.get("past_history")
        for i in reversed(range(len(past_history))):
            if text in past_history[i]:
                past_history.pop(i)
        doc_ref.update({"past_history": past_history})
    elif source == "addiction-history-new":
        addiction_history=doc.get("addiction_history")
        for i in reversed(range(len(addiction_history))):
            if text in addiction_history[i]:
                addiction_history.pop(i)
        doc_ref.update({"addiction_history": addiction_history})

    print("Discarded text:", text)
    return jsonify({"success": True})

@app.route("/upload", methods=["POST"])
def upload_file():
    doc = doc_ref.get()
    reports=doc.get("reports")
    print("reports")
    print(reports)
    if request.method == "POST":
        file = request.files["file"]
        filename = secure_filename(file.filename)
        file_extension = os.path.splitext(filename)[1]
        file_extension = filename.split(".")[-1]
        custom_filename = request.form["filename"]
        filename = f"{formatted_time} {custom_filename}.{file_extension}"
        reports.append(filename)
        doc_ref.update({"reports": reports})
        if file:
            # Upload file to Google Cloud Storage
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(filename)
            blob.upload_from_file(file)
            reports.append(filename)  # Append the URL instead of the file object
        else:
            return "Error uploading. Please try again!!!!"
        return redirect(url_for("index"))

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

if __name__ == "__main__":
    app.run(debug=True, port=8080)
