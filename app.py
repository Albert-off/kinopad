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
    return "<html><body><h1>✓ Kinopad Финальный API Работает!</h1></body></html>"

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
            # Ссылки снова ведут на наш сервер, который сделает правильный POST без CORS-проблем
            episodes_data[str(ep)] = f"https://kinopad.onrender.com/get_stream_direct?id={post_id}&season={season}&episode={ep}&translator_id={translator_id}&domain={domain}"

        return jsonify({
            "success": True,
            "season": season,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка обработки: {str(e)}"}), 500

# ЭТОТ РОУТ ДЕЛАЕТ ЧИСТЫЙ POST ЗАПРОС СИМУЛИРУЯ МОБИЛЬНЫЙ БРАУЗЕР
@app.route('/get_stream_direct', methods=['GET'])
def get_stream_direct():
    post_id = request.args.get('id')
    season = request.args.get('season')
    episode = request.args.get('episode')
    translator_id = request.args.get('translator_id', '1')
    domain = request.args.get('domain', 'https://hdrezka.me')

    url = f"{domain}/engine/ajax/get_cdn_series.php"
    
    data = {
        "id": post_id,
        "season": season,
        "episode": episode,
        "translator_id": translator_id,
        "action": "get_stream"
    }

    # Маскируемся под официальное мобильное приложение, для которого Cloudflare всегда отключен!
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": domain,
        "Referer": domain + "/"
    }

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        text_data = response.text

        # Ищем mp4/m3u8 ссылки внутри ответа (даже если там кастомный JSON или текст)
        urls = re.findall(r'https?://[^\s,\s"\\ movie]+(?:\.mp4|\.m3u8)[^\s"\\ movie]*', text_data)
        if urls:
            # Берём ссылку с максимальным качеством (обычно последняя)
            final_url = urls[-1].split(' or ')[0].replace('\\', '').strip()
            return jsonify({"success": True, "video_url": fix_url(final_url)})

        return jsonify({"success": False, "error": "Поток не найден. Попробуйте обновить ссылку донора."}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
