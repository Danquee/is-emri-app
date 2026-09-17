from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import sqlite3
import datetime
import random
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- AYARLAR ---
ADMIN_USERNAME = "GLC"
ADMIN_PASSWORD = "180289"  # Buradan şifrenizi değiştirebilirsiniz

# --- VERİTABANI KURULUMU ---
def get_db():
    conn = sqlite3.connect("is_emirleri.db")
    conn.row_factory = sqlite3.Row
    return conn

def db_kur():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS is_emirleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wo_no TEXT,
            tarih TEXT,
            saat TEXT,
            aciklama TEXT,
            durum TEXT,
            kapanis_tarih TEXT,
            kapanis_saat TEXT
        )
    """)
    conn.commit()
    conn.close()

db_kur()

# --- GİRİŞ KONTROL DEKORATÖRÜ ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Lütfen önce giriş yapın.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTALAR ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash("Başarıyla giriş yapıldı.", "success")
            return redirect(url_for('index'))
        else:
            flash("Hatalı kullanıcı adı veya şifre!", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("Oturum kapatıldı.", "info")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    filtre = request.args.get('filtre', 'Tarihe Göre (En Yeni Üstte)')
    
    sql_query = "SELECT * FROM is_emirleri"
    
    if filtre == "Tarihe Göre (En Yeni Üstte)":
        sql_query += " ORDER BY id DESC"
    elif filtre == "Tarihe Göre (En Eski Üstte)":
        sql_query += " ORDER BY id ASC"
    elif filtre == "Önce Açık Olanlar (Açıklar Üstte)":
        sql_query += " ORDER BY CASE WHEN durum='AÇIK' THEN 0 ELSE 1 END, id DESC"
    elif filtre == "Önce Kapalı Olanlar (Kapalılar Üstte)":
        sql_query += " ORDER BY CASE WHEN durum='KAPATILDI' THEN 0 ELSE 1 END, id DESC"
    elif filtre == "Sadece Açık İş Emirleri":
        sql_query += " WHERE durum='AÇIK' ORDER BY id DESC"
    elif filtre == "Sadece Kapalı İş Emirleri":
        sql_query += " WHERE durum='KAPATILDI' ORDER BY id DESC"
    else:
        sql_query += " ORDER BY id DESC"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    is_emirleri = cursor.fetchall()
    conn.close()

    return render_template('index.html', is_emirleri=is_emirleri, secili_filtre=filtre)

@app.route('/ekle', methods=['POST'])
@login_required
def ekle():
    aciklama = request.form.get('aciklama', '').strip()
    if not aciklama:
        flash("Açıklama boş bırakılamaz!", "warning")
        return redirect(url_for('index'))

    simdi = datetime.datetime.now()
    tarih_str = simdi.strftime("%d.%m.%Y")
    saat_str = simdi.strftime("%H:%M:%S")
    wo_no = f"WO-{simdi.strftime('%Y%m%d')}-{random.randint(100, 999)}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO is_emirleri (wo_no, tarih, saat, aciklama, durum, kapanis_tarih, kapanis_saat)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (wo_no, tarih_str, saat_str, aciklama, "AÇIK", "", ""))
    conn.commit()
    conn.close()

    flash(f"{wo_no} numaralı iş emri başarıyla oluşturuldu.", "success")
    return redirect(url_for('index'))

@app.route('/kapat/<int:id>')
@login_required
def kapat(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT durum, wo_no FROM is_emirleri WHERE id=?", (id,))
    rec = cursor.fetchone()

    if not rec:
        flash("İş emri bulunamadı!", "danger")
        conn.close()
        return redirect(url_for('index'))

    if rec['durum'] == "KAPATILDI":
        flash("Bu iş emri zaten kapatılmış!", "warning")
        conn.close()
        return redirect(url_for('index'))

    simdi = datetime.datetime.now()
    k_tarih = simdi.strftime("%d.%m.%Y")
    k_saat = simdi.strftime("%H:%M:%S")

    cursor.execute("UPDATE is_emirleri SET durum='KAPATILDI', kapanis_tarih=?, kapanis_saat=? WHERE id=?",
                   (k_tarih, k_saat, id))
    conn.commit()
    conn.close()

    flash(f"{rec['wo_no']} numaralı iş emri başarıyla kapatıldı.", "success")
    return redirect(url_for('index'))

@app.route('/sil/<int:id>')
@login_required
def sil(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM is_emirleri WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("İş emri başarıyla silindi.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
