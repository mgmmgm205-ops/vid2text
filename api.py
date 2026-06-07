from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import tempfile
import subprocess
import sys

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def download_audio(url, output_path):
    cmd = [
        'yt-dlp',
        '-x',
        '--audio-format', 'mp3',
        '--audio-quality', '128K',
        '-o', output_path,
        '--no-playlist',
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

@app.route('/api/transcribe', methods=['POST', 'OPTIONS'])
def transcribe():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        url = data.get('url', '')
        
        if not url:
            return jsonify({"success": False, "error": "مفيش رابط"})

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, 'audio.%(ext)s')
            
            success = download_audio(url, audio_path)
            
            # إيجاد الملف الصوتي
            audio_file = None
            for f in os.listdir(tmpdir):
                if f.startswith('audio'):
                    audio_file = os.path.join(tmpdir, f)
                    break
            
            if not audio_file or not os.path.exists(audio_file):
                return jsonify({"success": False, "error": "فشل تنزيل الصوت - تأكد من الرابط"})
            
            # تفريغ بـ OpenAI Whisper
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

@app.route('/api/<tool>', methods=['POST', 'OPTIONS'])
def handle_tool(tool):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        text = data.get('text', '')
        
        prompts = {
            'summary': f'لخص النص ده في 5 نقاط مهمة:\n{text[:3000]}',
            'article': f'اكتب مقال SEO احترافي من النص ده:\n{text[:3000]}',
            'mcq': f'اعمل 10 أسئلة MCQ من النص ده مع 4 خيارات والإجابة:\n{text[:3000]}',
            'translate': f'ترجم النص ده للإنجليزي:\n{text[:3000]}',
            'clean': f'نظف ورتب النص ده:\n{text[:3000]}',
            'keywords': f'استخرج أهم 10 كلمات مفتاحية من النص ده:\n{text[:3000]}',
            'social': f'اكتب 3 بوستات سوشيال من النص ده:\n{text[:3000]}',
            'qa': f'اعمل 5 أسئلة وأجوبة من النص ده:\n{text[:3000]}',
            'mindmap': f'اعمل خريطة ذهنية من النص ده:\n{text[:3000]}',
            'cert': f'اكتب نص شهادة إتمام من النص ده:\n{text[:3000]}',
            'ppt': f'اعمل مخطط PowerPoint من النص ده:\n{text[:3000]}',
            'compare': f'حلل وقارن المحتوى ده:\n{text[:3000]}',
            'srt': f'حول النص ده لصيغة SRT:\n{text[:3000]}',
            'template': f'اعمل قالب احترافي من النص ده:\n{text[:3000]}',
            'podcast': f'اكتب سكريبت بودكاست من النص ده:\n{text[:3000]}',
        }
        
        prompt = prompts.get(tool, f'حلل النص ده:\n{text[:3000]}')
        
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
