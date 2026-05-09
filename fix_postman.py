import json

with open('cartify_postman_collection.json', 'r') as f:
    data = json.load(f)

def fix_item(item):
    if 'request' in item:
        req = item['request']
        if 'url' in req and isinstance(req['url'], dict) and 'raw' in req['url']:
            # Expand the URL correctly for Postman 2.1.0 to avoid the issue where it doesn't show
            raw_url = req['url']['raw']
            req['url'] = {
                "raw": raw_url,
                "host": ["{{base_url}}"] if raw_url.startswith("{{base_url}}") else raw_url.split('/')[0:3],
                "path": [p for p in raw_url.replace("{{base_url}}/", "").split('/') if p]
            }

        # Fix Upload Product
        if item['name'] == 'Upload Product':
            req['body'] = {
                "mode": "formdata",
                "formdata": [
                    { "key": "name", "value": "Discounted Shoes", "type": "text" },
                    { "key": "price", "value": "50.00", "type": "text" },
                    { "key": "original_price", "value": "100.00", "type": "text" },
                    { "key": "discount", "value": "50.0", "type": "text" },
                    { "key": "category", "value": "1", "type": "text" },
                    { "key": "image", "type": "file", "src": [] }
                ]
            }
        
        # Fix Edit Vendor Product
        if item['name'] == 'Edit Vendor Product':
            req['body'] = {
                "mode": "formdata",
                "formdata": [
                    { "key": "name", "value": "Updated Shoes", "type": "text" },
                    { "key": "price", "value": "45.00", "type": "text" },
                    { "key": "image", "type": "file", "src": [] }
                ]
            }

    if 'item' in item:
        for sub_item in item['item']:
            fix_item(sub_item)

for item in data['item']:
    fix_item(item)

with open('cartify_postman_collection.json', 'w') as f:
    json.dump(data, f, indent=4)

print("Done")
