import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET'])
def home():
    return "<html><body><h1>✓ Kinopad Генератор серий готов!</h1></body></html>"

@app.route('/get_episodes', methods=['GET'])
def get_episodes():
    rezka_url = request.args.get('url')
    requested_season = request.args.get('season', '1')

    if not rezka_url:
        return jsonify({"success": False, "error": "Missing URL parameter"}), 400

    try:
        id_match = re.search(r'/(\d+)-[^/]+', rezka_url)
        if not id_match:
            return jsonify({"success": False, "error": "Не удалось извлечь ID из ссылки."}), 400
        
        post_id = id_match.group(1)

        translator_match = re.search(r'-latest/(\d+)-', rezka_url)
        translator_id = translator_match.group(1) if translator_match else "1"

        season_match = re.search(r'/(\d+)-season', rezka_url)
        season = season_match.group(1) if season_match else requested_season
        
        domain_match = re.search(r'https?://[^/]+', rezka_url)
        domain = domain_match.group(0) if domain_match else "https://hdrezka.me"

        episodes_data = {}
        for ep in range(1, 31):
            episodes_data[str(ep)] = {
                "id": post_id,
                "season": season,
                "episode": str(ep),
                "translator_id": translator_id,
                "domain": domain
            }

        return jsonify({
            "success": True,
            "season": season,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка обработки: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
