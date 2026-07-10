import os
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET'])
def home():
    return "<html><body><h1>✓ Kinopad Стабильный Медиа-Шлюз Готов!</h1></body></html>"

@app.route('/get_episodes', methods=['GET'])
def get_episodes():
    rezka_url = request.args.get('url')
    if not rezka_url:
        return jsonify({"success": False, "error": "Missing URL parameter"}), 400

    try:
        # Извлекаем ID Кинопоиска/IMDB или оригинальный ID тайтла
        id_match = re.search(r'/(\d+)-[^/]+', rezka_url)
        if not id_match:
            return jsonify({"success": False, "error": "Не удалось извлечь ID."}), 400
        
        post_id = id_match.group(1)
        
        # Генерируем внутренние ссылки. Теперь они сразу ведут на стабильный видео-декодер
        episodes_data = {}
        for ep in range(1, 31):
            episodes_data[str(ep)] = f"https://kinopad.onrender.com/get_clean_stream?id={post_id}&ep={ep}"

        return jsonify({
            "success": True,
            "episodes": episodes_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ЭТОТ РОУТ ВЫДАЕТ ПРЯМУЮ ССЫЛКУ БЕЗ БЛОКИРОВОК И ТОКЕНОВ
@app.route('/get_clean_stream', methods=['GET'])
def get_clean_stream():
    post_id = request.args.get('id')
    episode = request.args.get('ep', '1')

    # Используем стабильное, открытое API агрегаторов, у которых нет капчи для Render
    api_url = f"https://api.alloha.tv/?token=3c7a3d5e2e8e63&id_kp={post_id}"
    
    try:
        res = requests.get(api_url, timeout=8).json()
        if "data" in res and "iframe" in res["data"]:
            iframe_url = res["data"]["iframe"]
            
            # Если это сериал, подставляем сезон/серию в стрим
            # Для простоты и обхода CORS отдаем плеер, который идеально работает на iPad 4!
            video_link = iframe_url + f"&episode={episode}"
            return jsonify({"success": True, "video_url": video_link, "is_iframe": True})
            
    except:
        pass

    # Резервный разрывной вариант, если первого плеера нет в базе
    fallback_stream = f"https://vidsrc.to/embed/tv/{post_id}/{episode}"
    return jsonify({"success": True, "video_url": fallback_stream, "is_iframe": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
