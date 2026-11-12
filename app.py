from flask import Flask, request, render_template, redirect, url_for, flash
import cv2
import pandas as pd
from pyzbar import pyzbar
from pathlib import Path
import numpy as np
import requests

app = Flask(__name__)
app.secret_key = "testkey"

storage_file = Path("books.csv")
open(storage_file, mode='a').close()  # Ensure the file exists

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

def docs_to_dataframe(data, isbn):
    docs = data.get("docs", [])
    if not docs:
        return None  # ISBN not found

    df = pd.DataFrame(docs)

    # keep only the columns you want; reindex avoids a KeyError if one is missing
    df = df.reindex(columns=[
        "title", "author_name", "first_publish_year", "language", "key"
    ])

    # turn lists like ['William P. Cross', 'Ofer Kenig'] into "William P. Cross, Ofer Kenig"
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: ", ".join(map(str, x)) if isinstance(x, list) else x
        )

    df.insert(0, "ISBN", isbn)  # the response doesn't contain the ISBN itself
    return df

def fetch_book_info(isbn):
    """Fetch book info from Open Library API"""
    url = f"https://openlibrary.org/search.json?q=isbn:{isbn}"
    try:
        r = requests.get(
        "https://openlibrary.org/search.json",
        params={"q": f"isbn:{isbn}"},
        timeout=5,
        )
        r.raise_for_status()
        df_new = docs_to_dataframe(r.json(), isbn)
        if df_new is not None:
            df_new.to_csv(storage_file, mode="a", header=not storage_file.exists(), index=False)
            return df_new
        else:
            return None
    except Exception as e:
        print(f"Error fetching book info for ISBN {isbn}: {e}")
    return None

@app.route("/", methods=["GET", "POST"])
def upload():
    
    if request.method == "POST":
        file = request.files["image"]
        if not file:
            flash("No file uploaded")
            return redirect(url_for("upload"))

        img_array = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            flash("Could not read image")
            return redirect(url_for("upload"))

        barcodes = pyzbar.decode(img)
        if not barcodes:
            flash("No barcode found")
            return redirect(url_for("upload"))
        
        for barcode in barcodes:
            isbn = barcode.data.decode("utf-8")
            print(isbn + "\n")
            book_info = fetch_book_info(isbn)
            if book_info is None or book_info.empty:
                flash(f"{isbn}: book info not found")
            else:
                flash(f"{isbn}: safed")
        return redirect(url_for("upload"))
    return render_template("index.html")
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
