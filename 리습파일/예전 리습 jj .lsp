;; ========================================================
;; [JJ] 폐곡선 벽체 면적/둘레 기반 단독 물량 산출 리습 (Pro 버전)
;; - 조적: 닫힌 벽체 다중 선택 -> 단면적(m2) x 층고 = 체적(m3)
;; - 미장: 선 다중 선택 -> 둘레길이 x 시공높이 = 면적(m2)
;; - 타일: 질문 최소화 초스피드 모드 (규격+부위 통합 선택)
;; - 방통: 해치/폴리선 클릭 -> 바닥면적 및 두께로 체적(루베) 산출
;; - 업데이트: OneDrive 인식, 엑셀 오류방지, 공제 가로*세로 동시입력 지원
;; ========================================================

(vl-load-com)

(defun c:JJ ( / *error* 
                fn_get_deduction fn_write_csv fn_get_closed fn_get_length
                m_type ss_data plan_area_mm len_mm plan_area_m h_m 
                op_data op_w_m op_h_m op_ea thick_mm thick_m deduct_vol b_vol brick_cnt jj_remital
                len_m mj_t_mm mj_area mj_remital
                t_part t_type t_box_pcs t_w t_h t_name wall_area floor_area_m tile_area total_tile_pcs total_boxes tile_remital
                bt_t_mm vol_m bt_remital bt_remicon)

  ;; --------------------------------------------------------
  ;; [오류 처리]
  ;; --------------------------------------------------------
  (defun *error* (msg)
    (if (not (member msg '("Function cancelled" "quit / exit abort")))
      (princ (strcat "\n[오류] " msg))
    )
    (princ)
  )

  ;; --------------------------------------------------------
  ;; [함수 1] 공제 물량(개구부) 가로*세로 동시 입력 지원
  ;; --------------------------------------------------------
  (defun fn_get_deduction ( / str temp_str idx w h ea)
    ;; 공백이 포함되어도 문자열로 받을 수 있게 T 인자 사용
    (setq str (getstring T "\n공제 사이즈(가로*세로) 입력 (예: 900*2100) [없으면 엔터/스페이스바]: "))
    
    (if (or (= str "") (= str "0") (= str " "))
      (list 0.0 0.0 0)
      (progn
        ;; x, X, 쉼표, 슬래시 등을 모두 * 로 통일
        (setq temp_str (vl-string-translate "xX, /" "*****" str))
        (setq idx (vl-string-search "*" temp_str))
        
        (if idx
          (progn
            ;; * 가 있으면 앞뒤로 쪼개기
            (setq w (atof (substr temp_str 1 idx)))
            (setq h (atof (substr temp_str (+ idx 2))))
          )
          (progn
            ;; * 없이 숫자만 쳤을 경우 가로로 인식하고 세로를 별도 질문
            (setq w (atof temp_str))
            (setq h (getreal "\n공제 세로(mm) 입력 <2100>: "))
            (if (null h) (setq h 2100.0))
          )
        )
        
        (setq ea (getint "\n공제 개소(수량) 입력 <1>: "))
        (if (null ea) (setq ea 1))
        
        (list (/ w 1000.0) (/ h 1000.0) ea)
      )
    )
  )

  ;; --------------------------------------------------------
  ;; [함수 2] CSV 엑셀 파일 기록 (OneDrive 연동 인식 및 에러 방지)
  ;; --------------------------------------------------------
  (defun fn_write_csv (gong_name val1 val2 val3 res1 res2 / desk_path csv_path file)
    ;; 바탕화면 경로 찾기 (원드라이브 연동 여부 확인)
    (setq desk_path (strcat (getenv "USERPROFILE") "\\OneDrive\\Desktop"))
    (if (not (vl-file-directory-p desk_path))
      (setq desk_path (strcat (getenv "USERPROFILE") "\\Desktop"))
    )
    (setq csv_path (strcat desk_path "\\현장_물량집계.csv"))
    
    (if (not (findfile csv_path))
      (progn
        (setq file (open csv_path "w"))
        (write-line "날짜/시간,공종,바닥면적(m2)/길이(m),높이/두께(m),체적(m3)/면적(m2),결과1,결과2" file)
        (close file)
      )
    )
    
    (setq file (open csv_path "a"))
    (if file
      (progn
        (write-line 
          (strcat 
            (menucmd "M=$(edtime,$(getvar,date),YYYY-MO-DD HH:MM)") "," gong_name ","
            val1 "," val2 "," val3 "," res1 "," res2
          )
          file
        )
        (close file)
        (princ (strcat "\n-> 바탕화면 [현장_물량집계.csv]에 저장되었습니다.\n"))
      )
      (princ "\n[경고!] 엑셀 파일이 열려있어서 저장하지 못했습니다. 엑셀을 닫고 다시 산출해주세요!\n")
    )
  )

  ;; --------------------------------------------------------
  ;; [함수 3] 닫힌 폴리선 및 해치(HATCH) 다중 선택 - 조적/바닥/방통용
  ;; --------------------------------------------------------
  (defun fn_get_closed (msg / ss i ent obj oType area len sum_area sum_len)
    (princ (strcat "\n" msg))
    (setq ss (ssget '((0 . "LWPOLYLINE,POLYLINE,CIRCLE,ELLIPSE,HATCH"))))
    (while (null ss)
      (princ "\n선택되지 않았습니다. 폴리선 또는 해치를 다시 클릭하세요: ")
      (setq ss (ssget '((0 . "LWPOLYLINE,POLYLINE,CIRCLE,ELLIPSE,HATCH"))))
    )
    (setq sum_area 0.0 sum_len 0.0 i 0)
    (while (< i (sslength ss))
      (setq ent (ssname ss i))
      (setq obj (vlax-ename->vla-object ent))
      (setq oType (cdr (assoc 0 (entget ent))))
      
      (if (= oType "HATCH")
        (progn
          (setq area (vla-get-Area obj))
          (setq len 0.0)
        )
        (progn
          (setq area (vlax-curve-getArea obj))
          (setq len (vlax-curve-getDistAtParam obj (vlax-curve-getEndParam obj)))
        )
      )
      (setq sum_area (+ sum_area area))
      (setq sum_len (+ sum_len len))
      (setq i (1+ i))
    )
    (princ (strcat "\n-> 선택된 객체 수: " (itoa (sslength ss)) " 개"))
    (list sum_area sum_len)
  )

  ;; --------------------------------------------------------
  ;; [함수 4] 선 다중 선택 (길이 합산) - 미장/벽타일용
  ;; --------------------------------------------------------
  (defun fn_get_length (msg / ss i ent obj len sum_len)
    (princ (strcat "\n" msg))
    (setq ss (ssget '((0 . "LINE,LWPOLYLINE,POLYLINE,ARC,CIRCLE"))))
    (while (null ss)
      (princ "\n선택되지 않았습니다. 다시 클릭하세요: ")
      (setq ss (ssget '((0 . "LINE,LWPOLYLINE,POLYLINE,ARC,CIRCLE"))))
    )
    (setq sum_len 0.0 i 0)
    (while (< i (sslength ss))
      (setq ent (ssname ss i))
      (setq obj (vlax-ename->vla-object ent))
      (setq len (vlax-curve-getDistAtParam obj (vlax-curve-getEndParam obj)))
      (setq sum_len (+ sum_len len))
      (setq i (1+ i))
    )
    (princ (strcat "\n-> 선택된 객체 수: " (itoa (sslength ss)) " 개"))
    (/ sum_len 1000.0)
  )


  ;; ========================================================
  ;; 프로그램 시작
  ;; ========================================================
  (princ "\n==============================================")
  (princ "\n>>> [JJ] 현장 물량 단독 산출 프로그램 (Pro) <<<")
  (princ "\n==============================================")

  (initget "1 2 3 4")
  (setq m_type (getkword "\n산출 공종 선택 [1: 조적 / 2: 미장 / 3: 타일 / 4: 방통(바닥미장)] <1>: "))
  (if (null m_type) (setq m_type "1"))

  ;; ========================================================
  ;; [1번: 조적만 산출]
  ;; ========================================================
  (if (= m_type "1")
    (progn
      (setq ss_data (fn_get_closed "[조적] 벽체 폴리선 또는 해치(HATCH)를 선택하세요 (다중선택 가능): "))
      (setq plan_area_mm (car ss_data))
      (setq len_mm (cadr ss_data))
      (setq plan_area_m (/ plan_area_mm 1000000.0))

      (princ (strcat "\n-> 감지된 총 벽체 단면적: " (rtos plan_area_m 2 3) " ㎡"))

      (setq h_m (/ (cond ((getreal "\n층고 입력(mm) <2400>: ")) (2400.0)) 1000.0))

      (setq op_data (fn_get_deduction))
      (setq op_w_m (nth 0 op_data) op_h_m (nth 1 op_data) op_ea (nth 2 op_data))

      (setq b_vol (* plan_area_m h_m))
      
      (if (> op_w_m 0)
        (progn
          (if (> len_mm 0)
            (setq thick_m (/ plan_area_mm len_mm 0.5 1000.0))
            (progn
              (setq thick_mm (getreal "\n해치(Hatch) 전용 선택입니다. 공제용 벽체 두께(mm)를 입력하세요 <200>: "))
              (if (null thick_mm) (setq thick_mm 200.0))
              (setq thick_m (/ thick_mm 1000.0))
            )
          )
          (setq deduct_vol (* op_w_m op_h_m op_ea thick_m))
          (setq b_vol (- b_vol deduct_vol))
        )
      )
      (if (< b_vol 0) (setq b_vol 0.0))

      (setq brick_cnt (fix (+ (* b_vol 773.0) 0.999)))
      (setq jj_remital (fix (+ (* b_vol 7.5) 0.999)))

      (princ "\n----------------------------------------------")
      (princ "\n[조적 물량 단독 산출 결과]")
      (princ (strcat "\n- 벽체 총 단면적: " (rtos plan_area_m 2 3) " ㎡"))
      (princ (strcat "\n- 벽체 층고 높이: " (rtos h_m 2 2) " m"))
      (if (> op_ea 0) (princ (strcat "\n- 개구부 공제   : " (itoa op_ea) " 개소 반영 완료")))
      (princ (strcat "\n- 순 벽체 체적  : " (rtos b_vol 2 3) " ㎥ (루베)"))
      (princ (strcat "\n■ 시멘트 벽돌  : " (itoa brick_cnt) " 장 (할증 3% 포함)"))
      (princ (strcat "\n■ 조적용 레미탈: " (itoa jj_remital) " 포 (40kg 기준)"))
      (princ "\n==============================================")

      (fn_write_csv "조적" (rtos plan_area_m 2 3) (rtos h_m 2 2) (rtos b_vol 2 3) (strcat (itoa brick_cnt) "장") (strcat (itoa jj_remital) "포"))
    )
  )

  ;; ========================================================
  ;; [2번: 미장만 산출]
  ;; ========================================================
  (if (= m_type "2")
    (progn
      (setq len_m (fn_get_length "[미장] 미장할 선(선/폴리선)을 선택하세요 (다중선택 가능): "))
      
      (setq mj_t_mm (cond ((getreal "\n미장 두께(mm) 입력 <18>: ")) (18.0)))
      (setq h_m (/ (cond ((getreal "\n미장 높이(mm) <2400>: ")) (2400.0)) 1000.0))

      (setq op_data (fn_get_deduction))
      (setq op_w_m (nth 0 op_data) op_h_m (nth 1 op_data) op_ea (nth 2 op_data))

      (setq mj_area (- (* len_m h_m) (* op_w_m op_h_m op_ea)))
      (if (< mj_area 0) (setq mj_area 0.0))

      (setq mj_remital (fix (+ (* mj_area (/ mj_t_mm 20.0)) 0.999)))

      (princ "\n----------------------------------------------")
      (princ (strcat "\n[단면 미장(" (rtos mj_t_mm 2 0) "T) 산출 결과]"))
      (princ (strcat "\n- 미장 총 길이  : " (rtos len_m 2 2) " m"))
      (princ (strcat "\n- 미장 높이     : " (rtos h_m 2 2) " m"))
      (if (> op_ea 0) (princ (strcat "\n- 개구부 공제   : " (itoa op_ea) " 개소 반영 완료")))
      (princ (strcat "\n- 순 시공 면적  : " (rtos mj_area 2 2) " ㎡ (헤베)"))
      (princ (strcat "\n■ 미장용 레미탈: " (itoa mj_remital) " 포 (40kg 기준)"))
      (princ "\n==============================================")

      (fn_write_csv "미장" (rtos len_m 2 2) (rtos h_m 2 2) (rtos mj_area 2 2) "-" (strcat (itoa mj_remital) "포"))
    )
  )

  ;; ========================================================
  ;; [3번: 타일만 산출]
  ;; ========================================================
  (if (= m_type "3")
    (progn
      (initget "1 2 3 4")
      (setq t_type (getkword "\n타일 규격(부위) [1: 300x600(벽) / 2: 300x300(바닥) / 3: 600x600(벽) / 4: 600x600(바닥)] <1>: "))
      (if (null t_type) (setq t_type "1"))
      
      (cond
        ((= t_type "1") (setq t_w 0.3 t_h 0.6 t_box_pcs 8 t_name "300x600(벽)" t_part "WALL"))
        ((= t_type "2") (setq t_w 0.3 t_h 0.3 t_box_pcs 16 t_name "300x300(바닥)" t_part "FLOOR"))
        ((= t_type "3") (setq t_w 0.6 t_h 0.6 t_box_pcs 4 t_name "600x600(벽)" t_part "WALL"))
        ((= t_type "4") (setq t_w 0.6 t_h 0.6 t_box_pcs 4 t_name "600x600(바닥)" t_part "FLOOR"))
      )

      (if (= t_part "WALL")
        (progn
          (setq len_m (fn_get_length "[타일-벽] 시공 둘레 선(폴리선/라인)을 클릭하세요: "))
          (setq h_m (/ (cond ((getreal "\n타일 시공 높이(mm) <2100>: ")) (2100.0)) 1000.0))

          (setq op_data (fn_get_deduction))
          (setq op_w_m (nth 0 op_data) op_h_m (nth 1 op_data) op_ea (nth 2 op_data))

          (setq wall_area (- (* len_m h_m) (* op_w_m op_h_m op_ea)))
          (if (< wall_area 0) (setq wall_area 0.0))

          (setq tile_area (* wall_area 1.03))
          (setq total_tile_pcs (fix (+ (/ tile_area (* t_w t_h)) 0.999)))
          (setq total_boxes (fix (+ (/ tile_area (* t_w t_h t_box_pcs)) 0.999)))
          (setq tile_remital (fix (+ (* wall_area 0.55) 0.999)))

          (princ "\n----------------------------------------------")
          (princ (strcat "\n[벽 타일 산출 결과 - " t_name "]"))
          (princ (strcat "\n- 시공 총 둘레  : " (rtos len_m 2 2) " m"))
          (princ (strcat "\n- 시공 높이     : " (rtos h_m 2 2) " m"))
          (if (> op_ea 0) (princ (strcat "\n- 개구부 공제   : " (itoa op_ea) " 개소 반영 완료")))
          (princ (strcat "\n- 순 시공 면적  : " (rtos wall_area 2 2) " ㎡ (헤베)"))
          (princ (strcat "\n- 타일 주문면적 : " (rtos tile_area 2 2) " ㎡ (할증 3% 포함)"))
          (princ (strcat "\n■ 타일 박스(BOX): " (itoa total_boxes) " 박스 (" (itoa total_tile_pcs) "장)"))
          (princ (strcat "\n■ 떠붙임 레미탈: " (itoa tile_remital) " 포 (40kg 기준)"))
          (princ "\n==============================================")

          (fn_write_csv "타일(벽)" (rtos len_m 2 2) (rtos h_m 2 2) (rtos tile_area 2 2) (strcat (itoa total_boxes) "박스") (strcat (itoa tile_remital) "포"))
        )
        (progn
          (setq ss_data (fn_get_closed "[타일-바닥] 바닥 해치(HATCH) 또는 폴리선을 클릭하세요: "))
          (setq floor_area_m (/ (car ss_data) 1000000.0))
          
          (setq tile_area (* floor_area_m 1.03))
          (setq total_tile_pcs (fix (+ (/ tile_area (* t_w t_h)) 0.999)))
          (setq total_boxes (fix (+ (/ tile_area (* t_w t_h t_box_pcs)) 0.999)))
          (setq tile_remital (fix (+ (* floor_area_m 0.55) 0.999)))

          (princ "\n----------------------------------------------")
          (princ (strcat "\n[바닥 타일 산출 결과 - " t_name "]"))
          (princ (strcat "\n- 바닥 순 면적  : " (rtos floor_area_m 2 2) " ㎡ (헤베)"))
          (princ (strcat "\n- 타일 주문면적 : " (rtos tile_area 2 2) " ㎡ (할증 3% 포함)"))
          (princ (strcat "\n■ 타일 박스(BOX): " (itoa total_boxes) " 박스 (" (itoa total_tile_pcs) "장)"))
          (princ (strcat "\n■ 부자재(레미탈): " (itoa tile_remital) " 포 (면적대비 0.55 기준)"))
          (princ "\n==============================================")

          (fn_write_csv "타일(바닥)" (rtos floor_area_m 2 2) "-" (rtos tile_area 2 2) (strcat (itoa total_boxes) "박스") (strcat (itoa tile_remital) "포"))
        )
      )
    )
  )

  ;; ========================================================
  ;; [4번: 방통(바닥미장) 산출]
  ;; ========================================================
  (if (= m_type "4")
    (progn
      (setq ss_data (fn_get_closed "[방통] 바닥 해치(HATCH) 또는 폴리선을 클릭하세요 (다중선택 가능): "))
      (setq floor_area_m (/ (car ss_data) 1000000.0))
      
      (princ (strcat "\n-> 감지된 바닥 면적(헤베): " (rtos floor_area_m 2 3) " ㎡"))
      
      (setq bt_t_mm (cond ((getreal "\n방통(바닥미장) 시공 두께(mm) 입력 <50>: ")) (50.0)))
      (setq vol_m (* floor_area_m (/ bt_t_mm 1000.0)))

      ;; 레미탈: 1루베(m3) 당 약 45포 (40kg 기준)
      (setq bt_remital (fix (+ (* vol_m 45.0) 0.999)))
      
      ;; 레미콘: 1대(차) 당 6루베 기준
      (setq bt_remicon (/ vol_m 6.0))

      (princ "\n----------------------------------------------")
      (princ "\n[방통(바닥미장) 물량 산출 결과]")
      (princ (strcat "\n- 바닥 총 면적   : " (rtos floor_area_m 2 2) " ㎡ (헤베)"))
      (princ (strcat "\n- 방통 시공 두께 : " (rtos bt_t_mm 2 0) " mm"))
      (princ (strcat "\n- 방통 총 체적   : " (rtos vol_m 2 2) " ㎥ (루베)"))
      (princ (strcat "\n■ [결과1] 레미탈: " (itoa bt_remital) " 포 (40kg 기준, 1루베=45포)"))
      (princ (strcat "\n■ [결과2] 레미콘: " (rtos bt_remicon 2 1) " 대 (1대=6루베 기준)"))
      (princ "\n==============================================")

      (fn_write_csv "방통" (rtos floor_area_m 2 2) (rtos (/ bt_t_mm 1000.0) 2 3) (rtos vol_m 2 2) (strcat (itoa bt_remital) "포") (strcat (rtos bt_remicon 2 1) "대"))
    )
  )

  (princ)
)
(princ "\n[JJ 마감물량 산출 Pro 로드 완료] 실행 명령어: JJ")
(princ)
