from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import openai
import os
import tempfile
import subprocess
import re

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def download_audio(url, output_dir):
    cmd = [
        'yt-dlp',
        '-x',
        '--audio-format', 'mp3',
        '--audio-quality', '128K',
        '-o', os.path.join(output_dir, 'audio.%(ext)s'),
        '--no-playlist',
        '--quiet',
        url
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    for f in os.listdir(output_dir):
        if f.startswith('audio'):
            return os.path.join(output_dir, f)
    return None

@app.route('/api/transcribe', methods=['GET', 'POST', 'OPTIONS'])
def transcribe():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    try:
        data = request.get_json(force=True)
        url = data.get('url', '') if data else ''
        if not url:
            return jsonify({"success": False, "error": "مفيش رابط"})

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_file = download_audio(url, tmpdir)
            if not audio_file:
                return jsonify({"success": False, "error": "فشل تنزيل الصوت - تأكد من الرابط"})
            
            with open(audio_file, 'rb') as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json"
                )
            
            segments = []
            if hasattr(transcript, 'segments') and transcript.segments:
                for seg in transcript.segments:
                    mins = int(seg.start // 60)
                    secs = int(seg.start % 60)
                    segments.append({
                        "t": f"{mins:02d}:{secs:02d}",
                        "txt": seg.text.strip()
                    })
            else:
                segments = [{"t": "00:00", "txt": transcript.text}]
            
            return jsonify({
                "success": True,
                "segments": segments,
                "text": transcript.text
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
            'summary': f'لخص النص ده في 5 نقاط مهمة:\n{text[:3000]}',
            'article': f'اكتب مقال SEO احترافي من النص ده:\n{text[:3000]}',
            'mcq': f'اعمل 10 أسئلة MCQ من النص ده مع 4 خيارات والإجابة:\n{text[:3000]}',
            'translate': f'ترجم النص ده للإنجليزي:\n{text[:3000]}',
            'clean': f'نظف ورتب النص ده:\n{text[:3000]}',
            'keywords': f'استخرج أهم 10 كلمات مفتاحية:\n{text[:3000]}',
            'social': f'اكتب 3 بوستات سوشيال:\n{text[:3000]}',
            'qa': f'اعمل 5 أسئلة وأجوبة:\n{text[:3000]}',
            'mindmap': f'اعمل خريطة ذهنية:\n{text[:3000]}',
            'ppt': f'اعمل مخطط PPT:\n{text[:3000]}',
            'podcast': f'اكتب سكريبت بودكاست:\n{text[:3000]}',
            'cert': f'اكتب شهادة إتمام:\n{text[:3000]}',
            'srt': f'حول النص لـ SRT:\n{text[:3000]}',
            'template': f'اعمل قالب:\n{text[:3000]}',
            'compare': f'قارن المحتوى:\n{text[:3000]}',
        }
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
    return jsonify({"status": "ok", "message": "VideoScript API شغال!"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
