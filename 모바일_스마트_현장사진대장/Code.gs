/**
 * ================================================================================
 * [뽀삐] 스마트 현장사진대장 - 구글 앱스 스크립트 (Code.gs)
 * ================================================================================
 * 기능:
 *  1. doGet: 모바일 웹앱 HTML 인터페이스 서비스 제공
 *  2. doPost: 모바일에서 전송된 워터마크 사진을 구글 드라이브 폴더에 영구 보관
 *  3. 구글 시트 [진행및대기현황] / [완료목록] / [현장사진대장]에 자동 행 삽입
 *  4. 뽀삐 현장 대시보드(도마변동9 현장)와 100% 컬럼 구조 완벽 호환
 */

// 드라이브 폴더 및 시트 설정 상수
const DRIVE_FOLDER_NAME = "[뽀삐] 스마트 현장사진대장 보관함";
const TARGET_SHEET_NAME = "현장사진대장"; // 메인 사진 대장 시트

/**
 * 1. 모바일 웹앱 진입점 (GET)
 */
function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('🐕 뽀삐 스마트 현장사진대장')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * 2. 모바일 웹앱 데이터 수신 및 구글 드라이브/시트 자동 저장 (POST)
 */
function doPost(e) {
  try {
    const postData = JSON.parse(e.postData.contents);
    const result = processPhotoRecord(postData);
    
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      message: "성공적으로 구글 시트와 드라이브에 저장되었습니다.",
      fileUrl: result.fileUrl,
      rowNumber: result.rowNumber
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    Logger.log("doPost Error: " + error.toString());
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * 사진 저장 및 시트 기록 핵심 로직
 */
function processPhotoRecord(data) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // 1. 구글 드라이브 사진 저장
  const folder = getOrCreateFolder(DRIVE_FOLDER_NAME);
  
  // Base64 디코딩
  const base64Data = data.imageBase64.split(',')[1];
  const decodedBlob = Utilities.newBlob(
    Utilities.base64Decode(base64Data), 
    'image/jpeg'
  );

  // 체계적인 파일명 생성: YYYYMMDD_HHMMSS_[동호수]_[공종]_[상태].jpg
  const now = new Date();
  const ts = Utilities.formatDate(now, "Asia/Seoul", "yyyyMMdd_HHmmss");
  const dateFormatted = Utilities.formatDate(now, "Asia/Seoul", "yyyy-MM-dd");
  const fileName = `${ts}_${cleanStr(data.dong)}_${cleanStr(data.unit)}_${cleanStr(data.trade)}_${cleanStr(data.status)}.jpg`;
  decodedBlob.setName(fileName);

  // 드라이브에 저장 및 공개 링크 생성
  const file = folder.createFile(decodedBlob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  const fileUrl = file.getUrl();
  const fileId = file.getId();
  const thumbFormula = `=IMAGE("https://drive.google.com/thumbnail?id=${fileId}&sz=w400")`;

  // 2. 구글 시트 기록 준비
  const dong = data.dong || "101동";
  const floor = data.floor || "01F";
  const unit = data.unit || "101호";
  const detailLoc = data.detailLocation || `${dong} ${unit}`;
  const trade = data.trade || "미지정";
  const status = data.status || "완료";
  const desc = data.description || "-";
  const gps = data.gps || "-";

  // 메인 사진대장 시트 가져오기 (없으면 헤더와 함께 자동 생성)
  let sheet = ss.getSheetByName(TARGET_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(TARGET_SHEET_NAME);
    initPhotoSheetHeader(sheet);
  }

  // 순번 계산
  const lastRow = Math.max(sheet.getLastRow(), 1);
  const seqNum = (lastRow >= 2) ? (lastRow - 1) : 1;

  // 행 데이터 구성: [현장관리대장 & 대시보드 100% 호환 구조]
  // 순번 | 동 | 층 | 호수 | 공종 | 상태 | 작업내용 및 부위 | 작업일자 | 상세위치 | GPS정보 | 사진링크 | 사진미리보기 | 등록시간
  const newRow = [
    seqNum,
    dong,
    floor,
    unit,
    trade,
    status,
    desc,
    dateFormatted,
    detailLoc,
    gps,
    fileUrl,
    thumbFormula,
    Utilities.formatDate(now, "Asia/Seoul", "yyyy-MM-dd HH:mm:ss")
  ];

  sheet.appendRow(newRow);

  // 3. [현장 대시보드 호환 보강] 상태에 따른 시트 자동 분류 연동
  // 만약 시트에 '진행및대기현황' 또는 '완료목록' 시트가 존재하면 해당 탭에도 행 추가
  syncToDashboardSheets(ss, {
    dong: dong,
    floor: floor,
    unit: unit,
    trade: trade,
    status: status,
    desc: desc,
    date: dateFormatted,
    note: `사진기록: ${fileUrl}`
  });

  return {
    fileUrl: fileUrl,
    rowNumber: sheet.getLastRow()
  };
}

/**
 * 현장 대시보드용 '진행및대기현황' / '완료목록' / 공종별 시트 자동 동기화
 */
function syncToDashboardSheets(ss, item) {
  try {
    const isCompleted = (item.status === "완료");
    const targetTabName = isCompleted ? "완료목록" : "진행및대기현황";
    const targetSheet = ss.getSheetByName(targetTabName);
    
    if (targetSheet) {
      const nextSeq = Math.max(targetSheet.getLastRow() - 2, 1);
      // 순번, 동, 층, 호수, 공종, 상태, 작업내용, 작업일자, 비고
      targetSheet.appendRow([
        nextSeq,
        item.dong,
        item.floor,
        item.unit,
        item.trade,
        item.status,
        item.desc,
        item.date,
        item.note
      ]);
    }

    // 공종별 시트(조적, 미장, 문틀사춤, 타일, 방통 등)가 있으면 그곳에도 동시 기록
    const tradeSheet = ss.getSheetByName(item.trade);
    if (tradeSheet) {
      const tradeSeq = Math.max(tradeSheet.getLastRow() - 2, 1);
      tradeSheet.appendRow([
        tradeSeq,
        item.dong,
        item.floor,
        item.unit,
        item.trade,
        item.status,
        item.desc,
        item.date,
        item.note
      ]);
    }
  } catch (e) {
    Logger.log("대시보드 시트 동기화 생략/오류: " + e.toString());
  }
}

/**
 * 사진대장 시트 헤더 서식 초기화
 */
function initPhotoSheetHeader(sheet) {
  const headers = [
    "순번", "동", "층", "호수", "공종", "상태", 
    "작업내용 및 부위", "작업일자", "상세위치(수기)", "GPS정보", 
    "사진원본링크", "사진미리보기", "등록일시"
  ];
  sheet.appendRow(headers);

  // 헤더 스타일링 (뽀삐 전용 다크네이비 프리미엄 헤더)
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setBackground("#1e293b");
  headerRange.setFontColor("#ffffff");
  headerRange.setFontWeight("bold");
  headerRange.setHorizontalAlignment("center");
  sheet.setFrozenRows(1);
  sheet.setRowHeight(1, 36);

  // 열 너비 자동 조정
  sheet.setColumnWidth(1, 50);  // 순번
  sheet.setColumnWidth(2, 70);  // 동
  sheet.setColumnWidth(3, 60);  // 층
  sheet.setColumnWidth(4, 70);  // 호수
  sheet.setColumnWidth(5, 80);  // 공종
  sheet.setColumnWidth(6, 70);  // 상태
  sheet.setColumnWidth(7, 220); // 작업내용
  sheet.setColumnWidth(8, 100); // 일자
  sheet.setColumnWidth(9, 130); // 상세위치
  sheet.setColumnWidth(10, 160); // GPS
  sheet.setColumnWidth(11, 120); // 링크
  sheet.setColumnWidth(12, 140); // 썸네일
  sheet.setColumnWidth(13, 140); // 등록일시
}

/**
 * 드라이브 폴더 조회 또는 생성
 */
function getOrCreateFolder(folderName) {
  const folders = DriveApp.getFoldersByName(folderName);
  if (folders.hasNext()) {
    return folders.next();
  }
  return DriveApp.createFolder(folderName);
}

function cleanStr(str) {
  if (!str) return "";
  return String(str).replace(/[\\/:*?"<>|]/g, "_").trim();
}
