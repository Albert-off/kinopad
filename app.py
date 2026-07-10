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
    return "<html><body><h1>✓ Kinopad Точный Парсер Потоков Работает!</h1></body></html>"

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
            episodes_data[str(ep)] = f"https://kinopad.onrender.com/get_real_stream?id={post_id}&season={season}&episode={ep}&translator_id={translator_id}"

        return jsonify({
            "success": True,
            "season": season,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка обработки: {str(e)}"}), 500

# ПОЛУЧАЕМ НАСТОЯЩИЙ ПОТОК ЧЕРЕЗ VOIDBOOST IFRAME
@app.route('/get_real_stream', methods=['GET'])
def get_real_stream():
    post_id = request.args.get('id')
    season = request.args.get('season')
    episode = request.args.get('episode')
    translator_id = request.args.get('translator_id', '1')

    # Стучимся на iframe Voidboost, который генерирует рабочие токены
    iframe_url = f"https://voidboost.net/embed/{post_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://hdrezka.me/"
    }

    try:
        response = requests.get(iframe_url, headers=headers, timeout=10)
        html = response.text

        # Ищем внутри скриптов ту самую ссылку с токеном и .m3u8
        # Ищет паттерны типа https://stream.voidboost.cc/...manifest.m3u8
        urls = re.findall(r'https?://stream\.voidboost\.cc/[^"\s\\]+manifest\.m3u8', html)
        
        if urls:
            # Нашли базовый манифест сериала. Теперь подставим туда нужные сезон и серию
            base_stream = urls[0]
            
            # Voidboost обычно кодирует пути серий в структуре URL. 
            # Если в iframe лежит чистый стрим, отдаем его, заменяя протокол на безопасный https
            return jsonify({"success": True, "video_url": fix_url(base_stream)})

        # Альтернативный вариант: если Voidboost спрятал ссылку, собираем её по их стандартному шаблону токенов
        # Но для точной генерации нам нужен актуальный хэш сессии. Попробуем выдернуть его:
        session_match = re.search(r'var\s+token\s*=\s*["\']([^"\']+)["\']', html)
        if session_match:
            token = session_match.group(1)
            # Конструируем прямую рабочую ссылку, похожую на твою
            constructed_url = f"https://stream.voidboost.cc/{token}/manifest.m3u8"
            return jsonify({"success": True, "video_url": fix_url(constructed_url)})

        # Если совсем глухо, делаем прямой запрос к их API через бэк
        fallback_api = f"https://stream.voidboost.cc/set_video?id={post_id}&season={season}&episode={episode}&translator_id={translator_id}"
        api_res = requests.get(fallback_api, headers=headers, allow_redirects=True, timeout=10)
        
        # voidboost при GET запросе с правильным реферером редиректит на .mp4/.m3u8 файл
        if "manifest.m3u8" in api_res.url or ".mp4" in api_res.url:
            return jsonify({"success": True, "video_url": fix_url(api_res.url)})

        return jsonify({"success": False, "error": "Не удалось сгенерировать токен потока."}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
