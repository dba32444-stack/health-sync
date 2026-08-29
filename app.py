from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

# نأخذ التوكن والـ Database ID من متغيرات البيئة
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
    data = request.json
    
    # البيانات اللي بتجينا من الآيفون
    date_str = data.get("date", datetime.today().strftime('%Y-%m-%d'))
    calories = data.get("calories")
    protein = data.get("protein")
    carbs = data.get("carbs")
    fats = data.get("fats")
    fiber = data.get("fiber")

    # الخطوة 1: البحث في نوشن هل تاريخ اليوم موجود مسبقاً؟
    search_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "Name",  # عمود العنوان (التاريخ)
            "title": {
                "equals": date_str
            }
        }
    }
    
    response = requests.post(search_url, json=payload, headers=HEADERS)
    if response.status_code != 200:
        return jsonify({"error": "Failed to query Notion", "details": response.text}), 400
    
    results = response.json().get("results", [])

    # تجهيز خصائص الماكروز مطابقة تماماً لأسماء أعمدة نوشن لدك
    properties = {
        "Name": {
            "title": [{"text": {"content": date_str}}]
        }
    }
    
    if calories is not None: properties["Calories"] = {"number": float(calories)}
    if protein is not None: properties["Protein"] = {"number": float(protein)}
    if carbs is not None: properties["Carbs"] = {"number": float(carbs)}
    if fats is not None: properties["Total fat"] = {"number": float(fats)}  # تم التعديل هنا لتطابق عمودك
    if fiber is not None: properties["Fiber"] = {"number": float(fiber)}

    # الخطوة 2: الشرط الذكي (تحديث الصف الموجود أو إنشاء صف جديد)
    if len(results) > 0:
        # الصف موجود مسبقاً لنفس اليوم! تحديثه (PATCH) بدل ما يسوي صف جديد
        page_id = results[0]["id"]
        update_url = f"https://api.notion.com/v1/pages/{page_id}"
        update_payload = {"properties": properties}
        
        update_res = requests.patch(update_url, json=update_payload, headers=HEADERS)
        if update_res.status_code == 200:
            return jsonify({"status": "success", "action": "updated", "page_id": page_id}), 200
        else:
            return jsonify({"error": "Failed to update page", "details": update_res.text}), 400
    else:
        # الصف غير موجود! إنشاء صف جديد (POST)
        create_url = "https://api.notion.com/v1/pages"
        create_payload = {
            "parent": {"database_id": DATABASE_ID},
            "properties": properties
        }
        
        create_res = requests.post(create_url, json=create_payload, headers=HEADERS)
        if create_res.status_code == 200:
            return jsonify({"status": "success", "action": "created"}), 200
        else:
            return jsonify({"error": "Failed to create page", "details": create_res.text}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
