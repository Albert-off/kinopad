import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from HdRezkaApi import HdRezkaApi

app = Flask(__name__)
# Полное разрешение CORS для связи с вашим GitHub Pages
CORS(app, resources={r"/*": {"origins": "*"}})

def fix_url(url):
    """Принудительно переводит ссылки на https, чтобы старый Safari на iPad не блокировал контент"""
    if url and url.startswith("http://"):
        return url.replace("http://", "https://", 1)
    return url

@app.route('/get_episodes', methods=['GET'])
def get_episodes():
    rezka_url = request.args.get('url')
    season = request.args.get('season', '1')

    if not rezka_url:
        return jsonify({"success": False, "error": "Missing URL parameter"}), 400

    try:
        # Инициализируем парсер.
        # ВНИМАНИЕ: Если Rezka выдает ошибку Anubis, в поле 'url' в браузере на ПК вставляй актуальное рабочее зеркало!
        rezka = HdRezkaApi(rezka_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        # Получаем стрим для выбранного сезона
        streams = rezka.getStream(season)

        episodes_data = {}
        for episode in streams.episodes:
            try:
                # Жесткий приоритет на максимальное качество: 1080p -> 720p -> всё остальное
                try:
                    url = streams(episode)('1080p')
                except Exception:
                    try:
                        url = streams(episode)('720p')
                    except Exception:
                        url = streams(episode)()

                # Сохраняем исправленную безопасную ссылку
                if url:
                    episodes_data[str(episode)] = fix_url(url)

            except Exception:
                continue

        if not episodes_data:
            return jsonify({"success": False, "error": "Серии не найдены. Возможно, это фильм, а не сериал."}), 404

        return jsonify({
            "success": True,
            "season": season,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Обязательная настройка для нормальных хостингов (Render, Railway и др.)
    # Программа будет брать порт, который ей выделит сервер
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
