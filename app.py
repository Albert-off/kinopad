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
    return "<html><body><h1>✓ Kinopad Парсер Нового Поколения Работает!</h1></body></html>"

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
            # Передаем саму ссылку на главную страницу сериала, чтобы распарсить её код напрямую!
            episodes_data[str(ep)] = f"https://kinopad.onrender.com/get_stream_via_page?id={post_id}&season={season}&episode={ep}&translator_id={translator_id}&orig_url={encodeURIComponent(rezka_url)}"

        return jsonify({
            "success": True,
            "season": season,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка обработки: {str(e)}"}), 500

# ВСЯ МАГИЯ ТУТ: Парсим главную страницу вместо AJAX-скрипта
@app.route('/get_stream_via_page', methods=['GET'])
def get_stream_via_page():
    post_id = request.args.get('id')
    season = request.args.get('season')
    episode = request.args.get('episode')
    translator_id = request.args.get('translator_id', '1')
    orig_url = request.args.get('orig_url')

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3"
    }

    try:
        # 1. Запрашиваем обычную страницу сериала
        page_response = requests.get(orig_url, headers=headers, timeout=10)
        html_text = page_response.text

        # 2. Ищем код инициализации плеера sofia (он отдает потоки)
        # Сначала попробуем вытащить прямые ссылки, которые часто лежат в кэше страницы
        urls = re.findall(r'https?://[^\s,\s"\\ movie]+(?:\.mp4|\.m3u8)[^\s"\\ movie]*', html_text)
        
        # 3. Если на странице нашлись видео-потоки, отдаем их
        if urls:
            final_url = urls[-1].split(' or ')[0].replace('\\', '').strip()
            return jsonify({"success": True, "video_url": fix_url(final_url)})

        # 4. Если напрямую не нашлось, делаем обходной маневр на мобильный cdn
        fallback_url = f"https://stream.voidboost.cc/set_video?id={post_id}&season={season}&episode={episode}&translator_id={translator_id}"
        return jsonify({"success": True, "video_url": fallback_url})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def encodeURIComponent(str):
    import urllib.parse
    return urllib.parse.quote(str, safe='~()*!\'')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
