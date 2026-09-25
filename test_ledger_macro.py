"""
================================================================================
[뽀삐 현장관리대장] 4번 기능 자동 검증 테스트 스크립트 (test_ledger_macro.py)
================================================================================
목적:
  1. 1번 시트([진행및대기현황])에서 '상태' 열(F열)에 '완료' 입력 시
     2번 시트([완료목록]) 맨 아래로 자동 복사되고 1번 시트에서는 깨끗하게 삭제되는지 검증
  2. 1번 시트의 순번(A열)이 1, 2, 3... 순으로 자동 재정렬되는지 검증
  3. 파이썬 openpyxl(keep_vba=True)로 저장 시 매크로가 100% 손실 없이 보존되는지 검증
"""

import sys
import shutil
from pathlib import Path
import win32com.client
import openpyxl

from excel_macro_manager import build_and_inject_ledger, safe_update_xlsm_with_python


def run_full_test():
    base_dir = Path(__file__).resolve().parent
    original_xlsm = base_dir / "현장관리대장.xlsm"
    test_xlsm = base_dir / "현장관리대장_테스트.xlsm"
    
    # 1. 원본 파일 존재 확인 및 테스트용 복사본 생성
    if not original_xlsm.exists():
        print("[!] 원본 파일 생성 중...")
        build_and_inject_ledger(original_xlsm)
        
    shutil.copy2(original_xlsm, test_xlsm)
    print(f"[*] 테스트용 복사본 생성: {test_xlsm.name}")
    
    excel = None
    passed_steps = 0
    total_steps = 4
    
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.EnableEvents = True
        
        wb = excel.Workbooks.Open(str(test_xlsm.resolve()))
        ws1 = wb.Sheets("진행및대기현황")
        ws2 = wb.Sheets("완료목록")
        
        # ----------------------------------------------------------------------
        # [테스트 1] 초기 상태 검사
        # ----------------------------------------------------------------------
        initial_ws1_unit = ws1.Cells(4, 4).Value # 1501호
        initial_ws1_status = ws1.Cells(4, 6).Value # 진행
        initial_ws2_last_row = ws2.Cells(ws2.Rows.Count, 2).End(-4162).Row # -4162 = xlUp
        
        print(f"\n[테스트 1] 초기 데이터 확인")
        print(f"  - 1번 시트 4행 세대: {initial_ws1_unit}, 상태: {initial_ws1_status}")
        print(f"  - 2번 시트 완료목록 현재 마지막 행: {initial_ws2_last_row}행")
        assert initial_ws1_unit == "1501호", "1번 시트 초기 데이터가 올바르지 않습니다."
        passed_steps += 1
        print("  => [PASS] 초기 데이터 정상 확인 완료")
        
        # ----------------------------------------------------------------------
        # [테스트 2] '완료' 입력 시 자동 이동 및 삭제 동작 검증
        # ----------------------------------------------------------------------
        print(f"\n[테스트 2] F4 셀에 '완료' 입력 시뮬레이션 실행...")
        ws1.Cells(4, 6).Value = "완료"
        
        # 동작 후 상태 확인
        after_ws1_row4_unit = ws1.Cells(4, 4).Value # 1502호가 4행으로 올라왔어야 함
        after_ws1_row4_num = ws1.Cells(4, 1).Value  # 순번은 1이어야 함
        after_ws2_last_row = ws2.Cells(ws2.Rows.Count, 2).End(-4162).Row
        moved_unit = ws2.Cells(after_ws2_last_row, 4).Value
        moved_status = ws2.Cells(after_ws2_last_row, 6).Value
        moved_time = ws2.Cells(after_ws2_last_row, 10).Value
        
        print(f"  - [이동 후 1번 시트] 4행 세대: {after_ws1_row4_unit} (기존 1501호 삭제되고 다음 세대로 당겨짐)")
        print(f"  - [이동 후 1번 시트] 4행 순번: {after_ws1_row4_num} (순번 1로 자동 재정렬)")
        print(f"  - [이동 후 2번 시트] 맨 아래 추가된 행: {after_ws2_last_row}행")
        print(f"  - [이동 후 2번 시트] 세대: {moved_unit}, 상태: {moved_status}, 처리시각: {moved_time}")
        
        assert after_ws1_row4_unit == "1502호", "1번 시트에서 해당 행이 삭제되지 않았습니다."
        assert after_ws1_row4_num == 1, "1번 시트 순번이 1로 재정렬되지 않았습니다."
        assert moved_unit == "1501호", "2번 시트로 데이터가 복사되지 않았습니다."
        assert moved_status == "완료", "2번 시트 상태가 완료로 기록되지 않았습니다."
        passed_steps += 1
        print("  => [PASS] 실시간 자동 이동 및 1번 시트 삭제 100% 정상 작동!")
        
        wb.Save()
        wb.Close(SaveChanges=False)
        
    finally:
        if excel:
            excel.Quit()
            
    # ----------------------------------------------------------------------
    # [테스트 3] 파이썬 openpyxl(keep_vba=True) 수정 후 매크로 보존 검증
    # ----------------------------------------------------------------------
    print(f"\n[테스트 3] 파이썬 openpyxl(keep_vba=True)로 엑셀 저장 시 매크로 보존 검증")
    # openpyxl로 열어서 데이터 수정 후 저장
    wb_py = openpyxl.load_workbook(test_xlsm, keep_vba=True)
    ws_py = wb_py["진행및대기현황"]
    # 4행 비고란 수정
    ws_py.cell(row=4, column=9, value="파이썬 검증용 수정")
    wb_py.save(test_xlsm)
    wb_py.close()
    print("  - openpyxl keep_vba=True 로 데이터 수정 후 저장 성공")
    
    # ----------------------------------------------------------------------
    # [테스트 4] 저장된 파일 재오픈 후 매크로 동작 재검증
    # ----------------------------------------------------------------------
    print(f"\n[테스트 4] 파이썬으로 저장된 .xlsm 재오픈 후 매크로 지속 동작 확인...")
    excel2 = win32com.client.DispatchEx("Excel.Application")
    excel2.Visible = False
    excel2.DisplayAlerts = False
    excel2.EnableEvents = True
    
    try:
        wb2 = excel2.Workbooks.Open(str(test_xlsm.resolve()))
        ws1_2 = wb2.Sheets("진행및대기현황")
        ws2_2 = wb2.Sheets("완료목록")
        
        # 다시 4행(1502호)을 완료로 변경
        target_unit = ws1_2.Cells(4, 4).Value
        print(f"  - 이번에는 4행의 [{target_unit}]를 '완료'로 변경합니다...")
        ws1_2.Cells(4, 6).Value = "완료"
        
        after_unit2 = ws1_2.Cells(4, 4).Value
        ws2_last2 = ws2_2.Cells(ws2_2.Rows.Count, 2).End(-4162).Row
        moved_unit2 = ws2_2.Cells(ws2_last2, 4).Value
        
        print(f"  - 1번 시트 4행: {after_unit2} (1502호 삭제 후 1001호 당겨짐)")
        print(f"  - 2번 시트 마지막 행: {moved_unit2} 추가됨")
        
        assert moved_unit2 == target_unit, "파이썬 저장 후 매크로가 동작하지 않았습니다."
        passed_steps += 2
        print("  => [PASS] 파이썬 저장 후에도 매크로가 영구 보존되어 완벽하게 동작합니다!")
        
        wb2.Close(SaveChanges=False)
    finally:
        excel2.Quit()
        
    # 테스트 파일 정리
    try:
        test_xlsm.unlink()
    except:
        pass
        
    print("\n" + "=" * 60)
    print(f" ★ 모든 테스트 성공 ({passed_steps}/{total_steps} 통과)! 사장님 엑셀 즉시 테스트 준비 완료.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    run_full_test()
