from flask import (
    Flask,
    url_for,
    render_template,
    request,
    redirect,
    make_response,
    session,
    jsonify,
)
from google.cloud import firestore
from uuid import uuid1
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
# from dotenv import load_dotenv
import logging
import os
from google.cloud import storage
from werkzeug.utils import secure_filename
from flask import send_file
import pytz


logging.basicConfig(level=logging.INFO)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "medjunction-8df36356d2d0.json" 
# Get current Indian Standard Time (IST)
ist = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist)
formatted_time = current_time.strftime("%d-%m-%Y")
# Specify the allowed file extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}

app = Flask("medjunction")

session_uuid = str(uuid1())
# Set the path where uploaded files will be saved
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

storage_client = storage.Client()
bucket_name = "paitent_profile_bucket"
db = firestore.Client(project="medjunction")
paitent_collection = db.collection("paitent")
doc_ref = paitent_collection.document("2")
# doc_ref.set(
#     {
#     "name": "Abhis Doe",
#     "sex": "Male",
#     "location": "Gorakhpur, India",
#     "insurance_provider": "star",
#     "insurance": "AKJKJSDF123R3",
# }
# )
# doc_ref.update(
#     {"complaints_data":["27/Mar/2024: Complaint 1, Complaint 2",
#     "29/Mar/2024:  Complaint 3",]}
# )

# doc_ref.update(
#     {"co_morbidities":["27/Mar/2024: Complaint 1, Complaint 2",
#     "29/Mar/2024:  Complaint 3",]}
# )


# doc_ref.update(
#     {"hopi":["27/Mar/2024: Complaint 1, Complaint 2",
#     "29/Mar/2024:  Complaint 3",]}
# )

# doc_ref.update(
#     {"surgery_history":["27/Mar/2024: Complaint 1, Complaint 2",
#     "29/Mar/2024:  Complaint 3",]}
# )

# doc_ref.update(
#     {"addiction_history":["27/Mar/2024: Complaint 1, Complaint 2",
#     "29/Mar/2024:  Complaint 3",]}
# )

# doc_ref.update(
#     {"past_history":["27/Mar/2024: Complaint 1, Complaint 2",
#     "29/Mar/2024:  Complaint 3",]}
# )


# doc_ref.update(
#     {"reports":["27/Mar/2024: Complaint 1, Complaint 2",
#     "29/Mar/2024:  Complaint 3",]}
# )


@app.route("/")
def index():

    doc = doc_ref.get()
    print(doc)
    if doc.exists:
        patient_data = {"name": doc.get("name"),
        "insurance": doc.get("insurance"),
        "insurance_provider": doc.get("insurance_provider"),
        "location": doc.get("location"),
        "sex": doc.get("sex")
        }

        complaints_data = doc.get("complaints_data")
        co_morbidities = doc.get("co_morbidities")
        past_history = doc.get("past_history")
        addiction_history = doc.get("addiction_history")
        surgery_history = doc.get("surgery_history")
        reports = doc.get("reports")
    else:
        return "Profile does not exists"
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

@app.route('/edit_profile_page')
def edit_profile_page():
    doc = doc_ref.get()

    if doc.exists:
        patient_data = {"name": doc.get("name"),
        "insurance": doc.get("insurance"),
        "insurance_provider": doc.get("insurance_provider"),
        "location": doc.get("location"),
        "sex": doc.get("sex")
        }
    return render_template('edit_profile.html',patient=patient_data)


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
    app.run(debug=True, port=8081)
