/**
 * ================================================================================
 * [뽀삐] 스마트 현장사진대장 - 구글 앱스 스크립트 (Code.gs)
 * ================================================================================
 * 기능:
 *  1. doGet: 모바일 웹앱 HTML 화면 서비스
 *  2. processPhotoRecord: 모바일 웹앱에서 직접 호출(google.script.run)되어 사진 저장 & 시트 기록
 *  3. doPost: 외부 REST API 호출 호환
 *  4. testPermission: 구글 드라이브 & 시트 권한 최초 1회 즉시 승인용 함수
 */

const DRIVE_FOLDER_NAME = "[뽀삐] 스마트 현장사진대장 보관함";
const TARGET_SHEET_NAME = "현장사진대장";

/**
 * [중요] 최초 1회 권한 승인용 테스트 함수
 * 편집기 상단에서 이 함수를 선택하고 [▷ 실행]을 누르시면 구글 드라이브/시트 접근 권한을 1초 만에 승인할 수 있습니다.
 */
function testPermission() {
  const folder = getOrCreateFolder(DRIVE_FOLDER_NAME);
  const ss = getTargetSpreadsheet();
  Logger.log("✅ 권한 승인 성공! 드라이브 폴더: " + folder.getName() + " / 시트: " + ss.getName());
}

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
 * 2. 모바일 웹앱에서 직접 호출하는 핵심 함수 (google.script.run 연동)
 */
function processPhotoRecord(data) {
  try {
    const ss = getTargetSpreadsheet();
    const folder = getOrCreateFolder(DRIVE_FOLDER_NAME);
    
    // Base64 이미지 디코딩
    let rawBase64 = data.imageBase64;
    if (rawBase64.indexOf(',') > -1) {
      rawBase64 = rawBase64.split(',')[1];
    }
    
    const decodedBlob = Utilities.newBlob(
      Utilities.base64Decode(rawBase64), 
      'image/jpeg'
    );

    // 체계적인 파일명 생성: YYYYMMDD_HHMMSS_[동호수]_[공종]_[상태].jpg
    const now = new Date();
    const ts = Utilities.formatDate(now, "Asia/Seoul", "yyyyMMdd_HHmmss");
    const dateFormatted = Utilities.formatDate(now, "Asia/Seoul", "yyyy-MM-dd");
    const dong = data.dong || "101동";
    const floor = data.floor || "01F";
    const unit = data.unit || "101호";
    const detailLoc = data.detailLocation || `${dong} ${unit}`;
    const trade = data.trade || "미지정";
    const status = data.status || "완료";
    const desc = data.description || "-";
    const gps = data.gps || "-";

    const fileName = `${ts}_${cleanStr(dong)}_${cleanStr(unit)}_${cleanStr(trade)}_${cleanStr(status)}.jpg`;
    decodedBlob.setName(fileName);

    // 구글 드라이브에 저장 및 전체 공개 보기 권한 설정
    const file = folder.createFile(decodedBlob);
    try {
      file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    } catch(e) {
      // 도메인 정책 등으로 setSharing 실패 시 패스
    }
    
    const fileUrl = file.getUrl();
    const fileId = file.getId();
    const thumbFormula = `=IMAGE("https://drive.google.com/thumbnail?id=${fileId}&sz=w400")`;

    // 메인 사진대장 시트 가져오기 (없으면 헤더와 함께 자동 생성)
    let sheet = ss.getSheetByName(TARGET_SHEET_NAME);
    if (!sheet) {
      sheet = ss.insertSheet(TARGET_SHEET_NAME);
      initPhotoSheetHeader(sheet);
    }

    const lastRow = Math.max(sheet.getLastRow(), 1);
    const seqNum = (lastRow >= 2) ? (lastRow - 1) : 1;

    // 대시보드 100% 호환 행 추가
    sheet.appendRow([
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
    ]);

    // 대시보드 상태 탭(완료목록 / 진행및대기현황) 및 공종별 탭에도 자동 동기화
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
      success: true,
      message: "구글 시트와 드라이브에 정상 저장되었습니다.",
      fileUrl: fileUrl,
      rowNumber: sheet.getLastRow()
    };

  } catch (err) {
    Logger.log("processPhotoRecord 에러: " + err.toString());
    return {
      success: false,
      message: "저장 실패: " + err.toString()
    };
  }
}

/**
 * 3. 외부 HTTP POST 요청 처리 (하위 호환)
 */
function doPost(e) {
  try {
    const postData = JSON.parse(e.postData.contents);
    const result = processPhotoRecord(postData);
    
    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * 스프레드시트 인스턴스 안전 획득
 */
function getTargetSpreadsheet() {
  let ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss) return ss;
  
  const files = DriveApp.getFilesByName("현장관리대장_스마트사진");
  if (files.hasNext()) {
    return SpreadsheetApp.open(files.next());
  }
  return SpreadsheetApp.create("현장관리대장_스마트사진");
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

  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setBackground("#1e293b");
  headerRange.setFontColor("#ffffff");
  headerRange.setFontWeight("bold");
  headerRange.setHorizontalAlignment("center");
  sheet.setFrozenRows(1);
  sheet.setRowHeight(1, 36);

  sheet.setColumnWidth(1, 50);
  sheet.setColumnWidth(2, 70);
  sheet.setColumnWidth(3, 60);
  sheet.setColumnWidth(4, 70);
  sheet.setColumnWidth(5, 80);
  sheet.setColumnWidth(6, 70);
  sheet.setColumnWidth(7, 220);
  sheet.setColumnWidth(8, 100);
  sheet.setColumnWidth(9, 130);
  sheet.setColumnWidth(10, 160);
  sheet.setColumnWidth(11, 120);
  sheet.setColumnWidth(12, 140);
  sheet.setColumnWidth(13, 140);
}

/**
 * 상태별 / 공종별 시트 자동 연동
 */
function syncToDashboardSheets(ss, item) {
  try {
    const isCompleted = (item.status === "완료");
    const targetTabName = isCompleted ? "완료목록" : "진행및대기현황";
    const targetSheet = ss.getSheetByName(targetTabName);
    
    if (targetSheet) {
      const nextSeq = Math.max(targetSheet.getLastRow() - 2, 1);
      targetSheet.appendRow([
        nextSeq, item.dong, item.floor, item.unit, item.trade, item.status, item.desc, item.date, item.note
      ]);
    }

    const tradeSheet = ss.getSheetByName(item.trade);
    if (tradeSheet) {
      const tradeSeq = Math.max(tradeSheet.getLastRow() - 2, 1);
      tradeSheet.appendRow([
        tradeSeq, item.dong, item.floor, item.unit, item.trade, item.status, item.desc, item.date, item.note
      ]);
    }
  } catch (e) {
    Logger.log("대시보드 동기화 스킵: " + e.toString());
  }
}

function cleanStr(str) {
  if (!str) return "";
  return String(str).replace(/[\\/:*?"<>|]/g, "_").trim();
}
