import os
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def fix_url(url):
    if url and url.startswith("http://"):
        return url.replace("http://", "https://", 1)
    return url

@app.route('/', methods=['GET'])
def home():
    return "<html><body><h1>✓ Kinopad Сверхзвуковой API работает без парсинга!</h1></body></html>"

@app.route('/get_episodes', methods=['GET'])
def get_episodes():
    rezka_url = request.args.get('url')
    requested_season = request.args.get('season', '1')

    if not rezka_url:
        return jsonify({"success": False, "error": "Missing URL parameter"}), 400

    try:
        # Извлекаем ID поста (например, 74222 или 80675)
        id_match = re.search(r'/(\d+)-[^/]+', rezka_url)
        if not id_match:
            return jsonify({"success": False, "error": "Не удалось извлечь ID из ссылки. Убедитесь, что ссылка содержит ID (например, /74222-dandadan...)"}), 400
        
        post_id = id_match.group(1)

        # Пытаемся вытащить ID озвучки (например, 105 для StudioBand)
        translator_match = re.search(r'-latest/(\d+)-', rezka_url)
        translator_id = translator_match.group(1) if translator_match else "1" # 1 - оригинал / дефолт

        # Пытаемся вытащить сезон и серию из ссылки, если они там есть
        season_match = re.search(r'/(\d+)-season', rezka_url)
        episode_match = re.search(r'/(\d+)-episode', rezka_url)

        season = season_match.group(1) if season_match else requested_season
        
        episodes_data = {}

        # Проверяем, сериал это или фильм (в ссылках на серии всегда есть слово season или episode)
        if "season" in rezka_url or "episode" in rezka_url or int(post_id) > 0:
            # Так как мы не можем скачать список серий из-за Cloudflare, 
            # мы генерируем прямые AJAX-ссылки для плеера на 30 серий вперед!
            # Твой HTML плеер сможет запустить любую из них.
            for ep in range(1, 31):
                episodes_data[str(ep)] = fix_url(
                    f"https://hdrezka.me/engine/ajax/get_cdn_series.php?id={post_id}&season={season}&episode={ep}&translator_id={translator_id}&action=get_stream"
                )
            is_series = True
        else:
            # Если это чистый фильм
            episodes_data["1"] = fix_url(
                f"https://hdrezka.me/engine/ajax/get_cdn_series.php?id={post_id}&translator_id={translator_id}&action=get_movie"
            )
            is_series = False

        return jsonify({
            "success": True,
            "type": "series" if is_series else "movie",
            "season": season,
            "translator_id": translator_id,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка обработки ссылки: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
