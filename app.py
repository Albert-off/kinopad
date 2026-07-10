import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from HdRezkaApi import HdRezkaApi

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def fix_url(url):
    if url and url.startswith("http://"):
        return url.replace("http://", "https://", 1)
    return url

@app.route('/', methods=['GET'])
def home():
    return """
    <html>
        <head><title>Kinopad API</title><style>body{font-family:sans-serif;text-align:center;padding-top:100px;background-color:#f4f4f9;color:#333;}.container{background:white;padding:30px;border-radius:10px;display:inline-block;box-shadow:0 4px 6px rgba(0,0,0,0.1);}h1{color:#2ecc71;margin-bottom:10px;}p{color:#7f8c8d;}</style></head>
        <body><div class="container"><h1>✓ Kinopad API Работает!</h1><p>Ваш личный сервер-прослойка для iPad 4 успешно запущен.</p></div></body>
    </html>
    """

@app.route('/get_episodes', methods=['GET'])
def get_episodes():
    rezka_url = request.args.get('url')
    season = request.args.get('season', '1')

    if not rezka_url:
        return jsonify({"success": False, "error": "Missing URL parameter"}), 400

    # Очищаем URL и принудительно переводим на стандартный домен, который лучше всего жует библиотека
    # Заменяем зеркала типа rezka-tv.org на hdrezka.me внутри парсера
    if "rezka" in rezka_url:
        rezka_url = re.sub(r'https?://[^/]+', 'https://hdrezka.me', rezka_url)

    try:
        rezka = HdRezkaApi(rezka_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
        })
        
        # Проверяем, сериал это или одиночный фильм/аниме-фильм
        # Если у объекта нет списка эпизодов, то это фильм
        try:
            streams = rezka.getStream(season)
            has_episodes = hasattr(streams, 'episodes') and streams.episodes
        except Exception:
            has_episodes = False

        episodes_data = {}

        if has_episodes:
            # Логика для сериалов / многосерийных аниме
            for episode in streams.episodes:
                try:
                    url = None
                    for quality in ['1080p', '720p', '480p', '360p']:
                        try:
                            url = streams(episode)(quality)
                            if url: break
                        except Exception:
                            continue
                    if not url:
                        url = streams(episode)()
                    
                    if url:
                        episodes_data[str(episode)] = fix_url(url)
                except Exception:
                    continue
        else:
            # Логика для одиночных фильмов
            try:
                url = None
                for quality in ['1080p', '720p', '480p', '360p']:
                    try:
                        url = rezka.getStream()(quality)
                        if url: break
                    except Exception:
                        continue
                if not url:
                    url = rezka.getStream()()
                
                if url:
                    episodes_data["1"] = fix_url(url) # Фильм отдаем как "1 серия"
            except Exception as movie_err:
                return jsonify({"success": False, "error": f"Не удалось получить поток фильма: {str(movie_err)}"}), 404

        if not episodes_data:
            return jsonify({"success": False, "error": "Видео-потоки не найдены или заблокированы донором."}), 404

        return jsonify({
            "success": True,
            "type": "series" if has_episodes else "movie",
            "season": season,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка парсера: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
