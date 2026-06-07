from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os

app = Flask(__name__)

# السماح لكل الدومينات
CORS(app, resources={r"/*": {"origins": "*"}})

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

@app.route('/api/transcribe', methods=['POST', 'OPTIONS'])
def transcribe():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        url = data.get('url', '')
        text = f"تم استلام الطلب بنجاح! الرابط: {url}\n\nهذا نص تجريبي - سيتم ربط OpenAI Whisper قريباً لتفريغ الفيديو الحقيقي."
        return jsonify({"success": True, "text": text})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/summarize', methods=['POST', 'OPTIONS'])
def summarize():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        text = data.get('text', '')
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"لخص النص ده في 5 نقاط:\n{text[:2000]}"}]
        )
        return jsonify({"success": True, "result": response.choices[0].message.content})
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
            'summary': f'لخص النص ده في 5 نقاط مهمة:\n{text[:2000]}',
            'article': f'اكتب مقال SEO من النص ده:\n{text[:2000]}',
            'mcq': f'اعمل 10 أسئلة MCQ من النص ده مع الإجابات:\n{text[:2000]}',
            'translate': f'ترجم النص ده للإنجليزي:\n{text[:2000]}',
            'clean': f'نظف ورتب النص ده:\n{text[:2000]}',
            'keywords': f'استخرج أهم 10 كلمات مفتاحية من النص ده:\n{text[:2000]}',
            'social': f'اكتب بوستات سوشيال ميديا من النص ده:\n{text[:2000]}',
            'qa': f'اعمل 5 أسئلة وأجوبة من النص ده:\n{text[:2000]}',
        }
        
        prompt = prompts.get(tool, f'حلل النص ده:\n{text[:2000]}')
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
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
