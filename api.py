from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import openai
import os
import requests
import re

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def get_video_id(url):
    patterns = [
        r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be/([0-9A-Za-z_-]{11})',
        r'shorts/([0-9A-Za-z_-]{11})'
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def get_youtube_captions(video_id):
    # جلب الترجمة من YouTube API
    url = f"https://www.googleapis.com/youtube/v3/captions?part=snippet&videoId={video_id}&key={YOUTUBE_API_KEY}"
    res = requests.get(url)
    data = res.json()
    
    if 'items' not in data or not data['items']:
        return None
    
    # اختار أول ترجمة متاحة
    caption_id = data['items'][0]['id']
    
    # جلب محتوى الترجمة
    caption_url = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}?key={YOUTUBE_API_KEY}&tfmt=srt"
    caption_res = requests.get(caption_url)
    
    return caption_res.text if caption_res.status_code == 200 else None

def parse_srt(srt_text):
    segments = []
    blocks = srt_text.strip().split('\n\n')
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            text = ' '.join(lines[2:])
            start = time_line.split(' --> ')[0]
            parts = start.replace(',', ':').split(':')
            mins = int(parts[1])
            secs = int(parts[2])
            segments.append({
                "t": f"{mins:02d}:{secs:02d}",
                "txt": text.strip()
            })
    return segments

def get_video_info(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}"
    res = requests.get(url)
    data = res.json()
    if 'items' in data and data['items']:
        return data['items'][0]['snippet']
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

        video_id = get_video_id(url)
        if not video_id:
            return jsonify({"success": False, "error": "رابط يوتيوب غير صحيح"})

        # جرب جلب الترجمة
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ar'])
            except:
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                except:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            segments = []
            full_text = ""
            for item in transcript_list:
                mins = int(item['start'] // 60)
                secs = int(item['start'] % 60)
                segments.append({
                    "t": f"{mins:02d}:{secs:02d}",
                    "txt": item['text'].strip()
                })
                full_text += item['text'] + " "
            
            return jsonify({
                "success": True,
                "segments": segments,
                "text": full_text.strip()
            })
            
        except Exception as e:
            # لو مفيش ترجمة
            video_info = get_video_info(video_id)
            title = video_info['title'] if video_info else url
            
            return jsonify({
                "success": False,
                "error": f"الفيديو '{title}' مش عنده ترجمة تلقائية. جرب فيديو تاني أو ارفع ملف صوتي مباشرة."
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
