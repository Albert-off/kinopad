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
    return "<html><body><h1>✓ Kinopad Умный Прокси-API работает!</h1></body></html>"

@app.route('/get_episodes', methods=['GET'])
def get_episodes():
    rezka_url = request.args.get('url')
    requested_season = request.args.get('season', '1')

    if not rezka_url:
        return jsonify({"success": False, "error": "Missing URL parameter"}), 400

    try:
        # 1. Извлекаем ID поста и озвучки из твоей ссылки
        id_match = re.search(r'/(\d+)-[^/]+', rezka_url)
        if not id_match:
            return jsonify({"success": False, "error": "Не удалось извлечь ID из ссылки."}), 400
        
        post_id = id_match.group(1)

        translator_match = re.search(r'-latest/(\d+)-', rezka_url)
        translator_id = translator_match.group(1) if translator_match else "1"

        season_match = re.search(r'/(\d+)-season', rezka_url)
        season = season_match.group(1) if season_match else requested_season
        
        episodes_data = {}

        # 2. Внимание! Ссылки для кнопок теперь ведут на НАШ сервер Render (/get_video_link)
        for ep in range(1, 31):
            episodes_data[str(ep)] = f"https://kinopad.onrender.com/get_video_link?id={post_id}&season={season}&episode={ep}&translator_id={translator_id}"

        return jsonify({
            "success": True,
            "type": "series",
            "season": season,
            "translator_id": translator_id,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка обработки: {str(e)}"}), 500

# 3. ЭТОТ РОУТ ОБЯЗАТЕЛЕН! Он вытягивает реальный mp4, когда ты жмешь на кнопку серии
@app.route('/get_video_link', methods=['GET'])
def get_video_link():
    post_id = request.args.get('id')
    season = request.args.get('season')
    episode = request.args.get('episode')
    translator_id = request.args.get('translator_id', '1')

    # Имитируем правильный POST-запрос, который требует Резка
    url = "https://hdrezka.me/engine/ajax/get_cdn_series.php"
    data = {
        "id": post_id,
        "season": season,
        "episode": episode,
        "translator_id": translator_id,
        "action": "get_stream"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://hdrezka.me",
        "Referer": "https://hdrezka.me/"
    }

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        res_json = response.json()

        if res_json.get("success") and "url" in res_json:
            streams_str = res_json["url"]
            
            # Парсим все ссылки на видеопотоки из ответа
            urls = re.findall(r'https?://[^\s,\s]+(?:\.mp4|\.m3u8)[^\s]*', streams_str)
            if urls:
                # Берем видео-ссылку (обычно в конце лучшее качество)
                final_video_url = urls[-1].split(' or ')[0].strip()
                return jsonify({"success": True, "video_url": fix_url(final_video_url)})
        
        return jsonify({"success": False, "error": "Не удалось получить видео-поток от донора"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
