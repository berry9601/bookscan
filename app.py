from flask import Flask, request, render_template, jsonify
import cv2
import pandas as pd
from pyzbar import pyzbar
from pathlib import Path
import numpy as np
import requests

app = Flask(__name__)
excel_file = Path("books.xlsx")

def get_author_name(author_key):
    """Fetch author name from Open Library"""
    url = f"https://openlibrary.org{author_key}.json"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("name", author_key)
    except Exception as e:
        print(f"Error fetching author {author_key}: {e}")
    return author_key  # fallback

def fetch_book_info(isbn):
    """Fetch book info from Open Library API"""
    url = f"https://openlibrary.org/isbn/"+isbn+".json"
    params = {
        "bibkeys": f"ISBN:{isbn}",
        "format": "json",
        "jscmd": "data"
    }
    response = requests.get(url)
    if response.status_code != 200:
        return None
    print(response.json())
    data = response.json()
    book_key = f"ISBN:{isbn}"
    excel_file = Path("books.xlsx")
    book_data = flatten_book_data(data)
    df_new = pd.DataFrame([book_data])
    if excel_file.exists():
        df_existing = pd.read_excel(excel_file)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_excel(excel_file, index=False)


def flatten_book_data(book):
    # Fetch full author names
    author_names = []
    for a in book.get("authors", []):
        key = a.get("key", "")
        if key:
            author_names.append(get_author_name(key))

    return {
        "ISBN": book.get("isbn_13", [""])[0],
        "Title": book.get("title", ""),
        "Subtitle": book.get("subtitle", ""),
        "Full Title": book.get("full_title", ""),
        "Authors": ", ".join(author_names),
        "Publishers": ", ".join(book.get("publishers", [])),
        "Publish Date": book.get("publish_date", ""),
        "Subjects": ", ".join(book.get("subjects", [])),
        "Language": ", ".join(l.get("key", "") for l in book.get("languages", [])),
        "Pages": book.get("pagination", ""),
        "Classification": ", ".join(book.get("lc_classifications", [])),
        "Created": book.get("created", {}).get("value", ""),
        "Last Modified": book.get("last_modified", {}).get("value", "")
    }

@app.route("/", methods=["GET", "POST"])
def upload():
    isbn = None
    if request.method == "POST":
        file = request.files["image"]
        img_array = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        barcodes = pyzbar.decode(img)
        if barcodes:
            isbn = barcodes[0].data.decode("utf-8")
            print(isbn + "/n")
            book_info = fetch_book_info(isbn)
            #if not book_info:
            #    return jsonify({"status": "error", "message": "Book info not found"}), 404
            
    return render_template("index.html", isbn=isbn)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
