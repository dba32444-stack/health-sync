from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

NOTION_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}

@app.route('/sync-health', methods=['POST'])
def sync_health():
    print("DATA RECEIVED:", request.json)
    data = request.json
    
    date_str = data.get("date", datetime.today().strftime('%Y-%m-%d'))
    
    # نقبل القيم بغض النظر عن حالة الحروف المرسلة من الشورتكت (كابيتال أو سمول)
    calories = data.get("Calories") or data.get("calories")
    protein = data.get("Protein") or data.get("protein")
    carbs = data.get("Carbs") or data.get("carbs")
    fats = data.get("Total Fat") or data.get("total fat") or data.get("fats") or data.get("Fats")
    fiber = data.get("Fiber") or data.get("fiber")

    search_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "Name", 
            "title": {
                "equals": date_str
            }
        }
    }
    
    response = requests.post(search_url, json=payload, headers=HEADERS)
    if response.status_code != 200:
        return jsonify({"error": "Failed to query Notion", "details": response.text}), 400
    
    results = response.json().get("results", [])

    # **هنا الربط الدقيق 100% مع أسماء أعمدة نوشن الفعلية:**
    properties = {
        "Name": {
            "title": [{"text": {"content": date_str}}]
        }
    }
    
    if calories is not None: properties["Calories"] = {"number": float(calories)}
    if protein is not None: properties["Protein"] = {"number": float(protein)}
    if carbs is not None: properties["Carbs"] = {"number": float(carbs)}
    if fats is not None: properties["Total Fat"] = {"number": float(fats)}
    if fiber is not None: properties["Fiber"] = {"number": float(fiber)}

    if len(results) > 0:
        page_id = results[0]["id"]
        update_url = f"https://api.notion.com/v1/pages/{page_id}"
        update_payload = {"properties": properties}
        
        update_res = requests.patch(update_url, json=update_payload, headers=HEADERS)
        if update_res.status_code == 200:
            return jsonify({"status": "success", "action": "updated", "page_id": page_id}), 200
        else:
            return jsonify({"error": "Failed to update page", "details": update_res.text}), 400
    else:
        create_url = "https://api.notion.com/v1/pages"
        create_payload = {
            "parent": {"database_id": DATABASE_ID},
            "properties": properties
        }
        
        create_res = requests.post(create_url, json=create_payload, headers=HEADERS)
        if create_res.status_code == 200:
            return jsonify({"status": "success", "action": "created"}}, 200
        else:
            return jsonify({"error": "Failed to create page", "details": create_res.text}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
