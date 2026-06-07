from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import openai
import os
import requests

app = Flask(__name__)
CORS(app)

def get_env(key):
    for k, v in os.environ.items():
        if k.strip() == key.strip():
            return v.strip()
    return ""

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/api/transcribe', methods=['GET', 'POST', 'OPTIONS'])
def transcribe():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    try:
        RAPIDAPI_KEY = get_env("RAPIDAPI_KEY")
        if not RAPIDAPI_KEY:
            return jsonify({"success": False, "error": "RAPIDAPI_KEY مفقود"})

        data = request.get_json(force=True)
        url = data.get('url', '') if data else ''
        if not url:
            return jsonify({"success": False, "error": "مفيش رابط"})

        # استخدام RapidAPI
        api_url = "https://youtube-transcripts-transcribe-youtube-video-to-text.p.rapidapi.com/youtube/transcribe"
        
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "youtube-transcripts-transcribe-youtube-video-to-text.p.rapidapi.com"
        }
        
        params = {"url": url, "chunkSize": "5"}
        
        response = requests.get(api_url, headers=headers, params=params, timeout=60)
        result = response.json()
        
        if response.status_code != 200:
            return jsonify({"success": False, "error": f"فشل API: {result}"})
        
        # تحويل النتيجة
        segments = []
        full_text = ""
        
        if 'content' in result:
            for item in result['content']:
                offset = item.get('offset', 0)
                mins = int(offset // 60)
                secs = int(offset % 60)
                text = item.get('text', '')
                segments.append({"t": f"{mins:02d}:{secs:02d}", "txt": text})
                full_text += text + " "
        elif 'text' in result:
            segments = [{"t": "00:00", "txt": result['text']}]
            full_text = result['text']
        else:
            return jsonify({"success": False, "error": f"نتيجة غير متوقعة: {result}"})
        
        return jsonify({
            "success": True,
            "segments": segments,
            "text": full_text.strip()
        })
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/<tool>', methods=['GET', 'POST', 'OPTIONS'])
def handle_tool(tool):
    if request.method == 'OPTIONS':
        return make_response('', 200)
    try:
        data = request.get_json(force=True)
        text = data.get('text', '') if data else ''
        
        prompts = {
            'summary': f'لخص في 5 نقاط:\n{text[:3000]}',
            'article': f'اكتب مقال SEO:\n{text[:3000]}',
            'mcq': f'اعمل 10 أسئلة MCQ:\n{text[:3000]}',
            'translate': f'ترجم للإنجليزي:\n{text[:3000]}',
            'clean': f'نظف النص:\n{text[:3000]}',
            'keywords': f'استخرج 10 كلمات مفتاحية:\n{text[:3000]}',
            'social': f'اكتب 3 بوستات سوشيال:\n{text[:3000]}',
            'qa': f'اعمل 5 أسئلة وأجوبة:\n{text[:3000]}',
            'mindmap': f'اعمل خريطة ذهنية:\n{text[:3000]}',
            'ppt': f'اعمل مخطط PPT:\n{text[:3000]}',
            'podcast': f'اكتب سكريبت بودكاست:\n{text[:3000]}',
            'cert': f'اكتب شهادة إتمام:\n{text[:3000]}',
            'srt': f'حول لـ SRT:\n{text[:3000]}',
            'template': f'اعمل قالب:\n{text[:3000]}',
            'compare': f'قارن المحتوى:\n{text[:3000]}',
        }
        
        OPENAI_KEY = get_env("OPENAI_API_KEY")
        client = openai.OpenAI(api_key=OPENAI_KEY)
        prompt = prompts.get(tool, f'حلل:\n{text[:3000]}')
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500
        )
        return jsonify({"success": True, "result": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/health')
def health():
    rapidapi = get_env("RAPIDAPI_KEY")
    return jsonify({
        "status": "ok",
        "rapidapi_key": "موجود ✅" if rapidapi else "مفقود ❌"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
