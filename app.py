# app.py
import os
from datetime import datetime
import cv2
import json
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify

app = Flask(__name__)

HISTORY_DIR = "static/thumbs"
os.makedirs(HISTORY_DIR, exist_ok=True)
SAVE_DIR = "static/tmp_img"
os.makedirs(SAVE_DIR, exist_ok=True)

frame_count = 0
saved_count = 0
streaming_enabled = False

def capture_frame():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if ret:
        cv2.imwrite("static/frame.jpg", frame)
        cartoon = cv2.stylization(frame, sigma_s=150, sigma_r=0.25)
        cv2.imwrite("static/cartoon.jpg", cartoon)

        # 保存するサムネイルを履歴として追加
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thumb_path = os.path.join(HISTORY_DIR, f"thumb_{timestamp}.jpg")
        thumbnail = cv2.resize(frame, (80, 60))
        cv2.imwrite(thumb_path, thumbnail)

        # 古い履歴を削除（15枚制限）
        thumbs = sorted(os.listdir(HISTORY_DIR))
        while len(thumbs) > 15:
            os.remove(os.path.join(HISTORY_DIR, thumbs.pop(0)))

def generate_camera_stream():
    global streaming_enabled  # ここを忘れずに！

    cap = cv2.VideoCapture(0)
    frame_count = 0
    saved_count = len(os.listdir(SAVE_DIR))

    while streaming_enabled:
        ret, frame = cap.read()
        if not ret:
            break

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        # 10フレームごとに保存
        if frame_count % 10 == 0 and saved_count < 15:
            save_path = os.path.join(SAVE_DIR, f"{saved_count}.png")
            cv2.imwrite(save_path, frame)
            saved_count += 1

        # ★ ここでチェック：15枚揃ったらストリーミングを自動停止
        if saved_count >= 15:
            streaming_enabled = False
            break

        frame_count += 1

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()


@app.route("/")
def index():
    capture_frame()
    thumbs = sorted(os.listdir(HISTORY_DIR), reverse=True)
    return render_template("index.html", thumbs=thumbs)

@app.route("/start", methods=["POST"])
def start():
    global streaming_enabled
    global frame_count
    global saved_count

    # ストリーミング有効化
    streaming_enabled = True

    # 保存カウントをリセット
    frame_count = 0
    saved_count = 0

    # 保存フォルダ(static/tmp_img)をリセット
    for filename in os.listdir(SAVE_DIR):
        file_path = os.path.join(SAVE_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

    return redirect(url_for("index"))


@app.route("/stop", methods=["POST"])
def stop():
    global streaming_enabled
    streaming_enabled = False
    return redirect(url_for("index"))


@app.route("/end", methods=["POST"])
def end():
    # 処理終了のロジック（必要に応じて）
    return redirect(url_for("index"))

@app.route('/video_feed')
def video_feed():
    if not streaming_enabled:
        return Response(b"", mimetype='multipart/x-mixed-replace; boundary=frame')
    return Response(generate_camera_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/history_images')
def history_images():
    images = sorted(os.listdir(SAVE_DIR), key=lambda x: int(x.split('.')[0]))
    return jsonify(images)

@app.route('/streaming_status')
def streaming_status():
    return jsonify({"enabled": streaming_enabled})

# 新規ページ追加
@app.route("/select")
def select():
    return render_template("select.html")

@app.route("/processing")
def processing():
    return render_template("processing.html")

@app.route("/signature")
def signature():
    return render_template("signature.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

if __name__ == "__main__":
    app.run(debug=True)
