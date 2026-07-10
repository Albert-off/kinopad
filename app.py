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

    # Заголовки, чтобы притвориться настоящим настольным браузером
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://rezka.ag/",
        "Cache-Control": "max-age=0"
    }

    try:
        # Шаг 1. Качаем страницу напрямую через requests со всеми маскировками
        session = requests.Session()
        response = session.get(rezka_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return jsonify({"success": False, "error": f"Резка вернула статус {response.status_code}. Возможно, включена защита."}), 403
            
        html = response.text

        # Шаг 2. Ищем ID фильма/сериала на странице с помощью регулярных выражений
        # Обычно на Резке это лежит в коде инициализации плеера: sof.tv.initCDNMoviesEvents(ID, ...)
        id_match = re.search(r'initCDNMoviesEvents\(\s*(\d+)', html)
        if not id_match:
            # Альтернативный поиск ID в других местах страницы
            id_match = re.search(r'data-id="(\d+)"', html)
            if not id_match:
                id_match = re.search(r'id="post_id"\s+value="(\d+)"', html)

        if not id_match:
            return jsonify({"success": False, "error": "Не удалось определить ID контента на странице. Защита Cloudflare заблокировала парсинг."}), 404

        post_id = id_match.group(1)

        # Шаг 3. Ищем скрытые ссылки CDN или плеера внутри HTML-кода
        # Ищем куски кодированных строк плеера (обычно начинаются на #H or #U)
        cdn_streams = re.findall(r'"(https?:\\?/\\?/[^"]+\.mp4[^"]*)"', html)
        
        episodes_data = {}
        
        # Проверяем, есть ли готовые прямые mp4/m3u8 стримы в коде
        if cdn_streams:
            for i, stream in enumerate(cdn_streams[:30], 1):
                clean_url = stream.replace('\\/', '/')
                episodes_data[str(i)] = fix_url(clean_url)
        
        # Если прямых ссылок нет, попробуем собрать универсальный манифест плеера Резки
        if not episodes_data:
            # Для Дандадана и сериалов выдергиваем конфигурацию серий из скрытых скриптов страницы
            # Если это сериал, на странице есть список серий в блоках data-episode_id
            episodes_matches = re.findall(r'data-episode_id="(\d+)"[^>]*>([^<]+)', html)
            
            if episodes_matches:
                # Если нашли серии в верстке, формируем ссылки для них через их плеер-интерфейс
                for ep_id, ep_name in episodes_matches:
                    ep_num = re.sub(r'\D', '', ep_name) # оставляем только цифру серии
                    if not ep_num:
                        ep_num = ep_id
                    # Генерируем ссылку, которую поймет плеер (через перенаправление)
                    episodes_data[str(ep_num)] = fix_url(f"https://hdrezka.me/engine/ajax/get_cdn_series.php?id={post_id}&season={season}&episode={ep_num}")
            else:
                # Если это фильм, отдаем одну универсальную ссылку
                episodes_data["1"] = fix_url(f"https://hdrezka.me/engine/ajax/get_cdn_series.php?id={post_id}&action=get_movie")

        # Если совсем ничего не нашлось, отдаем ошибку парсинга структуры
        if not episodes_data or len(episodes_data) == 0:
            return jsonify({"success": False, "error": "Потоки видео не обнаружены. Попробуйте обновить ссылку донора."}), 404

        return jsonify({
            "success": True,
            "type": "series" if "season" in html or episodes_matches else "movie",
            "season": season,
            "episodes": episodes_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Критическая ошибка сервера: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
