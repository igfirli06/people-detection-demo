from flask import Flask, render_template, Response, jsonify
import cv2
import numpy as np
import pyparsing as pp
import random
import time
from datetime import datetime

app = Flask(__name__)

# ==========================================
# 1. FORTIGATE LOG PARSER ENGINE
# ==========================================
class FortiParser(object):
    def __init__(self):
        priority = pp.Combine(pp.Suppress('<') + pp.Word(pp.nums) + pp.Suppress('>'))
        SEPERATOR = pp.Word("!#$%&'()*+,-./:;<=>?@[\]^_`{|}~")
        objName = pp.Combine(pp.Word(pp.alphanums) + pp.ZeroOrMore(SEPERATOR + pp.Word(pp.alphanums)))
        value = (pp.quotedString | objName)
        assgn = pp.Combine(pp.Word(pp.alphas) + "=" + value)
        self.logLine = priority("pri") + pp.OneOrMore(assgn)("fields")

    def parseMsg(self, line):
        result_dict = {}
        try:
            obj = self.logLine.parseString(line)
            for field in obj.fields:
                kv = field.split('=')
                result_dict[kv[0]] = kv[1]
        except pp.ParseException as err:
            result_dict['err'] = err.line
        finally:
            return result_dict

parser = FortiParser()

# ==========================================
# 2. CCTV DUMMY GENERATOR (Simulasi YOLO)
# ==========================================
def generate_cctv_frames():
    # Membuat kanvas video dummy berukuran 640x480
    x, y = 100, 240
    direction = 5
    
    while True:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Gambar Zona Berbahaya (Merah)
        zone_pts = np.array([[400, 100], [600, 100], [600, 400], [400, 400]], np.int32)
        cv2.polylines(frame, [zone_pts], isClosed=True, color=(0, 0, 255), thickness=3)
        cv2.putText(frame, "RESTRICTED ZONE", (410, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Simulasi Pergerakan Pekerja (Kotak Hijau)
        x += direction
        if x > 600 or x < 50:
            direction *= -1
            
        cv2.rectangle(frame, (x, y), (x+50, y+100), (0, 255, 0), 2)
        cv2.putText(frame, "ID:12 [Person]", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Logika Deteksi: Jika Pekerja masuk zona merah
        if x > 350:
            cv2.putText(frame, "ALERT: PERSON IN ZONE!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            cv2.rectangle(frame, (x, y), (x+50, y+100), (0, 0, 255), 3) # Berubah merah
            
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.1) # Simulasi 10 FPS

# ==========================================
# 3. ROUTES APLIKASI
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/people')
def people():
    return render_template('people.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_cctv_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/fortigate')
def fortigate():
    return render_template('fortigate.html')

@app.route('/api/generate-log')
def generate_log():
    # Menghasilkan dummy log mirip syslog Fortigate
    ips = ["192.168.1.10", "10.0.0.5", "172.16.2.14"]
    actions = ["accept", "deny", "timeout"]
    now = datetime.now()
    
    raw_log = f"<14>date={now.strftime('%Y-%m-%d')} time={now.strftime('%H:%M:%S')} devname=KTI-FW01 devid=FGT12345 srcip={random.choice(ips)} dstip=8.8.8.8 action={random.choice(actions)} policyid=1"
    
    parsed_data = parser.parseMsg(raw_log)
    
    return jsonify({
        "raw": raw_log,
        "parsed": parsed_data
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')