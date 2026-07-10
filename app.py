import os
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Разрешаем CORS, чтобы GitHub Pages мог свободно общаться с Render
CORS(app, resources={r"/*": {"origins": "*"}})

def fix_url(url):
    if url and url.startswith("http://"):
        return url.replace("http://", "https://", 1)
    return url

@app.route('/', methods=['GET'])
def home():
    return "<html><body><h1>✓ Kinopad Мощный Прокси-API работает!</h1></body></html>"

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
        
        episodes_data = {}

        # Формируем ссылки на НАШ сервер, передавая домен из оригинальной ссылки пользователя
        # Если ты вставил rezka-tv.org, прокси будет использовать именно его (зеркала реже банят дата-центры)
        domain_match = re.search(r'https?://[^/]+', rezka_url)
        domain = domain_match.group(0) if domain_match else "https://hdrezka.me"

        for ep in range(1, 31):
            episodes_data[str(ep)] = f"https://kinopad.onrender.com/proxy_video?id={post_id}&season={season}&episode={ep}&translator_id={translator_id}&domain={domain}"

        return jsonify({
            "success": True,
            "season": season,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка обработки: {str(e)}"}), 500

# ЭТОТ РОУТ ЗАБИРАЕТ ДАННЫЕ БЕЗ CORS И ОБРАБАТЫВАЕТ ОШИБКИ БЕЗ ПАДЕНИЯ В 500
@app.route('/proxy_video', methods=['GET'])
def proxy_video():
    post_id = request.args.get('id')
    season = request.args.get('season')
    episode = request.args.get('episode')
    translator_id = request.args.get('translator_id', '1')
    target_domain = request.args.get('domain', 'https://hdrezka.me')

    url = f"{target_domain}/engine/ajax/get_cdn_series.php"
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
        "Origin": target_domain,
        "Referer": target_domain + "/"
    }

    try:
        # Читаем как текст, чтобы не падать, если Резка вернет не JSON
        response = requests.post(url, data=data, headers=headers, timeout=12)
        text_data = response.text

        # Ищем mp4/m3u8 ссылки прямо в сыром тексте ответа регуляркой
        urls = re.findall(r'https?://[^\s,\s"]+(?:\.mp4|\.m3u8)[^\s"]*', text_data)
        if urls:
            final_video_url = urls[-1].split(' or ')[0].replace('\\', '').strip()
            return jsonify({"success": True, "video_url": fix_url(final_video_url)})
        
        return jsonify({"success": False, "error": "Видео не найдено в ответе. Возможно, зеркало заблокировано."}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
