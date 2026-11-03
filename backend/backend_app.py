from datetime import date, datetime
import json
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError

ID = "id"
TITLE = "title"
CONTENT = "content"
AUTHOR = "author"
DATE = "date"

BLOGPOSTS = "blogposts"
POSTS_FILE = Path(__file__).with_name("posts.json")

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


def load_posts():
    """Read the stored posts and any additional database metadata as UTF-8."""
    try:
        with POSTS_FILE.open("r", encoding="utf-8") as file:
            file_data = json.load(file)
        if not isinstance(file_data, dict):
            raise ValueError("Database must be an object")
        posts = file_data.get(BLOGPOSTS)
        if not isinstance(posts, list) or any(
            not isinstance(item, dict)
            or type(item.get(ID)) is not int
            or not isinstance(item.get(TITLE), str)
            or not isinstance(item.get(CONTENT), str)
            for item in posts
        ):
            raise ValueError("Database contains invalid posts")
        return file_data
    except (OSError, ValueError) as error:
        app.logger.exception("Could not read posts")
        raise InternalServerError("Could not load posts") from error


def save_posts(file_data):
    """Write the updated database as UTF-8, preserving its metadata."""
    try:
        with POSTS_FILE.open("w", encoding="utf-8") as file:
            json.dump(file_data, file, indent=4, ensure_ascii=False)
    except (OSError, ValueError, TypeError) as error:
        app.logger.exception("Could not save posts")
        raise InternalServerError("Could not save posts") from error


@app.errorhandler(HTTPException)
def handle_http_error(error):
    """Return HTTP errors using the same JSON schema as route errors."""
    response = error.get_response()
    response.data = app.json.dumps({"message": error.description})
    response.content_type = "application/json"
    return response


def validate_post_fields(data):
    """Return a validation message for invalid supplied fields, if any."""
    for field in (TITLE, CONTENT, AUTHOR, DATE):
        if field in data and not isinstance(data[field], str):
            return f"{field} must be a string"
    for field in (TITLE, CONTENT):
        if field in data and not data[field].strip():
            return f"{field} cannot be empty"
    if DATE in data:
        try:
            parsed_date = date.fromisoformat(data[DATE])
            if parsed_date.isoformat() != data[DATE]:
                raise ValueError("Date must use YYYY-MM-DD")
        except ValueError:
            return "date must be a valid date in YYYY-MM-DD format"
    return None


@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Return all posts with optional sorting."""
    sort = request.args.get('sort')
    direction = request.args.get('direction')

    if sort is not None and sort not in (TITLE, CONTENT, AUTHOR, DATE):
        return jsonify({"message": "Invalid sort field"}), 400
    if direction is not None and direction not in ("asc", "desc"):
        return jsonify({"message": "Invalid sort direction"}), 400

    requested_data = load_posts().get(BLOGPOSTS, [])

    if sort:
        reverse_order = (direction == "desc")

        if sort == DATE:
            requested_data = sorted(
                requested_data,
                key=lambda item: datetime.strptime(
                    item.get(DATE, "1970-01-01"), "%Y-%m-%d"
                ),
                reverse=reverse_order
            )
        elif sort in [TITLE, CONTENT, AUTHOR]:
            requested_data = sorted(
                requested_data,
                key=lambda item: item.get(sort, "").lower(),
                reverse=reverse_order
            )

    return jsonify(requested_data)


@app.route('/api/posts', methods=['POST'])
def post():
    """Validate, store, and return a newly created post."""
    request_data = request.get_json()

    if not isinstance(request_data, dict):
        return jsonify({"message": "Request body must be a JSON object"}), 400
    missing = [field for field in (TITLE, CONTENT) if field not in request_data]
    if missing:
        message = "Missing required fields: " + ", ".join(missing)
        return jsonify({"message": message}), 400

    validation_message = validate_post_fields(request_data)
    if validation_message:
        return jsonify({"message": validation_message}), 400

    file_data = load_posts()
    posts_list = file_data.get(BLOGPOSTS, [])

    highest_id = max((item[ID] for item in posts_list), default=0)

    new_post = {
        ID: highest_id + 1,
        TITLE: request_data[TITLE],
        CONTENT: request_data[CONTENT],
        AUTHOR: request_data.get(AUTHOR, "Unknown"),
        DATE: request_data.get(DATE, date.today().isoformat())
    }

    posts_list.append(new_post)
    file_data[BLOGPOSTS] = posts_list

    save_posts(file_data)

    return jsonify(new_post), 201


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """Delete the post with the requested ID."""
    file_data = load_posts()
    posts_list = file_data.get(BLOGPOSTS, [])

    post_found = False
    for item in posts_list:
        if item[ID] == post_id:
            posts_list.remove(item)
            post_found = True
            break

    if not post_found:
        return jsonify({"message": "Post not found"}), 404

    file_data[BLOGPOSTS] = posts_list
    save_posts(file_data)

    return jsonify({
        "message": f"Post with id {post_id} has been deleted successfully."
    }), 200


@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    """Update the supplied fields and return the updated post."""
    request_data = request.get_json()
    if not isinstance(request_data, dict):
        return jsonify({
            "message": "Request body must be a JSON object"
        }), 400

    file_data = load_posts()
    posts_list = file_data.get(BLOGPOSTS, [])

    target_item = next(
        (item for item in posts_list if item[ID] == post_id), None
    )

    if not target_item:
        return jsonify({"message": "Post not found"}), 404

    validation_message = validate_post_fields(request_data)
    if validation_message:
        return jsonify({"message": validation_message}), 400

    if TITLE in request_data:
        target_item[TITLE] = request_data[TITLE]
    if CONTENT in request_data:
        target_item[CONTENT] = request_data[CONTENT]
    if AUTHOR in request_data:
        target_item[AUTHOR] = request_data[AUTHOR]
    if DATE in request_data:
        target_item[DATE] = request_data[DATE]

    file_data[BLOGPOSTS] = posts_list
    save_posts(file_data)

    return jsonify(target_item), 200


@app.route('/api/posts/search', methods=['GET'])
def search_post():
    """Return posts matching any supplied search term."""
    target_title = request.args.get('title')
    target_content = request.args.get('content')
    target_author = request.args.get('author')
    target_date = request.args.get('date')
    general_search = request.args.get('search')
    normalized_search = general_search.lower() if general_search else ""

    result_items = []
    requested_data = load_posts().get(BLOGPOSTS, [])

    for item in requested_data:
        is_match = False

        if (
            target_title
            and target_title.lower() in str(item.get(TITLE, "")).lower()
        ):
            is_match = True
        if (
            target_content
            and target_content.lower() in str(item.get(CONTENT, "")).lower()
        ):
            is_match = True
        if (
            target_author
            and target_author.lower() in str(item.get(AUTHOR, "")).lower()
        ):
            is_match = True
        if target_date and target_date in str(item.get(DATE, "")):
            is_match = True

        if normalized_search:
            if (
                normalized_search in str(item.get(TITLE, "")).lower()
                or normalized_search in str(item.get(CONTENT, "")).lower()
                or normalized_search in str(item.get(AUTHOR, "")).lower()
                or normalized_search in str(item.get(DATE, "")).lower()
            ):
                is_match = True

        if is_match and item not in result_items:
            result_items.append(item)

    return jsonify(result_items), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
