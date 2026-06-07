from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import openai
import os

app = Flask(__name__)
CORS(app)

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def get_openai_client():
    return openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_assemblyai_transcriber():
    import assemblyai as aai
    aai.settings.api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    config = aai.TranscriptionConfig(
        language_detection=True,
        punctuate=True,
        format_text=True
    )
    return aai.Transcriber(config=config)

@app.route('/api/transcribe', methods=['GET', 'POST', 'OPTIONS'])
def transcribe():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    try:
        data = request.get_json(force=True)
        url = data.get('url', '') if data else ''
        
        if not url:
            return jsonify({"success": False, "error": "مفيش رابط"})

        transcriber = get_assemblyai_transcriber()
        transcript = transcriber.transcribe(url)
        
        import assemblyai as aai
        if transcript.status == aai.TranscriptStatus.error:
            return jsonify({"success": False, "error": f"فشل التفريغ: {transcript.error}"})
        
        segments = []
        if transcript.words:
            words = transcript.words
            for i in range(0, len(words), 20):
                chunk = words[i:i+20]
                mins = int(chunk[0].start / 60000)
                secs = int((chunk[0].start % 60000) / 1000)
                text = ' '.join([w.text for w in chunk])
                segments.append({"t": f"{mins:02d}:{secs:02d}", "txt": text})
        else:
            segments = [{"t": "00:00", "txt": transcript.text}]
        
        return jsonify({"success": True, "segments": segments, "text": transcript.text})
            
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
        
        prompt = prompts.get(tool, f'حلل:\n{text[:3000]}')
        client = get_openai_client()
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
    key = os.environ.get("ASSEMBLYAI_API_KEY", "")
    return jsonify({
        "status": "ok",
        "assemblyai_key": "موجود ✅" if key else "مفقود ❌"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
