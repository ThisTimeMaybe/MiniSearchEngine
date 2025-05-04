from flask import Flask, request, render_template, redirect, url_for, flash, jsonify  # ✅ ADDED jsonify
from search_engine import search_query, index_documents
from scraper import scrape_google
import os
import cv2
import numpy as np
import requests
import json
import openai  # ✅ ADDED OpenAI
from werkzeug.utils import secure_filename
from whoosh.index import exists_in

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "static/uploads/"
IMAGE_DATABASE = "static/images/"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_DATABASE, exist_ok=True)

# API KEYS
BING_API_KEY = "cbb9aaa8eda46eefad95434407bf40cc"
BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/images/visualsearch"

# ✅ OpenAI API key from env
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Index documents only if index doesn't exist
if not exists_in("indexdir"):
    index_documents()

def get_image_features(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    orb = cv2.ORB_create()
    keypoints, descriptors = orb.detectAndCompute(img, None)
    return descriptors

def compare_images(query_img_path):
    query_features = get_image_features(query_img_path)
    if query_features is None:
        return []

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    results = []

    image_files = [img for img in os.listdir(IMAGE_DATABASE) if img.lower().endswith((".png", ".jpg", ".jpeg"))]
    for img_name in image_files:
        db_img_path = os.path.join(IMAGE_DATABASE, img_name)
        db_features = get_image_features(db_img_path)
        if db_features is None:
            continue
        matches = bf.match(query_features, db_features)
        matches = sorted(matches, key=lambda x: x.distance)
        score = sum(m.distance for m in matches[:10])
        results.append((img_name, score))

    results.sort(key=lambda x: x[1])
    return [f"/{IMAGE_DATABASE}{res[0]}" for res in results[:5]]

def search_bing_images(image_path):
    headers = {
        "Ocp-Apim-Subscription-Key": BING_API_KEY,
    }
    files = {
        "image": open(image_path, "rb"),
    }

    try:
        response = requests.post(BING_ENDPOINT, headers=headers, files=files)
        print("[BING API RESPONSE CODE]", response.status_code)
        print("[BING API RAW RESPONSE]", response.text)
        response.raise_for_status()
        data = response.json()

        print("[FULL BING JSON RESPONSE]")
        print(json.dumps(data, indent=2))

        similar_images = []
        for tag in data.get("tags", []):
            for action in tag.get("actions", []):
                if action.get("actionType") in ["VisualSearch", "PagesIncluding", "SimilarImages"]:
                    for item in action.get("data", {}).get("value", []):
                        url = item.get("thumbnailUrl") or item.get("contentUrl")
                        if url and url not in similar_images:
                            similar_images.append(url)

        return similar_images[:8]

    except Exception as e:
        print(f"[Bing Search Error] {e}")
        return []

@app.route("/")
def index():
    return render_template("index.html", results=None, snippets=None, image_results=None, web_results=None, query="")

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()
    if not query:
        flash("Please enter a search term.", "warning")
        return redirect(url_for("index"))

    results = search_query(query)
    snippets = [snippet for _, snippet in results] if results else []

    unique_results = {}
    for title, snippet in results:
        unique_results[title] = snippet
    final_results = [(title, unique_results[title]) for title in unique_results]

    web_results = scrape_google(query) or []

    return render_template(
        "index.html",
        results=final_results,
        snippets=snippets,
        query=query,
        image_results=None,
        web_results=web_results,
        zip=zip
    )

@app.route("/image_search", methods=["POST"])
def image_search():
    if "image" not in request.files or request.files["image"].filename == "":
        flash("No image uploaded.", "danger")
        return redirect(url_for("index"))

    file = request.files["image"]
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    image_results = compare_images(file_path)
    bing_results = search_bing_images(file_path)

    if not image_results and not bing_results:
        flash("No similar images found.", "info")

    return render_template(
        "index.html",
        image_results=image_results,
        web_results=bing_results,
        results=None,
        snippets=None,
        query=""
    )

# ✅ NEW: AI Assistant Chat Route
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"response": "Please send a valid message."})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}]
        )
        reply = response.choices[0].message["content"]
        return jsonify({"response": reply})
    except Exception as e:
        print(f"[OpenAI API ERROR] {e}")
        return jsonify({"response": "Sorry, I'm having trouble right now."})

if __name__ == "__main__":
    app.run(debug=True)
