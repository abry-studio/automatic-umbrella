"""
================================================================================
[뽀삐 현장 스마트 통합 파이프라인 웹 서버] (pipeline_server.py)
================================================================================
FastAPI 기반 고성능 실시간 웹 애플리케이션:
  - 사진/도면(이미지) 업로드 -> Windows Media OCR 정밀 텍스트 추출 -> 자동 분류
  - 엑셀 업로드 -> 헤더 동적 매핑 -> 자동 분류
  - 데이터 성격별 시트1/시트2/시트3~9 특정 행/열 자동 꽂아넣기
  - 구글 시트 / 엑셀 스타일의 탭 기반 인터랙티브 스프레드시트 뷰어
  - .xlsm 실시간 저장 및 엑셀 직접 열기 연동
"""

import os
import sys
import io
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re
import datetime
from PIL import Image, ImageDraw, ImageFont

from data_pipeline_engine import DataPipelineEngine

# 기본 경로
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
WEB_DIR = BASE_DIR / "web"
WEB_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="뽀삐 현장 스마트 데이터 파이프라인", version="1.0.0")

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 파이프라인 엔진 인스턴스
engine = DataPipelineEngine(BASE_DIR)


# Pydantic 모델
class CellEditRequest(BaseModel):
    sheet: str
    row: int
    col: int
    value: str

class ManualRouteRequest(BaseModel):
    dong: str
    unit: str
    trade: str
    status: str
    description: Optional[str] = ""
    date: Optional[str] = ""
    note: Optional[str] = ""


# ------------------------------------------------------------------------------
# 1. 정적 파일 및 메인 UI 라우트
# ------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html 파일을 찾을 수 없습니다.")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/style.css")
async def get_css():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")

@app.get("/app.js")
async def get_js():
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")


# ------------------------------------------------------------------------------
# 2. 시트 데이터 API
# ------------------------------------------------------------------------------
@app.get("/api/sheets")
async def get_all_sheets():
    """모든 시트 이름과 요약 정보 반환"""
    sheet_summaries = []
    for sname in engine.sheet_names:
        data = engine.sheets_data.get(sname, [])
        sheet_summaries.append({
            "name": sname,
            "rowCount": len(data),
            "colCount": max(len(r) for r in data) if data else 0
        })
    return {
        "sheets": sheet_summaries,
        "activeSheet": engine.sheet_names[0] if engine.sheet_names else "",
        "macroFile": engine.xlsm_path.name,
        "lastLog": engine.last_pipeline_log
    }

@app.get("/api/sheet/{sheet_name}")
async def get_sheet_detail(sheet_name: str):
    """특정 시트의 모든 셀 2차원 데이터 반환"""
    if sheet_name not in engine.sheets_data:
        raise HTTPException(status_code=404, detail="시트를 찾을 수 없습니다.")
    rows = engine.sheets_data[sheet_name]
    max_c = max(len(r) for r in rows) if rows else 0
    return {
        "sheet": sheet_name,
        "rows": rows,
        "rowCount": len(rows),
        "colCount": max_c
    }

@app.get("/api/dashboard-data")
async def get_dashboard_data():
    """실제 엑셀 워크북(827세대 및 동별 현황) 기반 실시간 통계 및 실속 작업 목록 반환"""
    return engine.get_dashboard_summary()


# ------------------------------------------------------------------------------
# 3. 파일 유입 및 파이프라인 가동 API (사진 또는 엑셀)
# ------------------------------------------------------------------------------
@app.post("/api/upload")
async def upload_and_process(file: UploadFile = File(...)):
    """업로드된 사진(이미지) 또는 엑셀 파일을 분석하여 시트별 셀/행으로 자동 꽂아넣기"""
    filename = file.filename.lower()
    content = await file.read()
    
    records = []
    source_type = "알 수 없음"

    # 이미지 파일 판별
    if any(filename.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]):
        source_type = "시공 사진 / 점검표 (OCR 분석)"
        records = await engine.extract_from_image(content, filename=file.filename)

    # 엑셀/CSV 파일 판별
    elif any(filename.endswith(ext) for ext in [".xlsx", ".xlsm", ".xls", ".csv"]):
        source_type = "외부 엑셀 대장 (스마트 매핑)"
        records = engine.extract_from_excel(content, filename)
    else:
        raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식입니다. (이미지 또는 엑셀 파일만 지원)")

    if not records:
        raise HTTPException(status_code=422, detail="파일에서 시공 데이터를 추출하지 못했습니다.")

    # 핵심 파이프라인 자동 배치 실행!
    pipeline_results = engine.execute_pipeline(records)

    return {
        "success": True,
        "sourceType": source_type,
        "filename": file.filename,
        "recordCount": len(records),
        "extractedRecords": records,
        "pipelineResults": pipeline_results,
        "dashboard": engine.get_dashboard_summary()
    }


# ------------------------------------------------------------------------------
# 4. 빠른 원클릭 샘플 테스트 API (공종별 전용 시트 분기 테스트)
# ------------------------------------------------------------------------------
@app.post("/api/sample/jojuk")
async def process_sample_jojuk():
    """[조적] 시공 사진 생성 및 OCR 분석 ➔ [조적] 시트 자동 배치 테스트"""
    img = Image.new("RGB", (650, 320), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_path = "C:/Windows/Fonts/malgun.ttf"
    try:
        font_title = ImageFont.truetype(font_path, 22)
        font_body = ImageFont.truetype(font_path, 18)
    except:
        font_title = font_body = ImageFont.load_default()

    draw.rectangle([10, 10, 640, 310], outline=(180, 80, 20), width=3)
    draw.rectangle([10, 10, 640, 55], fill=(180, 80, 20))
    draw.text((25, 20), "■ [현장 시공 점검표] 조적 공정 감리 검측서", fill=(255, 255, 255), font=font_title)

    draw.text((30, 80), "▶ 세대 정보: 102동 1001호 (10F)", fill=(0, 0, 0), font=font_body)
    draw.text((30, 120), "▶ 시공 공종: 조적 (주방 및 발코니 벽체 벽돌 쌓기)", fill=(0, 0, 0), font=font_body)
    draw.text((30, 160), "▶ 시공 상태: 완료 (검측통과 - 수직수평 정상)", fill=(0, 120, 0), font=font_body)
    draw.text((30, 200), "▶ 작업 부위: 주방 벽체 공간쌓기 및 단열재 충진 완료", fill=(50, 50, 50), font=font_body)
    draw.text((30, 240), "▶ 작업 일자: 2026-09-25 (책임시공: 박반장)", fill=(80, 80, 80), font=font_body)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    records = await engine.extract_from_image(buf.getvalue())
    pipeline_results = engine.execute_pipeline(records, custom_sheet_target="조적")

    return {
        "success": True,
        "sourceType": "현장 조적 시공 사진 (내용 분석 ➔ [조적] 시트 자동 꽂기)",
        "detectedTrade": "조적",
        "targetSheet": "조적",
        "recordCount": len(records),
        "extractedRecords": records,
        "pipelineResults": pipeline_results,
        "dashboard": engine.get_dashboard_summary()
    }

@app.post("/api/sample/mijang")
async def process_sample_mijang():
    """[미장] 시공 사진 생성 및 OCR 분석 ➔ [미장] 시트 자동 배치 테스트"""
    img = Image.new("RGB", (650, 320), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_path = "C:/Windows/Fonts/malgun.ttf"
    try:
        font_title = ImageFont.truetype(font_path, 22)
        font_body = ImageFont.truetype(font_path, 18)
    except:
        font_title = font_body = ImageFont.load_default()

    draw.rectangle([10, 10, 640, 310], outline=(40, 120, 180), width=3)
    draw.rectangle([10, 10, 640, 55], fill=(40, 120, 180))
    draw.text((25, 20), "■ [현장 시공 점검표] 미장 공정 일일 작업일지", fill=(255, 255, 255), font=font_title)

    draw.text((30, 80), "▶ 세대 정보: 103동 2101호 (21F)", fill=(0, 0, 0), font=font_body)
    draw.text((30, 120), "▶ 시공 공종: 미장 (세대 거실 벽체 견출 및 정벌)", fill=(0, 0, 0), font=font_body)
    draw.text((30, 160), "▶ 시공 상태: 완료 (감리 확인 합격)", fill=(0, 120, 0), font=font_body)
    draw.text((30, 200), "▶ 작업 부위: 안방 및 거실 벽면 초벌/정벌 미장 완료", fill=(50, 50, 50), font=font_body)
    draw.text((30, 240), "▶ 작업 일자: 2026-09-25 (책임시공: 이반장)", fill=(80, 80, 80), font=font_body)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    records = await engine.extract_from_image(buf.getvalue())
    pipeline_results = engine.execute_pipeline(records, custom_sheet_target="미장")

    return {
        "success": True,
        "sourceType": "현장 미장 시공 사진 (내용 분석 ➔ [미장] 시트 자동 꽂기)",
        "detectedTrade": "미장",
        "targetSheet": "미장",
        "recordCount": len(records),
        "extractedRecords": records,
        "pipelineResults": pipeline_results,
        "dashboard": engine.get_dashboard_summary()
    }

@app.post("/api/sample/sachum")
async def process_sample_sachum():
    """[문틀사춤] 시공 사진 생성 및 OCR 분석 ➔ [문틀사춤] 시트 자동 배치 테스트"""
    img = Image.new("RGB", (650, 320), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_path = "C:/Windows/Fonts/malgun.ttf"
    try:
        font_title = ImageFont.truetype(font_path, 22)
        font_body = ImageFont.truetype(font_path, 18)
    except:
        font_title = font_body = ImageFont.load_default()

    draw.rectangle([10, 10, 640, 310], outline=(50, 50, 120), width=3)
    draw.rectangle([10, 10, 640, 55], fill=(50, 50, 120))
    draw.text((25, 20), "■ [현장 시공 점검표] 문틀사춤 공정 검측표", fill=(255, 255, 255), font=font_title)

    draw.text((30, 80), "▶ 세대 정보: 101동 1501호 (15F)", fill=(0, 0, 0), font=font_body)
    draw.text((30, 120), "▶ 시공 공종: 문틀사춤 (세대 방화문 및 실내문틀)", fill=(0, 0, 0), font=font_body)
    draw.text((30, 160), "▶ 시공 상태: 완료 (시공 품질 적합)", fill=(0, 120, 0), font=font_body)
    draw.text((30, 200), "▶ 작업 부위: 현관 및 거실 문틀 사춤 몰탈 밀실 충진", fill=(50, 50, 50), font=font_body)
    draw.text((30, 240), "▶ 작업 일자: 2026-09-25 (책임시공: 최반장)", fill=(80, 80, 80), font=font_body)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    records = await engine.extract_from_image(buf.getvalue())
    pipeline_results = engine.execute_pipeline(records, custom_sheet_target="문틀사춤")

    return {
        "success": True,
        "sourceType": "현장 문틀사춤 시공 사진 (내용 분석 ➔ [문틀사춤] 시트 자동 꽂기)",
        "detectedTrade": "문틀사춤",
        "targetSheet": "문틀사춤",
        "recordCount": len(records),
        "extractedRecords": records,
        "pipelineResults": pipeline_results,
        "dashboard": engine.get_dashboard_summary()
    }


# ------------------------------------------------------------------------------
# 5. 사장님 수기 직접 입력 API (동·호수, 공종, 부위, 메모 즉시 엑셀 연동)
# ------------------------------------------------------------------------------
@app.post("/api/manual-entry")
async def add_manual_entry(payload: ManualRouteRequest):
    """사장님이 수기로 직접 적은 공정 일지를 엑셀 대장 및 동별 시트에 즉시 꽂아넣기"""
    dong_val = payload.dong.strip()
    if not dong_val.endswith("동"):
        dong_val += "동"
    unit_val = payload.unit.strip()
    if unit_val and not unit_val.endswith("호") and unit_val[-1].isdigit():
        unit_val += "호"

    floor_num = "".join([c for c in unit_val if c.isdigit()])
    floor_val = f"{floor_num[:-2]}F" if len(floor_num) >= 3 else "01F"
    if floor_val == "F": floor_val = "01F"

    record = {
        "dong": dong_val,
        "floor": floor_val,
        "unit": unit_val,
        "trade": payload.trade,
        "status": payload.status,
        "description": payload.description or f"{dong_val} {unit_val} {payload.trade} {payload.status}",
        "date": payload.date or datetime.date.today().strftime("%Y-%m-%d"),
        "note": payload.note or "현장 수기 관리 등록"
    }

    results = engine.execute_pipeline([record])
    engine.save_to_xlsm()

    return {
        "success": True,
        "message": f"[{dong_val} {unit_val}] {payload.trade} 수기 등록이 완료되었습니다.",
        "record": record,
        "results": results,
        "dashboard": engine.get_dashboard_summary()
    }


# ------------------------------------------------------------------------------
# 6. 셀 직접 수정 (인터랙티브 파이프라인 연동)
# ------------------------------------------------------------------------------
@app.post("/api/cell/edit")
async def edit_cell(payload: CellEditRequest):
    """화면에서 직접 셀 값을 바꿀 때 파이프라인 즉각 반응 (F열 '완료' 시 자동 이동 등)"""
    res = engine.update_cell_and_trigger_pipeline(
        payload.sheet, payload.row, payload.col, payload.value
    )
    return res


# ------------------------------------------------------------------------------
# 6. .xlsm 저장 및 엑셀 실행 API
# ------------------------------------------------------------------------------
@app.post("/api/save-xlsm")
async def save_xlsm_file(payload: Optional[Dict[str, Any]] = None):
    """대시보드의 작업 목록을 각 시트에 동기화한 후 원본 .xlsm에 안전하게 영구 저장"""
    if payload and "workLogs" in payload:
        logs = payload["workLogs"]
        records = []
        for item in logs:
            loc = item.get("location", "102동 1001호")
            d_match = re.search(r"(10[1-7])", loc)
            dong_val = f"{d_match.group(1)}동" if d_match else "102동"
            u_match = re.search(r"(\d{3,4})", loc)
            unit_val = f"{u_match.group(1)}호" if u_match else "1001호"
            
            records.append({
                "dong": dong_val,
                "floor": item.get("floor", "10F"),
                "unit": unit_val,
                "trade": item.get("trade", "조적"),
                "status": item.get("status", "완료"),
                "description": item.get("desc", ""),
                "date": item.get("date", datetime.date.today().strftime("%Y-%m-%d")),
                "note": item.get("note", "대시보드 실시간 동기화")
            })
        if records:
            engine.execute_pipeline(records)

    success = engine.save_to_xlsm()
    return {
        "success": success,
        "filePath": str(engine.xlsm_path),
        "message": "통합_현장관리및공정관리대장.xlsm 에 성공적으로 저장되었습니다." if success else "저장 실패"
    }

@app.post("/api/open-excel")
async def open_excel_interactively():
    """바탕화면의 엑셀 파일을 사용자 화면에 즉시 열기"""
    try:
        # 안전한 실행: Windows Shell execute
        os.startfile(str(engine.xlsm_path.resolve()))
        return {"success": True, "message": f"엑셀 파일이 열렸습니다: {engine.xlsm_path.name}"}
    except Exception as e:
        return {"success": False, "message": f"엑셀 실행 실패: {e}"}

@app.post("/api/reset")
async def reset_system_data():
    """안전 자동 백업 후 대시보드 및 메모리 데이터 깨끗이 초기화"""
    import shutil
    try:
        if engine.xlsm_path.exists():
            backup_dir = BASE_DIR / "결과_출력" / "백업"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"통합_현장관리및공정관리대장_초기화직전백업_{ts}.xlsm"
            shutil.copy2(engine.xlsm_path, backup_file)
            print(f"[*] 초기화 전 자동 백업 보존: {backup_file.name}")

        engine.load_from_workbook()
        return {
            "success": True, 
            "message": "안전 백업 완료 후 데이터가 깨끗하게 초기화되었습니다.",
            "dashboard": engine.get_dashboard_summary()
        }
    except Exception as e:
        return {"success": False, "message": f"초기화 중 오류: {e}"}


# ------------------------------------------------------------------------------
# 메인 엔트리포인트
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print(" [뽀삐] 현장 스마트 데이터 파이프라인 & 시트 뷰어 서버 시작")
    print(" 접속 주소: http://localhost:8500")
    print("=" * 70)
    uvicorn.run(app, host="127.0.0.1", port=8500)
