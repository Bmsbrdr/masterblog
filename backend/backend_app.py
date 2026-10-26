from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

ID = "id"
TITLE = "title"
CONTENT = "content"

SWAGGER_URL = "/api/docs"
API_URL = "/static/masterblog.json"

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': 'Masterblog API'
    }
)

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

POSTS = [
    {ID: 1, TITLE: "First post", CONTENT: "This is the first post."},
    {ID: 2, TITLE: "Second post", CONTENT: "This is the second post."},
]


@app.route('/api/posts', methods=['GET'])
def get_posts():
    sort = request.args.get('sort')
    direction = request.args.get('direction')
    requested_data = POSTS

    sort_key = ID
    if sort == "title":
        sort_key = TITLE
    elif sort == "content":
        sort_key = CONTENT
    else:
        return jsonify({"error": "400 bad request"}), 400

    reverse_order = (direction == "desc")

    if sort or direction:
        requested_data = sorted(POSTS, key=lambda item: item[sort_key], reverse=reverse_order)

    return jsonify(requested_data)

@app.route('/api/posts', methods=['POST'])
def post():
    request_data = request.get_json()
    if TITLE not in request_data.keys() or CONTENT not in request_data.keys():
        return jsonify({"error": "400 Bad Request"},),400
    if request_data[TITLE] == "" or request_data["content"] == "":
        return jsonify({"error": "400 Bad Request"},),400
    highest_id = max((item[ID] for item in POSTS))
    POSTS.append({"id": highest_id+1, TITLE: request_data[TITLE], "content": request_data[CONTENT]})
    return jsonify({"message": "201 Created"}), 201

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    for item in POSTS:
        if item[ID] == post_id:
            POSTS.remove(item)
            return jsonify({"message": "Successfully deleted. 200 OK"}), 200
    return jsonify({"error": "400 Bad Request"}, ), 400

@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    if not any(item[ID] == post_id for item in POSTS):
        return jsonify({"error": "404 Not Found"}), 400
    request_data = request.get_json()

    for item in POSTS:
        if item["id"] == post_id:
            if TITLE  in request_data.keys() and item[TITLE] != request_data[TITLE]:
                item[TITLE] = request_data[TITLE]
            if CONTENT in request_data.keys() and item[CONTENT] != request_data[CONTENT]:
                item[CONTENT] = request_data[CONTENT]
            return jsonify({"message": "200 OK", ID: item[ID], TITLE: item[TITLE], CONTENT: item[CONTENT]}), 200
    return jsonify({"message": "400b Bad Request"}), 200

@app.route('/api/posts/search', methods=['GET'])
def search_post():
    target_title = request.args.get('title')
    target_content = request.args.get('content')
    result_items = []
    if target_title is not None:
        for item in POSTS:
            raw_string = item[TITLE]
            if isinstance(raw_string, str):
                result = target_title.lower() in raw_string.lower()
                if result:
                    result_items.append(item)

    if target_content is not None:
        for item in POSTS:
            raw_string = item[CONTENT]
            if isinstance(raw_string, str):
                result = target_content.lower() in raw_string.lower()
                if result:
                    result_items.append(item)

    return jsonify(result_items), 200
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
