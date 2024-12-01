import os
import wave
from flask import Flask, request, jsonify
import audioop
import speech_recognition as sr

app = Flask(__name__)

# 控制是否删除临时文件
REMOVE_TEMP_FILES = True

# 函数：将 WAV 文件转换为 16kHz 单声道 PCM
def convert_wav_to_16khz_pcm_mono(input_wav, output_wav):
    try:
        with wave.open(input_wav, 'rb') as src:
            # 获取音频参数
            n_channels = src.getnchannels()
            samp_width = src.getsampwidth()
            samp_rate = src.getframerate()
            n_frames = src.getnframes()

            # 读取音频数据
            audio_data = src.readframes(n_frames)

            # 转换为单声道
            if n_channels > 1:
                audio_data = audioop.tomono(audio_data, samp_width, 1, 1)

            # 转换为 16kHz 采样率
            if samp_rate != 16000:
                audio_data, _ = audioop.ratecv(audio_data, samp_width, 1, samp_rate, 16000, None)

            # 写入输出文件
            with wave.open(output_wav, 'wb') as dst:
                dst.setnchannels(1)
                dst.setsampwidth(samp_width)
                dst.setframerate(16000)
                dst.writeframes(audio_data)
        return True
    except Exception as e:
        print(f"Error during audio conversion: {e}")
        return False

# 函数：语音转文字
def speech_to_text(wav_file):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_file) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "Google Speech Recognition could not understand your audio"
    except sr.RequestError as e:
        return f"Could not request results from Google Speech Recognition service; {e}"

# Flask 路由：处理音频并返回识别文本
@app.route('/api/speech_to_text', methods=['POST'])
def post_speech_to_text():
    if 'wav_data' not in request.json:
        return jsonify({"error": "Missing 'wav_data' in request"}), 400

    try:
        # 读取 Base64 编码的音频数据
        wav_data = request.json['wav_data']
        temp_input_file = "temp.wav"
        temp_output_file = "temp_output.wav"

        # 保存临时文件
        with open(temp_input_file, "wb") as f:
            import base64
            f.write(base64.b64decode(wav_data))

        # 转换音频文件格式
        if not convert_wav_to_16khz_pcm_mono(temp_input_file, temp_output_file):
            return jsonify({"error": "Audio conversion failed"}), 500

        # 识别音频并返回文本
        text = speech_to_text(temp_output_file)
        # 删除临时文件（根据配置）
        if REMOVE_TEMP_FILES:
            os.remove(temp_input_file)
            os.remove(temp_output_file)

        return jsonify({"text": text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 启动 Flask 服务
    app.run(debug=True, host='127.0.0.1', port=5000)
