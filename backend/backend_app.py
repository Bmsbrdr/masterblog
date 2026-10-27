from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from datetime import datetime

ID = "id"
TITLE = "title"
CONTENT = "content"
AUTHOR = "author"
DATE = "date"

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
CORS(app)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

POSTS = [
    {ID: 1, TITLE: "First post", CONTENT: "This is the first post.", AUTHOR: "Dennis", DATE: "2026-10-26"},
    {ID: 2, TITLE: "Second post", CONTENT: "This is the second post.", AUTHOR: "Dennis", DATE: "2026-10-26"}
]


@app.route('/api/posts', methods=['GET'])
def get_posts():
    sort = request.args.get('sort')
    direction = request.args.get('direction')
    requested_data = list(POSTS)

    if sort:
        reverse_order = (direction == "desc")

        if sort == DATE:
            requested_data = sorted(
                POSTS,
                key=lambda item: datetime.strptime(item.get(DATE, "1970-01-01"), "%Y-%m-%d"),
                reverse=reverse_order
            )
        elif sort in [TITLE, CONTENT, AUTHOR]:
            requested_data = sorted(
                POSTS,
                key=lambda item: item.get(sort, "").lower(),
                reverse=reverse_order
            )

    return jsonify(requested_data)


@app.route('/api/posts', methods=['POST'])
def post():
    request_data = request.get_json()

    if not request_data or TITLE not in request_data or CONTENT not in request_data:
        return jsonify({"error": "400 Bad Request - Title and content are required"}), 400

    if str(request_data[TITLE]).strip() == "" or str(request_data[CONTENT]).strip() == "":
        return jsonify({"error": "400 Bad Request - Fields cannot be empty"}), 400

    highest_id = max((item[ID] for item in POSTS)) if POSTS else 0

    new_post = {
        ID: highest_id + 1,
        TITLE: request_data[TITLE],
        CONTENT: request_data[CONTENT],
        AUTHOR: request_data.get(AUTHOR, "Unknown"),
        DATE: request_data.get(DATE, datetime.now().strftime("%Y-%m-%d"))
    }

    POSTS.append(new_post)
    return jsonify({"message": "201 Created"}), 201


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    for item in POSTS:
        if item[ID] == post_id:
            POSTS.remove(item)
            return jsonify({"message": "Successfully deleted. 200 OK"}), 200
    return jsonify({"error": "400 Bad Request"}), 400


@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    target_item = next((item for item in POSTS if item[ID] == post_id), None)
    if not target_item:
        return jsonify({"error": "404 Not Found"}), 400

    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "400 Bad Request"}), 400

    if TITLE in request_data:
        target_item[TITLE] = request_data[TITLE]
    if CONTENT in request_data:
        target_item[CONTENT] = request_data[CONTENT]
    if AUTHOR in request_data:
        target_item[AUTHOR] = request_data[AUTHOR]
    if DATE in request_data:
        target_item[DATE] = request_data[DATE]

    return jsonify({
        "message": "200 OK",
        ID: target_item[ID],
        TITLE: target_item[TITLE],
        CONTENT: target_item[CONTENT],
        AUTHOR: target_item[AUTHOR],
        DATE: target_item[DATE]
    }), 200


@app.route('/api/posts/search', methods=['GET'])
def search_post():
    target_title = request.args.get('title')
    target_content = request.args.get('content')
    target_author = request.args.get('author')
    target_date = request.args.get('date')

    general_search = request.args.get('search')

    result_items = []

    for item in POSTS:
        match = False

        if target_title and target_title.lower() in str(item.get(TITLE, "")).lower():
            match = True
        if target_content and target_content.lower() in str(item.get(CONTENT, "")).lower():
            match = True
        if target_author and target_author.lower() in str(item.get(AUTHOR, "")).lower():
            match = True
        if target_date and target_date in str(item.get(DATE, "")):
            match = True

        if general_search:
            gs = general_search.lower()
            if (gs in str(item.get(TITLE, "")).lower() or
                    gs in str(item.get(CONTENT, "")).lower() or
                    gs in str(item.get(AUTHOR, "")).lower() or
                    gs in str(item.get(DATE, "")).lower()):
                match = True

        if match and item not in result_items:
            result_items.append(item)

    return jsonify(result_items), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)