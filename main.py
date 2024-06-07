from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer
import pyotp
import qrcode
import io
import time
import logging
import urllib.parse
from fastapi.staticfiles import StaticFiles
from docxtpl import DocxTemplate
import pandas as pd
from pathlib import Path
from docx import Document
from docxcompose.composer import Composer
import os
import tempfile
from io import BytesIO
import numpy as np
from fdef import rupiah_strip, kalender_indo, bulan_indo

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"),name="static")
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace this with your actual secret key for session management
SESSION_SECRET = "DEDEGANTENGSECRETKEY"
serializer = URLSafeTimedSerializer(SESSION_SECRET)

templates = Jinja2Templates(directory="templates")

# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800

def create_session_token(username: str):
    session_data = {
        "username": username,
        "last_active": time.time()
    }
    return serializer.dumps(session_data)

def verify_session_token(token: str):
    try:
        session_data = serializer.loads(token, max_age=SESSION_TIMEOUT)
        return session_data
    except Exception as e:
        logger.error(f"Session verification failed: {e}")
        raise HTTPException(status_code=403, detail="Session expired or invalid")

def get_user_secret(username: str) -> str:
    sanitized_username = urllib.parse.quote(username, safe='')
    return f"{sanitized_username}DEDESAPUTRAGANTENG"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), otp_code: str = Form(...)):
    secret = get_user_secret(username)
    totp = pyotp.TOTP(secret)
    if not totp.verify(otp_code):
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid OTP code"})

    # Create a new session token
    session_token = create_session_token(username)
    response = RedirectResponse(url="/depan", status_code=302)
    response.set_cookie(key="session_token", value=session_token, httponly=True)
    return response

@app.get("/depan", response_class=HTMLResponse)
async def protected_route(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid OTP code"})

    session_data = verify_session_token(session_token)

    # Update the session's last active time
    new_session_token = create_session_token(session_data['username'])
    response = templates.TemplateResponse("shanum.html", {"request": request, "username": session_data['username']})
    response.set_cookie(key="session_token", value=new_session_token, httponly=True)
    return response

@app.get("/qrcode", response_class=HTMLResponse)
async def get_qrcode(request: Request, username: str):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=403, detail="Not authenticated")

    session_data = verify_session_token(session_token)

    # Update the session's last active time
    new_session_token = create_session_token(session_data['username'])
    secret = get_user_secret(username)
    totp = pyotp.TOTP(secret)
    otp_uri = totp.provisioning_uri(name=username, issuer_name="DedeApp")
    qr = qrcode.make(otp_uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# @app.post("/logout")
# async def logout(request: Request):
#     response = RedirectResponse(url="/", status_code=302)
#     response.delete_cookie("session_token")
#     return response
@app.route("/logout", methods=["GET", "POST"])
async def logout(request: Request):
    if request.method == "GET":
        response = RedirectResponse(url="/", status_code=302)
        response.delete_cookie("session_token")
        return response
    else:
        return HTTPException(status_code=405, detail="Method Not Allowed")


@app.get("/bikin-user", response_class=HTMLResponse)
async def protected_route(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=403, detail="Not authenticated")

    session_data = verify_session_token(session_token)

    # Update the session's last active time
    new_session_token = create_session_token(session_data['username'])
    response = templates.TemplateResponse("dedqrcode.html", {"request": request, "username": session_data['username']})
    response.set_cookie(key="session_token", value=new_session_token, httponly=True)
    return response

@app.get("/kuitansi", response_class=HTMLResponse)
async def protected_route(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return templates.TemplateResponse("notlogin.html", {"request": request})

    session_data = verify_session_token(session_token)

    # Update the session's last active time
    new_session_token = create_session_token(session_data['username'])
    response = templates.TemplateResponse("shanum.html", {"request": request, "username": session_data['username']})
    response.set_cookie(key="session_token", value=new_session_token, httponly=True)
    return response


@app.post("/generate-document")

async def generate_document(request: Request, file: UploadFile = File(...), category: str = Form(...),numberinput: int = Form(...),numberinput2: int = Form(...)):
    try:
        def extract_context_from_excel(file: UploadFile):
            content = file.file.read()
            file_like = BytesIO(content)
            if category == "kuitansi":
                sheet_name1 = "Lokal"
            elif category == "amplop":
                sheet_name1 = "Amplop"
            elif category == "nominatif":
                sheet_name1 = "Nominatif"
            else:
                raise HTTPException(status_code=400, detail="Invalid category")
            df = pd.read_excel(file_like, sheet_name=sheet_name1)
            return df.to_dict(orient="records")
# code baru        

        output_folder = "output"
        for filename in os.listdir(output_folder):
            file_path = os.path.join(output_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        context = extract_context_from_excel(file)
        jumlah_kui = numberinput
        kui_mulai = numberinput2 - 1
        context = context[kui_mulai:jumlah_kui]

        for item in context:
            # Determine the template based on the value in column D
            template_file = determine_template(item["template"])
            doc = DocxTemplate(template_file)
            doc.render(item)
            doc.save(f"output/{item['NAMA']}.docx")

        return templates.TemplateResponse("generate.html", {"request": request})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")

def determine_template(column_D_value):
    if column_D_value == "perjalanan dinas AMPLOP":
        return "template_docx/perjalanan dinas amplop.docx"
    elif column_D_value == "Bogor":
        return "bogor.docx"
    elif column_D_value == "perjalanan dinas":
        return "template_docx/perjadin.docx"
    else:
        raise HTTPException(status_code=400, detail="template")


@app.get("/merge-documents")
async def merge_documents():
    # List of file paths for input Word documents
    output_folder = "output"
    files2 = [os.path.join(output_folder, filename) for filename in os.listdir(output_folder) if filename.endswith(".docx")]

    # Check if any input files exist
    if not files2:
        raise HTTPException(status_code=404, detail="No input files found in the output folder")

    # Create a new in-memory buffer to hold the composed document
    composed_doc = io.BytesIO()

    # Create a new Document object to hold the composed content
    result = Document(files2[0])
    result.add_page_break()

    # Compose the content from the input documents
    composer = Composer(result)
    for i in range(1, len(files2)):
        doc2 = Document(files2[i])
        if i != len(files2) - 1:
            doc2.add_page_break()
        composer.append(doc2)

    # Save the composed document to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
        composer.save(temp_file.name)

        # Close the temporary file to ensure its content is flushed
        temp_file.close()

        # Provide the temporary file as a file response
        return FileResponse(temp_file.name, filename="kuitansi.docx", media_type="application/octet-stream")
@app.get("/work")
async def read_item(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return templates.TemplateResponse("notlogin.html", {"request": request, "error": "Invalid OTP code"})

    session_data = verify_session_token(session_token)

    # Update the session's last active time
    new_session_token = create_session_token(session_data['username'])
    response = templates.TemplateResponse("home.html", {"request": request, "username": session_data['username']})
    response.set_cookie(key="session_token", value=new_session_token, httponly=True)
    return response
# Coba dulu
@app.post("/generate-nominatif")

async def generate_nominatif(request: Request, file: UploadFile = File(...), category: str = Form(...), jumlahdata: int = Form(...)):
    jumlahdata = jumlahdata

    try:
        def extract_context_nominatif(file: UploadFile, category: str):
            content = file.file.read()
            file_like = BytesIO(content)
            if category == "kuitansi":
                sheet_name = "Nominatiff"
            elif category == "amplop":
                sheet_name = "Nominatiff"
            elif category == "nominatif":
                sheet_name = "Lokal"
            else:
                raise HTTPException(status_code=400, detail="Invalid category")
            df = pd.read_excel(file_like, sheet_name=sheet_name, nrows=jumlahdata)
            # df['harian'] = df['harian'].astype(int)
            mak = (df['MAK'][0])
            nama_keg = (df['nama_keg'][0])
            tgl_keg = (df['tgl_keg'][0])
            lok_keg = (df['lok_keg'][0])

            daftarNominatif = []
            for r_idx, r_val in df.iterrows():
                nama = r_val['NAMA']
                asal = r_val['ASAL']
                tujuan = r_val['TUJUAN']
                pesawat = r_val['PESAWAT']
                ta = r_val['TA']
                tt = r_val['TT']
                p = r_val['p']
                p_p = r_val['p_p']
                penginapan = r_val['PENGINAPAN']
                h = r_val['h']
                h_h = r_val['h_h']
                harian = r_val['HARIAN']
                total = r_val['TOTAL']
                # tgl_st = kalender_indo(r_val['tgl_st'])
                # tgl_tugas = kalender_indo(r_val['tgl_tugas'])
                # kali = r_val['kali']
                # harian = r_val['harian']
                # uang = rupiah_strip(r_val['uang'])
                daftarNominatif.append({"no": str(r_idx+1), "nama": nama, "asal": asal, "tujuan": tujuan, "pesawat": pesawat, "ta": ta, "tt": tt, "p": p, "l": "hr.", "p_p": p_p, "penginapan": penginapan, "h": h, "h_h": h_h, "harian": harian, "total":total})   

            return {'daftarNominatif': daftarNominatif, 'nama_keg': nama_keg, 'tgl_keg':tgl_keg, 'lok_keg':lok_keg, 'mak':mak}

        context = extract_context_nominatif(file, category)
        
        if category == "kuitansi":
            template = f"template_docx/nominatifkegiatan.docx"
        elif category == "amplop":
            template = f"template_docx/nominatifkegiatan.docx"
        elif category == "nominatif":
            template = f"template_docx/temtem.docx"
        else:
            raise HTTPException(status_code=400, detail="Invalid category")
        doctemp = template
        doc = DocxTemplate(doctemp)
        doc.render(context)
        nominatif_path = f"outputt/nominatif.docx"
        doc.save(nominatif_path)

        # Optionally, return a response with the path to the generated document
        return templates.TemplateResponse("downloadnominatif.html", {"request": request})

    except Exception as e:
        # Properly handle exceptions and return appropriate error responses
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nominatif")
async def read_item(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid OTP code"})

    session_data = verify_session_token(session_token)

    # Update the session's last active time
    new_session_token = create_session_token(session_data['username'])
    response = templates.TemplateResponse("nominatif.html", {"request": request, "username": session_data['username']})
    response.set_cookie(key="session_token", value=new_session_token, httponly=True)
    return response

@app.get("/download-nominatif")
async def download_nominatif():
    nominatif_path = "outputt/nominatif.docx"  # Ensure the correct path
    if os.path.exists(nominatif_path):
        return FileResponse(nominatif_path, media_type='application/octet-stream', filename="nominatif.docx")
    else:
        raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
