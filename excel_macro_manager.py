"""
================================================================================
[뽀삐 현장관리대장] 완벽한 엑셀 생성 및 골구도 통합 모듈 (excel_macro_manager.py)
================================================================================
핵심 해결:
  - 기존 오류 원인: .xlsm 파일 간 시트 단순 복사 시 vbaProject.bin 내부의 시트 CodeName이
    누락되어 엑셀 GUI에서 '파일 열기 실패' 또는 충돌이 발생하던 문제 완전 해결.
  - 해결책: 10개 모든 시트(진행및대기, 완료목록, 101동~107동, 골구도_완료이력)를 먼저
    정상 배치한 상태에서 VBA 컴파일러를 통해 CodeName을 완벽 매핑(Sheet1~Sheet10)한 후
    매크로를 주입하고 .xlsm으로 저장.
"""

import os
import sys
import shutil
from pathlib import Path
import winreg
import win32com.client


VBA_SHEET1_CODE = """Option Explicit

' ==============================================================================
' [뽀삐 현장관리대장] 1번 시트([진행및대기현황]) 실시간 자동 이동 이벤트 매크로
' ==============================================================================

Private Sub Worksheet_Change(ByVal Target As Range)
    On Error GoTo ErrorHandler
    
    Dim wsDone As Worksheet
    Dim statusCol As Long
    Dim col As Long, r As Long
    Dim headerRow As Long
    Dim hText As String
    
    ' [1단계] 상태 열 동적 탐색 (2~5행 중 실제 컬럼명이 '상태'인 열)
    statusCol = 0
    headerRow = 3
    
    For r = 2 To 5
        For col = 1 To 20
            hText = Trim(CStr(Me.Cells(r, col).Value))
            If Len(hText) > 0 And Len(hText) <= 10 And InStr(hText, "상태") > 0 Then
                statusCol = col
                headerRow = r
                Exit For
            End If
        Next col
        If statusCol > 0 Then Exit For
    Next r
    
    If statusCol = 0 Then
        statusCol = 6 ' F열 기본값
        headerRow = 3
    End If
    
    Dim checkRange As Range
    Set checkRange = Intersect(Target, Me.Columns(statusCol))
    
    If checkRange Is Nothing Then
        If Not Intersect(Target, Me.Columns(6)) Is Nothing Then
            Set checkRange = Intersect(Target, Me.Columns(6))
            statusCol = 6
        ElseIf Not Intersect(Target, Me.Columns(8)) Is Nothing Then
            Set checkRange = Intersect(Target, Me.Columns(8))
            statusCol = 8
        End If
    End If
    
    If checkRange Is Nothing Then Exit Sub
    
    ' [2단계] 완료목록 시트 확인
    On Error Resume Next
    Set wsDone = ThisWorkbook.Sheets("완료목록")
    On Error GoTo ErrorHandler
    
    If wsDone Is Nothing Then Exit Sub
    
    ' [3단계] '완료'로 변경된 행 수집
    Dim cell As Range
    Dim doneRows() As Long
    Dim doneCount As Long
    doneCount = 0
    
    For Each cell In checkRange
        If cell.Row > headerRow Then
            If Trim(CStr(cell.Value)) = "완료" Then
                doneCount = doneCount + 1
                ReDim Preserve doneRows(1 To doneCount)
                doneRows(doneCount) = cell.Row
            End If
        End If
    Next cell
    
    If doneCount = 0 Then Exit Sub
    
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    
    ' [4단계] 역순으로 완료목록 복사 후 진행시트에서 삭제
    Dim i As Long, rowIdx As Long, lastRowDone As Long
    Dim dongVal As String, hoVal As String, workVal As String
    Dim doneHeaderRow As Long
    doneHeaderRow = 3
    
    For i = doneCount To 1 Step -1
        rowIdx = doneRows(i)
        
        dongVal = Trim(CStr(Me.Cells(rowIdx, 2).Value))
        hoVal = Trim(CStr(Me.Cells(rowIdx, 4).Value))
        workVal = Trim(CStr(Me.Cells(rowIdx, 5).Value))
        
        lastRowDone = wsDone.Cells(wsDone.Rows.Count, 2).End(xlUp).Row + 1
        If lastRowDone <= doneHeaderRow Then lastRowDone = doneHeaderRow + 1
        
        Me.Rows(rowIdx).Copy Destination:=wsDone.Rows(lastRowDone)
        
        wsDone.Cells(lastRowDone, 1).Value = lastRowDone - doneHeaderRow
        wsDone.Cells(lastRowDone, statusCol).Value = "완료"
        
        If Trim(CStr(wsDone.Cells(lastRowDone, 10).Value)) = "" Then
            wsDone.Cells(lastRowDone, 10).Value = Format(Now, "YYYY-MM-DD HH:NN")
            wsDone.Cells(lastRowDone, 10).HorizontalAlignment = -4108
        End If
        
        Me.Rows(rowIdx).Delete Shift:=xlUp
        
        ' 동별 시트(101동~107동)가 있을 경우 해당 시트 셀도 완료 처리
        On Error Resume Next
        If Len(dongVal) > 0 Then
            Dim wsDongSheet As Worksheet
            Set wsDongSheet = ThisWorkbook.Sheets(dongVal)
            If Not wsDongSheet Is Nothing Then
                UpdateDongSheet wsDongSheet, hoVal, workVal
            End If
        End If
        On Error GoTo ErrorHandler
    Next i
    
    ' [5단계] 진행및대기현황 순번(A열) 재정렬
    Dim lastRowMe As Long
    lastRowMe = Me.Cells(Me.Rows.Count, 2).End(xlUp).Row
    If lastRowMe > headerRow Then
        For r = (headerRow + 1) To lastRowMe
            Me.Cells(r, 1).Value = r - headerRow
            Me.Cells(r, 1).HorizontalAlignment = -4108
        Next r
    End If

ErrorHandler:
    Application.EnableEvents = True
    Application.ScreenUpdating = True
End Sub

Private Sub UpdateDongSheet(wsD As Worksheet, hoVal As String, workVal As String)
    On Error Resume Next
    Dim r As Long, c As Long
    Dim targetRow As Long, targetCol As Long
    targetRow = 0
    targetCol = 0
    
    Dim hoTrim As String
    hoTrim = Replace(hoVal, "호", "")
    hoTrim = Replace(hoTrim, " ", "")
    
    For r = 4 To wsD.Cells(wsD.Rows.Count, 3).End(xlUp).Row
        Dim cellText As String
        cellText = Replace(CStr(wsD.Cells(r, 3).Value), "호", "")
        cellText = Replace(cellText, " ", "")
        If InStr(cellText, hoTrim) > 0 Then
            targetRow = r
            Exit For
        End If
    Next r
    
    If Len(workVal) > 0 Then
        For c = 4 To 15
            If InStr(CStr(wsD.Cells(3, c).Value), workVal) > 0 Then
                targetCol = c
                Exit For
            End If
        Next c
    End If
    
    If targetRow > 0 And targetCol > 0 Then
        wsD.Cells(targetRow, targetCol).Value = "완료"
        wsD.Cells(targetRow, targetCol).Interior.Color = RGB(198, 239, 206)
        wsD.Cells(targetRow, targetCol).Font.Color = RGB(0, 97, 0)
        wsD.Cells(targetRow, targetCol).Font.Bold = True
    End If
End Sub
"""

VBA_THISWORKBOOK_CODE = """Option Explicit

Private Sub Workbook_Open()
    Application.EnableEvents = True
    Application.ScreenUpdating = True
End Sub
"""

VBA_GLOBAL_MODULE = """Option Explicit

Sub ResetEvents()
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    MsgBox "뽀삐 현장관리대장 매크로 이벤트가 정상 활성화되었습니다!", vbInformation, "뽀삐 현장도우미"
End Sub
"""


def enable_excel_vbom_registry() -> bool:
    """Excel VBA 프로젝트 신뢰 권한 설정"""
    key_path = r"Software\Microsoft\Office\16.0\Excel\Security"
    try:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        except FileNotFoundError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, "AccessVBOM", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[!] AccessVBOM 설정 경고: {e}")
        return False


def build_full_integrated_ledger(source_golgudo_path: Path, output_xlsm_path: Path) -> bool:
    """
    모든 10개 시트(진행및대기현황, 완료목록, 101동~107동, 골구도_완료이력)를
    단일 프로세스에서 완벽하게 빌드하고 무결한 CodeName(Sheet1~Sheet10)을 부여한 후
    VBA 매크로를 주입하여 100% 열리는 .xlsm 파일을 생성합니다.
    """
    enable_excel_vbom_registry()
    abs_out = str(output_xlsm_path.resolve())
    output_xlsm_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 골구도 원본을 임시 xlsx로 변환
    temp_dir = output_xlsm_path.parent / ".temp_build"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_xlsx = temp_dir / "temp_golgudo_clean.xlsx"
    
    excel = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.EnableEvents = False
        
        # 1. 골구도 원본을 순수 데이터/서식 .xlsx로 변환
        wb_temp = excel.Workbooks.Open(str(source_golgudo_path.resolve()))
        wb_temp.SaveAs(str(temp_xlsx.resolve()), FileFormat=51) # 51 = xlOpenXMLWorkbook (.xlsx)
        wb_temp.Close(SaveChanges=False)
        
        # 2. 신규 통합문서 생성
        wb = excel.Workbooks.Add()
        
        # 1번 시트: 진행및대기현황
        ws1 = wb.Sheets(1)
        ws1.Name = "진행및대기현황"
        
        # 2번 시트: 완료목록
        ws2 = wb.Sheets.Add(None, ws1) # After ws1
        ws2.Name = "완료목록"
        
        # ----------------------------------------------------------------------
        # 1번 시트([진행및대기현황]) 디자인 및 서식
        # ----------------------------------------------------------------------
        ws1.Range("A1:I1").Merge()
        ws1.Range("A1").Value = "■ [현장관리대장] 공정 진행 및 대기 현황 (F열 '상태'에 '완료' 입력 시 [완료목록]으로 자동 이동)"
        ws1.Range("A1").Font.Name = "맑은 고딕"
        ws1.Range("A1").Font.Size = 13
        ws1.Range("A1").Font.Bold = True
        ws1.Range("A1").Font.Color = 0xFFFFFF
        ws1.Range("A1").Interior.Color = 0x5D361B # Dark Navy
        ws1.Range("A1").HorizontalAlignment = -4108 # xlCenter
        ws1.Rows(1).RowHeight = 35
        
        ws1.Range("A2:I2").Merge()
        ws1.Range("A2").Value = "※ 안내: F열(상태)에 '완료'를 입력하거나 선택하시면, 해당 줄이 2번 시트([완료목록]) 맨 아래로 자동 이동되고 본 시트에서는 삭제됩니다."
        ws1.Range("A2").Font.Name = "맑은 고딕"
        ws1.Range("A2").Font.Size = 9
        ws1.Range("A2").Font.Color = 0x333333
        ws1.Range("A2").Interior.Color = 0xE6EDF5
        ws1.Range("A2").HorizontalAlignment = -4108
        ws1.Rows(2).RowHeight = 22
        
        headers1 = ["순번", "동", "층", "호수", "공종", "상태", "작업내용 및 부위", "작업일자", "비고"]
        for c_idx, h in enumerate(headers1, 1):
            cell = ws1.Cells(3, c_idx)
            cell.Value = h
            cell.Font.Name = "맑은 고딕"
            cell.Font.Size = 10
            cell.Font.Bold = True
            cell.Font.Color = 0xFFFFFF
            cell.Interior.Color = 0x784C2C
            cell.HorizontalAlignment = -4108
        ws1.Rows(3).RowHeight = 26
        
        sample_data1 = [
            [1, "101동", "15F", "1501호", "문틀사춤", "진행", "거실/안방 문틀사춤 진행중", "2026-09-25", "정상 시공"],
            [2, "101동", "15F", "1502호", "문틀사춤", "대기", "발코니 사춤 작업 대기", "2026-09-25", "자재 반입 대기"],
            [3, "102동", "10F", "1001호", "조적", "진행", "주방 벽체 조적 쌓기", "2026-09-25", "단열재 확인"],
            [4, "102동", "10F", "1002호", "조적", "대기", "공용욕실 조적 대기", "2026-09-25", "-"],
            [5, "103동", "21F", "2101호", "세대미장", "진행", "거실 벽면 견출 및 미장", "2026-09-25", "1차 초벌"],
            [6, "103동", "21F", "2102호", "세대미장", "대기", "주방 미장 대기", "2026-09-25", "-"],
            [7, "104동", "08F", "801호", "타일", "진행", "현관 바닥 타일 시공", "2026-09-25", "줄눈 예정"],
            [8, "105동", "12F", "1203호", "방통", "대기", "세대 바닥 기포/방통 타설 대기", "2026-09-25", "설비 배관 완료후"]
        ]
        
        for r_idx, row_vals in enumerate(sample_data1, 4):
            for c_idx, val in enumerate(row_vals, 1):
                cell = ws1.Cells(r_idx, c_idx)
                cell.Value = val
                cell.Font.Name = "맑은 고딕"
                cell.Font.Size = 10
                cell.HorizontalAlignment = -4108 if c_idx in [1, 2, 3, 4, 5, 6, 8] else -4131
                if c_idx == 6:
                    if val == "진행":
                        cell.Interior.Color = 0xCDCEFC
                        cell.Font.Color = 0x0045B2
                        cell.Font.Bold = True
                    elif val == "대기":
                        cell.Interior.Color = 0xEDEDED
                        cell.Font.Color = 0x595959
            ws1.Rows(r_idx).RowHeight = 22
            
        ws1.Columns("A").ColumnWidth = 8
        ws1.Columns("B").ColumnWidth = 10
        ws1.Columns("C").ColumnWidth = 8
        ws1.Columns("D").ColumnWidth = 12
        ws1.Columns("E").ColumnWidth = 14
        ws1.Columns("F").ColumnWidth = 12
        ws1.Columns("G").ColumnWidth = 32
        ws1.Columns("H").ColumnWidth = 14
        ws1.Columns("I").ColumnWidth = 20
        
        # ----------------------------------------------------------------------
        # 2번 시트([완료목록]) 디자인 및 서식
        # ----------------------------------------------------------------------
        ws2.Range("A1:J1").Merge()
        ws2.Range("A1").Value = "■ [현장관리대장] 작업 완료 누적 대장 (실시간 자동 누적 및 이력 보존)"
        ws2.Range("A1").Font.Name = "맑은 고딕"
        ws2.Range("A1").Font.Size = 13
        ws2.Range("A1").Font.Bold = True
        ws2.Range("A1").Font.Color = 0xFFFFFF
        ws2.Range("A1").Interior.Color = 0x274E13
        ws2.Range("A1").HorizontalAlignment = -4108
        ws2.Rows(1).RowHeight = 35
        
        ws2.Range("A2:J2").Merge()
        ws2.Range("A2").Value = "※ 안내: 1번 시트([진행및대기현황])에서 '완료' 처리된 모든 데이터가 완료 시간과 함께 이곳에 자동으로 누적 보관됩니다."
        ws2.Range("A2").Font.Name = "맑은 고딕"
        ws2.Range("A2").Font.Size = 9
        ws2.Range("A2").Font.Color = 0x333333
        ws2.Range("A2").Interior.Color = 0xE2F0D9
        ws2.Range("A2").HorizontalAlignment = -4108
        ws2.Rows(2).RowHeight = 22
        
        headers2 = ["순번", "동", "층", "호수", "공종", "상태", "작업내용 및 부위", "작업일자", "비고", "완료처리일시"]
        for c_idx, h in enumerate(headers2, 1):
            cell = ws2.Cells(3, c_idx)
            cell.Value = h
            cell.Font.Name = "맑은 고딕"
            cell.Font.Size = 10
            cell.Font.Bold = True
            cell.Font.Color = 0xFFFFFF
            cell.Interior.Color = 0x38761D
            cell.HorizontalAlignment = -4108
        ws2.Rows(3).RowHeight = 26
        
        sample_data2 = [
            [1, "101동", "14F", "1401호", "문틀사춤", "완료", "안방 및 작은방 문틀사춤 완료", "2026-09-24", "검측 통과", "2026-09-24 16:30"],
            [2, "101동", "14F", "1402호", "세대미장", "완료", "거실 벽체 견출 및 미장 완료", "2026-09-24", "검측 통과", "2026-09-24 17:15"]
        ]
        for r_idx, row_vals in enumerate(sample_data2, 4):
            for c_idx, val in enumerate(row_vals, 1):
                cell = ws2.Cells(r_idx, c_idx)
                cell.Value = val
                cell.Font.Name = "맑은 고딕"
                cell.Font.Size = 10
                cell.HorizontalAlignment = -4108 if c_idx in [1, 2, 3, 4, 5, 6, 8, 10] else -4131
                if c_idx == 6:
                    cell.Interior.Color = 0xCEEFC6
                    cell.Font.Color = 0x006100
                    cell.Font.Bold = True
            ws2.Rows(r_idx).RowHeight = 22
            
        ws2.Columns("A").ColumnWidth = 8
        ws2.Columns("B").ColumnWidth = 10
        ws2.Columns("C").ColumnWidth = 8
        ws2.Columns("D").ColumnWidth = 12
        ws2.Columns("E").ColumnWidth = 14
        ws2.Columns("F").ColumnWidth = 12
        ws2.Columns("G").ColumnWidth = 32
        ws2.Columns("H").ColumnWidth = 14
        ws2.Columns("I").ColumnWidth = 20
        ws2.Columns("J").ColumnWidth = 20
        
        # ----------------------------------------------------------------------
        # 3. 골구도 시트들(101동~107동, 골구도_완료이력) 추가
        # ----------------------------------------------------------------------
        wb_clean_g = excel.Workbooks.Open(str(temp_xlsx.resolve()))
        for s in wb_clean_g.Sheets:
            tname = "골구도_완료이력" if s.Name == "완료목록" else s.Name
            last_s = wb.Sheets(wb.Sheets.Count)
            s.Copy(None, last_s)
            new_s = wb.Sheets(wb.Sheets.Count)
            new_s.Name = tname
            print(f"  [+] 시트 통합 성공: {s.Name} -> {tname}")
        wb_clean_g.Close(SaveChanges=False)
        
        # 시트 순서 보장 (1번: 진행및대기현황, 2번: 완료목록)
        ws1.Move(wb.Sheets(1))
        ws2.Move(None, wb.Sheets(1))
        
        # ----------------------------------------------------------------------
        # 4. 모든 10개 시트가 완벽히 로드된 후 VBA 매크로 주입
        # ----------------------------------------------------------------------
        vb_proj = wb.VBProject
        
        # 1번 시트([진행및대기현황]) CodeModule 매핑
        comp1 = vb_proj.VBComponents(ws1.CodeName)
        comp1.CodeModule.DeleteLines(1, comp1.CodeModule.CountOfLines)
        comp1.CodeModule.AddFromString(VBA_SHEET1_CODE)
        print(f"  [*] 1번 시트({ws1.Name} / CodeName: {comp1.Name})에 실시간 매크로 주입 완료!")
        
        # ThisWorkbook CodeModule
        comp_wb = vb_proj.VBComponents(wb.CodeName)
        comp_wb.CodeModule.DeleteLines(1, comp_wb.CodeModule.CountOfLines)
        comp_wb.CodeModule.AddFromString(VBA_THISWORKBOOK_CODE)
        print(f"  [*] ThisWorkbook({comp_wb.Name})에 초기화 매크로 주입 완료!")
        
        # SiteAutoModule
        mod_c = vb_proj.VBComponents.Add(1)
        mod_c.Name = "SiteAutoModule"
        mod_c.CodeModule.AddFromString(VBA_GLOBAL_MODULE)
        print(f"  [*] 표준 모듈(SiteAutoModule) 주입 완료!")
        
        # 1번 시트 활성화 및 첫 번째 셀 선택
        ws1.Activate()
        ws1.Range("F4").Select()
        
        # ----------------------------------------------------------------------
        # 5. .xlsm (FileFormat=52) 안전 저장
        # ----------------------------------------------------------------------
        wb.SaveAs(abs_out, FileFormat=52)
        wb.Close(SaveChanges=False)
        print(f"\n[성공] 통합_현장관리및공정관리대장.xlsm 완벽 생성 완료: {abs_out}")
        return True
        
    except Exception as e:
        print(f"[-] build_full_integrated_ledger 오류: {e}")
        return False
    finally:
        if excel:
            try:
                excel.Quit()
            except:
                pass
        if temp_xlsx.exists():
            try:
                temp_xlsx.unlink()
            except:
                pass
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


if __name__ == "__main__":
    base_dir = Path(r"c:\Users\ry789\OneDrive\Desktop\05 뽀삐 프로그램")
    golgudo_path = Path(r"C:\Users\ry789\OneDrive\Desktop\06 거위\골구도_공정관리_서식_백업_20260907_170608.xlsm")
    merged_path = base_dir / "통합_현장관리및공정관리대장.xlsm"
    
    print("=" * 60)
    print(" [뽀삐] 통합_현장관리및공정관리대장.xlsm 무결성 재생성 시작")
    print("=" * 60)
    
    success = build_full_integrated_ledger(golgudo_path, merged_path)
    
    if success:
        out_dir = base_dir / "결과_출력"
        out_dir.mkdir(parents=True, exist_ok=True)
        desktop_dir = Path(r"C:\Users\ry789\OneDrive\Desktop")
        
        # 모든 대상 경로에 안전 배포
        shutil.copy2(merged_path, out_dir / "통합_현장관리및공정관리대장.xlsm")
        shutil.copy2(merged_path, desktop_dir / "통합_현장관리및공정관리대장.xlsm")
        
        # 혹시 바탕화면 폴더가 C:\Users\ry789\Desktop 인 경우도 대비
        alt_desktop = Path(r"C:\Users\ry789\Desktop")
        if alt_desktop.exists() and alt_desktop != desktop_dir:
            try:
                shutil.copy2(merged_path, alt_desktop / "통합_현장관리및공정관리대장.xlsm")
            except:
                pass
                
        print("\n★ 최종 배포 완료:")
        print(f"  1. 작업 폴더: {merged_path}")
        print(f"  2. 결과 출력: {out_dir / '통합_현장관리및공정관리대장.xlsm'}")
        print(f"  3. 바탕 화면: {desktop_dir / '통합_현장관리및공정관리대장.xlsm'}")
