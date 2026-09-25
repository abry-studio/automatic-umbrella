;;; ==========================================================================
;;; [뽀삐 스마트 벽체 및 조적 물량산출 자동화 LISP (Pro 2.3)]
;;; 파일명: WLS.lsp / JJ.lsp
;;;
;;; [주요 반영 사항]
;;; 1. ★벽체 순번 도면 자동 넘버링 마크 표기★ (사용자 요청 적극 반영!)
;;;    - 1번 벽체 시작점 클릭 시 그 자리에 즉시 [1] 번호 원형 마크 생성!
;;;    - 2번째 벽체 시작점 클릭 시 그 자리에 즉시 [2] 번호 원형 마크 생성!
;;;    - 벽체가 많아도 도면 위에서 1, 2, 3... 번호가 한눈에 보여 순서 혼동 0%!
;;; 2. 글자 표기 위치 사용자 직접 클릭:
;;;    - 화면 중앙 가림 방지, 원하는 빈 공간을 클릭하여 결과 텍스트 배치
;;; 3. 도면 글자는 작고 심플하게 (No, L, A, 0.5B, 1.0B 5줄, 기본 80mm)
;;; 4. 상세 산출식 및 계산 공식은 엑셀(CSV)에 수식(=C*D, =ROUNDUP, =SUM)으로 기록
;;; 5. 산출 공식: [벽체길이(m) × 벽체높이(m) = 벽체면적(㎡)] (★길이 곱하기 높이★)
;;; 6. 단축키: JJ (조적/벽돌) / WW (일반벽체) / EX (엑셀열기)
;;; ==========================================================================

(vl-load-com)

;;; --------------------------------------------------------------------------
;;; [경로 탐색] 바탕화면 뽀삐_물량집계표.csv 경로
;;; --------------------------------------------------------------------------
(defun _wls_get_csv_path (/ desk_path)
  (setq desk_path (strcat (getenv "USERPROFILE") "\\OneDrive\\Desktop"))
  (if (not (vl-file-directory-p desk_path))
    (setq desk_path (strcat (getenv "USERPROFILE") "\\OneDrive\\바탕 화면"))
  )
  (if (not (vl-file-directory-p desk_path))
    (setq desk_path (strcat (getenv "USERPROFILE") "\\Desktop"))
  )
  (if (not (vl-file-directory-p desk_path))
    (setq desk_path (strcat (getenv "USERPROFILE") "\\바탕 화면"))
  )
  (strcat desk_path "\\뽀삐_물량집계표.csv")
)

;;; --------------------------------------------------------------------------
;;; [줄 수 계산] CSV 파일의 현재 줄 수 확인 (엑셀 수식 행 번호 매칭용)
;;; --------------------------------------------------------------------------
(defun _wls_count_csv_lines (csv_path / f cnt line)
  (setq cnt 0)
  (if (and csv_path (findfile csv_path))
    (progn
      (setq f (open csv_path "r"))
      (if f
        (progn
          (while (setq line (read-line f))
            (setq cnt (1+ cnt))
          )
          (close f)
        )
      )
    )
  )
  cnt
)

;;; --------------------------------------------------------------------------
;;; [헤더 검사] 기존 CSV 파일이 신규 수식 포맷인지 확인
;;; --------------------------------------------------------------------------
(defun _wls_check_csv_header (csv_path / f first_line)
  (setq first_line nil)
  (if (and csv_path (findfile csv_path))
    (progn
      (setq f (open csv_path "r"))
      (if f
        (progn
          (setq first_line (read-line f))
          (close f)
        )
      )
    )
  )
  (if (and first_line (vl-string-search "산출식" first_line))
    t
    nil
  )
)

;;; --------------------------------------------------------------------------
;;; [CSV 저장] 엑셀 수식(=C*D, =ROUNDUP, =SUM) 및 산출식 텍스트 기록
;;; --------------------------------------------------------------------------
(defun _wls_write_csv (rows_list is_brick / base_path csv_path file cur_time cur_time_tag
                                            existing_lines cur_excel_row start_excel_row end_excel_row
                                            r_no r_h r_len r_area r_b05 r_b10
                                            formula_area_txt formula_area_excel
                                            formula_b05_txt formula_b05_excel
                                            formula_b10_txt formula_b10_excel gubun_txt)
  (setq base_path (_wls_get_csv_path))
  (setq csv_path base_path)

  ;; 기존 파일이 구버전 헤더(산출식 미포함)일 경우 백업 파일로 이름 변경 후 신규 생성
  (if (and (findfile csv_path)
           (> (vl-file-size csv_path) 0)
           (not (_wls_check_csv_header csv_path)))
    (vl-file-rename csv_path (vl-string-subst "_구버전백업.csv" ".csv" csv_path))
  )

  ;; 파일 열기 (열려있으면 타임스탬프 백업 파일 생성)
  (setq file (open csv_path "a"))
  (if (null file)
    (progn
      (setq cur_time_tag (menucmd "M=$(edtime,$(getvar,date),HHMMSS)"))
      (setq csv_path (vl-string-subst (strcat "_작업_" cur_time_tag ".csv") ".csv" base_path))
      (setq file (open csv_path "w"))
      (if file
        (princ (strcat "\n>> [안내] 기존 엑셀이 열려 있어 [" (vl-filename-base csv_path) ".csv] 로 안전하게 저장합니다!"))
      )
    )
  )

  (if file
    (progn
      (close file)
      (setq existing_lines (_wls_count_csv_lines csv_path))
      (setq file (open csv_path "a"))

      ;; 첫 작성이면 헤더 작성
      (if (= existing_lines 0)
        (progn
          (write-line "날짜/시간,구분,길이(m),높이(m),산출식(수식),면적(m2),0.5B 산식,0.5B 수량(매),1.0B 산식,1.0B 수량(매)" file)
          (setq cur_excel_row 2)
        )
        (setq cur_excel_row (1+ existing_lines))
      )

      (setq start_excel_row cur_excel_row)
      (setq cur_time (menucmd "M=$(edtime,$(getvar,date),YYYY-MO-DD HH:MM)"))

      ;; 데이터 행들 기록
      (foreach row rows_list
        (setq r_no   (itoa (nth 0 row)))
        (setq r_h    (rtos (nth 1 row) 2 2))
        (setq r_len  (rtos (nth 2 row) 2 2))
        (setq r_area (rtos (nth 3 row) 2 2))
        (setq r_b05  (itoa (nth 4 row)))
        (setq r_b10  (itoa (nth 5 row)))

        ;; 산출식 텍스트 및 엑셀 수식 생성 (엑셀에서만 상세 표기)
        (setq formula_area_txt   (strcat r_len " * " r_h))
        (setq formula_area_excel (strcat "=C" (itoa cur_excel_row) "*D" (itoa cur_excel_row)))

        (if is_brick
          (progn
            (setq formula_b05_txt   (strcat r_area " * 75"))
            (setq formula_b05_excel (strcat "\"=ROUNDUP(F" (itoa cur_excel_row) "*75, 0)\""))
            (setq formula_b10_txt   (strcat r_area " * 149"))
            (setq formula_b10_excel (strcat "\"=ROUNDUP(F" (itoa cur_excel_row) "*149, 0)\""))
            (setq gubun_txt (strcat "조적(No." r_no ")"))
          )
          (progn
            (setq formula_b05_txt "-")
            (setq formula_b05_excel "-")
            (setq formula_b10_txt "-")
            (setq formula_b10_excel "-")
            (setq gubun_txt (strcat "벽체(No." r_no ")"))
          )
        )

        (write-line
          (strcat cur_time ","
                  gubun_txt ","
                  r_len ","
                  r_h ","
                  formula_area_txt ","
                  formula_area_excel ","
                  formula_b05_txt ","
                  formula_b05_excel ","
                  formula_b10_txt ","
                  formula_b10_excel)
          file
        )
        (setq cur_excel_row (1+ cur_excel_row))
      )

      ;; 세대 합계 행 기록
      (setq end_excel_row (1- cur_excel_row))

      (if is_brick
        (write-line
          (strcat cur_time ","
                  "조적(세대합계),"
                  "\"=SUM(C" (itoa start_excel_row) ":C" (itoa end_excel_row) ")\","
                  "-,"
                  "면적합계(SUM),"
                  "\"=SUM(F" (itoa start_excel_row) ":F" (itoa end_excel_row) ")\","
                  "0.5B 총수량,"
                  "\"=SUM(H" (itoa start_excel_row) ":H" (itoa end_excel_row) ")\","
                  "1.0B 총수량,"
                  "\"=SUM(J" (itoa start_excel_row) ":J" (itoa end_excel_row) ")\"")
          file
        )
        (write-line
          (strcat cur_time ","
                  "벽체(세대합계),"
                  "\"=SUM(C" (itoa start_excel_row) ":C" (itoa end_excel_row) ")\","
                  "-,"
                  "면적합계(SUM),"
                  "\"=SUM(F" (itoa start_excel_row) ":F" (itoa end_excel_row) ")\","
                  "-,"
                  "-,"
                  "-,"
                  "-")
          file
        )
      )

      ;; 회차 간 구분을 위한 빈 줄 삽입
      (write-line "" file)
      (close file)
      (princ (strcat "\n>> [엑셀 연동 완료] 바탕화면 [" (vl-filename-base csv_path) ".csv] 에 수식 포함 저장 완료!"))
      csv_path
    )
    (progn
      (princ "\n>> [오류] CSV 파일에 쓸 수 없습니다. 엑셀 창을 닫아주세요.")
      nil
    )
  )
)

;;; --------------------------------------------------------------------------
;;; [루틴] 벽체 순번 넘버링 마크 (하늘색 원 + 노란색 번호) 도면 표기 엔진
;;; --------------------------------------------------------------------------
(defun _wls_draw_wall_node (pt num th / r_rad t_ht)
  (setq r_rad (* th 0.45))
  (setq t_ht  (* th 0.50))
  ;; 1. 하늘색(4번) 원 (식별성 극대화)
  (entmake (list '(0 . "CIRCLE")
                 (cons 10 pt)
                 (cons 40 r_rad)
                 '(62 . 4)))
  ;; 2. 노란색(2번) 중앙 정렬 순번 숫자
  (entmake (list '(0 . "TEXT")
                 (cons 10 pt)
                 (cons 11 pt)
                 (cons 40 t_ht)
                 (cons 1 (itoa num))
                 (cons 7 (getvar "TEXTSTYLE"))
                 '(62 . 2)
                 '(72 . 1)
                 '(73 . 2)))
)

;;; --------------------------------------------------------------------------
;;; [루틴] 화면에 깔끔하게 여러 줄 글자(MTEXT / TEXT) 쓰기 엔진
;;; --------------------------------------------------------------------------
(defun _wls_make_mtext (pt txt th / doc space obj res lines str cur_y idx p line mtxt)
  (vl-load-com)
  (setq doc (vla-get-activedocument (vlax-get-acad-object)))
  (setq space (if (= (getvar "cvport") 1) (vla-get-paperspace doc) (vla-get-modelspace doc)))

  ;; \n 을 MTEXT 표준 단락구분자 \P 로 안전 변환
  (setq mtxt txt)
  (while (vl-string-search "\n" mtxt)
    (setq mtxt (vl-string-subst "\\P" "\n" mtxt))
  )

  ;; 1차 시도: ActiveX vla-addmtext (가장 깔끔한 여러 줄 문자)
  (setq res (vl-catch-all-apply
              'vla-addmtext
              (list space (vlax-3d-point pt) 0.0 mtxt)))

  (if (and res (not (vl-catch-all-error-p res)))
    (progn
      (vl-catch-all-apply 'vla-put-height (list res th))
      (vl-catch-all-apply 'vla-put-attachmentpoint (list res 5)) ; 5 = Middle Center
      (vl-catch-all-apply 'vla-put-insertionpoint (list res (vlax-3d-point pt)))
      (vl-catch-all-apply 'vla-put-color (list res 2)) ; 노란색(2번)
      res
    )
    ;; 2차 시도: 일반 TEXT로 줄 단위 분할 출력 (어떤 캐드에서도 절대 겹침 없음)
    (progn
      (setq lines '() str txt)
      (while (setq idx (vl-string-search "\n" str))
        (setq lines (append lines (list (substr str 1 idx))))
        (setq str (substr str (+ idx 2)))
      )
      (if (> (strlen str) 0) (setq lines (append lines (list str))))
      (if (null lines) (setq lines (list txt)))

      (setq cur_y (+ (cadr pt) (* (/ (1- (length lines)) 2.0) (* th 1.35))))
      (foreach line lines
        (setq p (list (car pt) cur_y (caddr pt)))
        (entmake (list '(0 . "TEXT")
                       (cons 10 p)
                       (cons 11 p)
                       (cons 40 th)
                       (cons 1 line)
                       (cons 7 (getvar "TEXTSTYLE"))
                       '(62 . 2)
                       '(72 . 1)
                       '(73 . 2)))
        (setq cur_y (- cur_y (* th 1.35)))
      )
      t
    )
  )
)

;;; --------------------------------------------------------------------------
;;; [루틴] 산출된 벽체 궤적선(자홍색 폴리선) 화면 그리기
;;; --------------------------------------------------------------------------
(defun _wls_draw_pline (pts th / ent_data)
  (if (>= (length pts) 2)
    (progn
      (setq ent_data (list '(0 . "LWPOLYLINE")
                           '(100 . "AcDbEntity")
                           '(100 . "AcDbPolyline")
                           (cons 90 (length pts))
                           '(70 . 0)
                           '(62 . 6)            ; 선명한 자홍색(Magenta)
                           (cons 43 (/ th 8.0)))) ; 식별하기 좋은 선 두께
      (foreach p pts
        (setq ent_data (append ent_data (list (cons 10 (list (car p) (cadr p))))))
      )
      (entmake ent_data)
    )
  )
)

;;; --------------------------------------------------------------------------
;;; [캐드 표 그리기] Table 객체 및 범용 선+문자 벡터표 2중 엔진
;;; --------------------------------------------------------------------------
(defun _wls_draw_cad_table (pt rows_list is_brick th / doc space num_rows num_cols tbl r
                                                      tot_len tot_area tot_b05 tot_b10 item)
  (vl-load-com)
  (setq doc (vla-get-activedocument (vlax-get-acad-object)))
  (setq space (if (= (getvar "cvport") 1) (vla-get-paperspace doc) (vla-get-modelspace doc)))

  (setq num_rows (+ (length rows_list) 3)) ; 제목(0) + 헤더(1) + 데이터 + 합계
  (setq num_cols (if is_brick 6 4))

  (setq tbl (vl-catch-all-apply
              'vla-addtable
              (list space (vlax-3d-point pt) num_rows num_cols (* th 2.4) (* th 7.5))))

  (if (and tbl (not (vl-catch-all-error-p tbl)))
    (progn
      ;; 제목
      (vla-settext tbl 0 0 (if is_brick "조적(벽돌) 물량 집계표" "벽체 물량 집계표"))

      ;; 헤더
      (vla-settext tbl 1 0 "번호")
      (vla-settext tbl 1 1 "길이(m)")
      (vla-settext tbl 1 2 "높이(m)")
      (vla-settext tbl 1 3 "면적(m2)")
      (if is_brick
        (progn
          (vla-settext tbl 1 4 "0.5B (75매/m2)")
          (vla-settext tbl 1 5 "1.0B (149매/m2)")
        )
      )

      ;; 데이터 행
      (setq r 2)
      (setq tot_len 0.0 tot_area 0.0 tot_b05 0 tot_b10 0)
      (foreach item rows_list
        (vla-settext tbl r 0 (strcat "No." (itoa (nth 0 item))))
        (vla-settext tbl r 1 (rtos (nth 2 item) 2 2))
        (vla-settext tbl r 2 (rtos (nth 1 item) 2 2))
        (vla-settext tbl r 3 (rtos (nth 3 item) 2 2))

        (setq tot_len (+ tot_len (nth 2 item)))
        (setq tot_area (+ tot_area (nth 3 item)))

        (if is_brick
          (progn
            (vla-settext tbl r 4 (strcat (itoa (nth 4 item)) "매"))
            (vla-settext tbl r 5 (strcat (itoa (nth 5 item)) "매"))
            (setq tot_b05 (+ tot_b05 (nth 4 item)))
            (setq tot_b10 (+ tot_b10 (nth 5 item)))
          )
        )
        (setq r (1+ r))
      )

      ;; 합계 행
      (vla-settext tbl r 0 "합계")
      (vla-settext tbl r 1 (strcat (rtos tot_len 2 2) "m"))
      (vla-settext tbl r 2 "-")
      (vla-settext tbl r 3 (strcat (rtos tot_area 2 2) "m2"))
      (if is_brick
        (progn
          (vla-settext tbl r 4 (strcat (itoa tot_b05) "매"))
          (vla-settext tbl r 5 (strcat (itoa tot_b10) "매"))
        )
      )
      (princ "\n>> [완료] 캐드 화면에 엑셀 집계표가 성공적으로 그려졌습니다!")
    )
    ;; Table 객체가 지원되지 않는 캐드 환경: 선과 문자로 직접 그리는 백업 벡터표
    (_wls_draw_vector_table pt rows_list is_brick th)
  )
)

;;; --------------------------------------------------------------------------
;;; [백업 표 그리기] 선(Line)과 문자(Text)로 100% 호환되는 격자표 작성
;;; --------------------------------------------------------------------------
(defun _wls_draw_vector_table (pt rows_list is_brick th / col_w_list cols_cnt rows_cnt total_w total_h row_h
                                                          x0 y0 cur_x cur_y r c item tot_len tot_area tot_b05 tot_b10
                                                          x_lines x_centers headers)
  (setq row_h (* th 2.4))
  (setq col_w_list (if is_brick
                     (list (* th 5.5) (* th 6.0) (* th 6.0) (* th 6.5) (* th 7.5) (* th 7.5))
                     (list (* th 5.5) (* th 6.0) (* th 6.0) (* th 6.5))))
  (setq cols_cnt (length col_w_list))
  (setq rows_cnt (+ (length rows_list) 3))

  ;; 전체 가로/세로 크기 및 열별 X 좌표 계산
  (setq total_w 0.0)
  (setq x0 (car pt) y0 (cadr pt))
  (setq x_lines (list x0))
  (foreach w col_w_list
    (setq total_w (+ total_w w))
    (setq x_lines (append x_lines (list (+ x0 total_w))))
  )
  (setq total_h (* row_h rows_cnt))

  ;; 각 열 중앙 X 좌표 계산
  (setq x_centers '() c 0)
  (while (< c cols_cnt)
    (setq x_centers (append x_centers (list (/ (+ (nth c x_lines) (nth (1+ c) x_lines)) 2.0))))
    (setq c (1+ c))
  )

  ;; 1. 가로 격자선
  (setq r 0)
  (while (<= r rows_cnt)
    (setq cur_y (- y0 (* r row_h)))
    (entmake (list '(0 . "LINE") (cons 10 (list x0 cur_y 0.0)) (cons 11 (list (+ x0 total_w) cur_y 0.0)) '(62 . 4)))
    (setq r (1+ r))
  )

  ;; 2. 세로 격자선
  (setq c 0)
  (while (<= c cols_cnt)
    (setq cur_x (nth c x_lines))
    (setq cur_y (if (= c 0) y0 (if (= c cols_cnt) y0 (- y0 row_h))))
    (entmake (list '(0 . "LINE") (cons 10 (list cur_x cur_y 0.0)) (cons 11 (list cur_x (- y0 total_h) 0.0)) '(62 . 4)))
    (setq c (1+ c))
  )

  ;; 3. 제목 텍스트
  (entmake (list '(0 . "TEXT")
                 (cons 10 (list (+ x0 (/ total_w 2.0)) (- y0 (* row_h 0.5)) 0.0))
                 (cons 11 (list (+ x0 (/ total_w 2.0)) (- y0 (* row_h 0.5)) 0.0))
                 (cons 40 (* th 1.2))
                 (cons 1 (if is_brick "조적(벽돌) 물량 집계표" "벽체 물량 집계표"))
                 (cons 7 (getvar "TEXTSTYLE"))
                 '(62 . 2) '(72 . 1) '(73 . 2)))

  ;; 4. 헤더 텍스트
  (setq headers (if is_brick
                  (list "번호" "길이(m)" "높이(m)" "면적(m2)" "0.5B (75매)" "1.0B (149매)")
                  (list "번호" "길이(m)" "높이(m)" "면적(m2)")))
  (setq c 0)
  (foreach h headers
    (entmake (list '(0 . "TEXT")
                   (cons 10 (list (nth c x_centers) (- y0 (* row_h 1.5)) 0.0))
                   (cons 11 (list (nth c x_centers) (- y0 (* row_h 1.5)) 0.0))
                   (cons 40 th) (cons 1 h) (cons 7 (getvar "TEXTSTYLE"))
                   '(62 . 3) '(72 . 1) '(73 . 2)))
    (setq c (1+ c))
  )

  ;; 5. 데이터 행들
  (setq r 2 tot_len 0.0 tot_area 0.0 tot_b05 0 tot_b10 0)
  (foreach item rows_list
    (setq cur_y (- y0 (* (+ r 0.5) row_h)))
    (setq tot_len (+ tot_len (nth 2 item)))
    (setq tot_area (+ tot_area (nth 3 item)))
    (setq tot_b05 (+ tot_b05 (nth 4 item)))
    (setq tot_b10 (+ tot_b10 (nth 5 item)))

    (entmake (list '(0 . "TEXT") (cons 10 (list (nth 0 x_centers) cur_y 0.0)) (cons 11 (list (nth 0 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (strcat "No." (itoa (nth 0 item)))) (cons 7 (getvar "TEXTSTYLE")) '(62 . 7) '(72 . 1) '(73 . 2)))
    (entmake (list '(0 . "TEXT") (cons 10 (list (nth 1 x_centers) cur_y 0.0)) (cons 11 (list (nth 1 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (rtos (nth 2 item) 2 2)) (cons 7 (getvar "TEXTSTYLE")) '(62 . 7) '(72 . 1) '(73 . 2)))
    (entmake (list '(0 . "TEXT") (cons 10 (list (nth 2 x_centers) cur_y 0.0)) (cons 11 (list (nth 2 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (rtos (nth 1 item) 2 2)) (cons 7 (getvar "TEXTSTYLE")) '(62 . 7) '(72 . 1) '(73 . 2)))
    (entmake (list '(0 . "TEXT") (cons 10 (list (nth 3 x_centers) cur_y 0.0)) (cons 11 (list (nth 3 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (rtos (nth 3 item) 2 2)) (cons 7 (getvar "TEXTSTYLE")) '(62 . 7) '(72 . 1) '(73 . 2)))
    (if is_brick
      (progn
        (entmake (list '(0 . "TEXT") (cons 10 (list (nth 4 x_centers) cur_y 0.0)) (cons 11 (list (nth 4 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (strcat (itoa (nth 4 item)) "매")) (cons 7 (getvar "TEXTSTYLE")) '(62 . 7) '(72 . 1) '(73 . 2)))
        (entmake (list '(0 . "TEXT") (cons 10 (list (nth 5 x_centers) cur_y 0.0)) (cons 11 (list (nth 5 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (strcat (itoa (nth 5 item)) "매")) (cons 7 (getvar "TEXTSTYLE")) '(62 . 7) '(72 . 1) '(73 . 2)))
      )
    )
    (setq r (1+ r))
  )

  ;; 6. 합계 행
  (setq cur_y (- y0 (* (+ r 0.5) row_h)))
  (entmake (list '(0 . "TEXT") (cons 10 (list (nth 0 x_centers) cur_y 0.0)) (cons 11 (list (nth 0 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 "합계") (cons 7 (getvar "TEXTSTYLE")) '(62 . 1) '(72 . 1) '(73 . 2)))
  (entmake (list '(0 . "TEXT") (cons 10 (list (nth 1 x_centers) cur_y 0.0)) (cons 11 (list (nth 1 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (strcat (rtos tot_len 2 2) "m")) (cons 7 (getvar "TEXTSTYLE")) '(62 . 1) '(72 . 1) '(73 . 2)))
  (entmake (list '(0 . "TEXT") (cons 10 (list (nth 2 x_centers) cur_y 0.0)) (cons 11 (list (nth 2 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 "-") (cons 7 (getvar "TEXTSTYLE")) '(62 . 1) '(72 . 1) '(73 . 2)))
  (entmake (list '(0 . "TEXT") (cons 10 (list (nth 3 x_centers) cur_y 0.0)) (cons 11 (list (nth 3 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (strcat (rtos tot_area 2 2) "m2")) (cons 7 (getvar "TEXTSTYLE")) '(62 . 1) '(72 . 1) '(73 . 2)))
  (if is_brick
    (progn
      (entmake (list '(0 . "TEXT") (cons 10 (list (nth 4 x_centers) cur_y 0.0)) (cons 11 (list (nth 4 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (strcat (itoa tot_b05) "매")) (cons 7 (getvar "TEXTSTYLE")) '(62 . 1) '(72 . 1) '(73 . 2)))
      (entmake (list '(0 . "TEXT") (cons 10 (list (nth 5 x_centers) cur_y 0.0)) (cons 11 (list (nth 5 x_centers) cur_y 0.0)) (cons 40 th) (cons 1 (strcat (itoa tot_b10) "매")) (cons 7 (getvar "TEXTSTYLE")) '(62 . 1) '(72 . 1) '(73 . 2)))
    )
  )
  (princ "\n>> [완료] 캐드 화면에 격자 집계표가 성공적으로 그려졌습니다!")
)

;;; ==========================================================================
;;; [메인 엔진] 벽체 및 조적 물량 산출 코어 엔진
;;; ==========================================================================
(defun _wls_main_engine (is_brick / *error* old_osm old_cmdecho mode cur_num
                                    total_len len_m wall_area h_m b05_cnt b10_cnt
                                    p1 p2 pt tbl_pt out_txt input_h input_th
                                    rows_list ans_open saved_csv_path ss i ent len
                                    pts mid_pt min_pt max_pt)
  ;; 에러 처리 함수
  (defun *error* (msg)
    (if old_osm (setvar "OSMODE" old_osm))
    (if old_cmdecho (setvar "CMDECHO" old_cmdecho))
    (if (not (wcmatch (strcase msg t) "*break,*cancel*,*exit*"))
      (princ (strcat "\n오류 발생: " msg))
    )
    (princ)
  )

  (setq old_osm (getvar "OSMODE"))
  (setq old_cmdecho (getvar "CMDECHO"))
  (setvar "CMDECHO" 0)

  ;; 1. 새 세대 산출 시 항상 1번(No.1)부터 시작
  (setq cur_num 1)

  (princ "\n=======================================================")
  (princ (if is_brick
           "\n>>> [JJ 조적/벽돌 물량 산출 (길이 x 높이)] <<<"
           "\n>>> [JJ 일반 벽체 면적 산출 (길이 x 높이)] <<<"))
  (princ "\n* 계산방식: 벽체길이(m) x 벽체높이(m) = 면적(m2)")
  (if is_brick
    (princ "\n* 조적매수: 0.5B(75매/m2) | 1.0B(149매/m2)")
  )
  (princ "\n* 도면표시: 벽체 클릭 지점에 순번 마크(1, 2, 3...) 자동 표기!")
  (princ "\n=======================================================")

  ;; 2. 벽체 높이 입력 (단위세대 기본값 2600mm)
  (if (not *w_height*) (setq *w_height* 2600.0))
  (setq input_h (getdist (strcat "\n벽체 높이(mm) 입력 [단위세대: 2600] <" (rtos *w_height* 2 0) ">: ")))
  (if input_h (setq *w_height* input_h))
  (setq h_m (/ *w_height* 1000.0))

  ;; 3. 글자 크기 입력 (도면 맞춤 권장: 60~80mm, 기본값: 80mm)
  (if (or (null *w_th*) (> *w_th* 120.0)) (setq *w_th* 80.0))
  (setq input_th (getdist (strcat "\n글자 크기(문자높이 mm) 입력 [도면 권장: 60~80] <" (rtos *w_th* 2 0) ">: ")))
  (if input_th (setq *w_th* input_th))

  ;; 4. 산출 방식 (기본값 P: 점연속클릭)
  (if (not *w_mode*) (setq *w_mode* "Pick"))
  (initget "Select Pick")
  (setq mode (getkword (strcat "\n산출 방식 선택 [점연속클릭(P) / 객체선택(S)] <" (if (= *w_mode* "Pick") "P" "S") ">: ")))
  (if mode (setq *w_mode* mode))

  (setq rows_list '())

  ;; 5. 벽체 연속 산출 루프 (완료하고 싶을 땐 시작점에서 그냥 Enter 누르면 완료!)
  (while
    (progn
      (setq total_len 0.0)
      (setq pts '())
      (setq mid_pt nil)

      (if (= *w_mode* "Pick")
        ;; [P 모드: 코너 점들을 연속 클릭]
        (progn
          (setvar "OSMODE" old_osm)
          (setq p1 (getpoint (strcat "\n[" (itoa cur_num) "번 벽체] 시작점 클릭 (★완료는 Enter★): ")))
          (if p1
            (progn
              (setq pts (list p1))
              ;; ★ 사용자가 클릭한 바로 그 자리에 1, 2, 3... 순번 원형 마크 즉시 표기!
              (_wls_draw_wall_node p1 cur_num *w_th*)

              (while (setq p2 (getpoint p1 "\n다음 점 클릭 (완료 시 Enter): "))
                (setq total_len (+ total_len (distance p1 p2)))
                (setq pts (append pts (list p2)))
                (setq p1 p2)
              )
            )
          )
        )
        ;; [S 모드: 도면의 선들을 드래그로 선택]
        (progn
          (prompt (strcat "\n[" (itoa cur_num) "번 벽체] 합산할 선들을 드래그로 선택 (★완료는 Enter★): "))
          (setq ss (ssget '((0 . "LINE,LWPOLYLINE,POLYLINE,ARC,SPLINE"))))
          (if ss
            (progn
              (setq i 0)
              (repeat (sslength ss)
                (setq ent (ssname ss i))
                (setq len (vl-catch-all-apply 'vlax-curve-getDistAtParam (list ent (vlax-curve-getEndParam ent))))
                (if (and len (not (vl-catch-all-error-p len)))
                  (setq total_len (+ total_len len))
                )
                (if (= i 0)
                  (progn
                    (vla-getboundingbox (vlax-ename->vla-object ent) 'min_pt 'max_pt)
                    (setq mid_pt (mapcar '/ (mapcar '+ (vlax-safearray->list min_pt) (vlax-safearray->list max_pt)) '(2.0 2.0 2.0)))
                    ;; S 모드에서도 선택한 벽체 중앙에 순번 번호 마크 즉시 표기!
                    (_wls_draw_wall_node mid_pt cur_num *w_th*)
                  )
                )
                (setq i (1+ i))
              )
            )
          )
        )
      )

      ;; 길이가 산출된 경우 화면에 산출선 및 글자 표기 (★길이 곱하기 높이★)
      (if (> total_len 0.0)
        (progn
          (setq len_m (/ total_len 1000.0))
          (setq wall_area (* len_m h_m))
          (setq b05_cnt (fix (+ (* wall_area 75.0) 0.9999)))
          (setq b10_cnt (fix (+ (* wall_area 149.0) 0.9999)))

          ;; 1. 화면에 산출된 벽체 궤적선(자홍색) 그리기
          (if (= *w_mode* "Pick")
            (_wls_draw_pline pts *w_th*)
          )

          ;; 2. 산출 데이터 리스트에 추가
          (setq rows_list (append rows_list (list (list cur_num h_m len_m wall_area b05_cnt b10_cnt))))

          ;; 3. 표기 텍스트 생성 (도면에는 예전처럼 깔끔하고 심플하게 표기!)
          (if is_brick
            (setq out_txt (strcat "No." (itoa cur_num)
                                  "\nL: " (rtos len_m 2 2) "m"
                                  "\nA: " (rtos wall_area 2 2) "m2 (H:" (rtos h_m 2 1) "m)"
                                  "\n[0.5B] " (itoa b05_cnt) "매"
                                  "\n[1.0B] " (itoa b10_cnt) "매"))
            (setq out_txt (strcat "No." (itoa cur_num)
                                  "\nL: " (rtos len_m 2 2) "m"
                                  "\nA: " (rtos wall_area 2 2) "m2"
                                  " (H:" (rtos h_m 2 1) "m)"))
          )

          ;; 4. 글자 표기 위치를 사용자가 원하는 빈 공간에 직접 마우스로 클릭할 때까지 대기!
          ;;    (엔터 실수로 화면 가운데에 자동 배치되어 도면을 가리는 현상 원천 차단)
          (setvar "OSMODE" old_osm)
          (setq pt nil)
          (while (null pt)
            (setq pt (getpoint (strcat "\n>> [" (itoa cur_num) "번 벽체 결과 글자]를 표기할 위치를 마우스로 클릭하세요 (원하는 빈 공간 클릭): ")))
          )
          (if pt
            (progn
              (_wls_make_mtext pt out_txt *w_th*)
              (princ (strcat "\n>> [" (itoa cur_num) "번 벽체 글자 표기 완료!]"))
            )
          )

          (setq cur_num (1+ cur_num))
          t ; 다음 벽체로 계속 진행!
        )
        nil ; 시작점에서 Enter를 치면 루프 종료!
      )
    )
  )

  ;; 6. 산출 완료 후 처리 (캐드 집계표 작성 & 엑셀 수식 연동 저장 & 자동 팝업)
  (if (> (length rows_list) 0)
    (progn
      (princ (strcat "\n>> [산출 완료] 총 " (itoa (length rows_list)) "개 벽체가 산출되었습니다."))

      ;; A. 캐드 도면 화면에 [엑셀 집계표] 그리기
      (setvar "OSMODE" 0)
      (setq tbl_pt (getpoint "\n>> 캐드 화면에 [엑셀 집계표]를 그릴 위치 클릭 (생략 시 Enter): "))
      (if tbl_pt
        (_wls_draw_cad_table tbl_pt rows_list is_brick *w_th*)
      )
      (setvar "OSMODE" old_osm)

      ;; B. 엑셀(CSV) 파일에 수식 포함 자동 연동 저장
      (setq saved_csv_path (_wls_write_csv rows_list is_brick))

      ;; C. 실제 엑셀 프로그램 바로 열기
      (if saved_csv_path
        (progn
          (initget "Yes No")
          (setq ans_open (getkword "\n>> 실제 엑셀(Excel) 프로그램을 바로 여시겠습니까? [예(Y) / 아니오(N)] <Y>: "))
          (if (or (null ans_open) (= ans_open "Yes"))
            (startapp "explorer.exe" saved_csv_path)
          )
        )
      )
    )
    (princ "\n>> 산출된 벽체가 없습니다.")
  )

  (setvar "OSMODE" old_osm)
  (setvar "CMDECHO" old_cmdecho)
  (princ "\n산출이 완료되었습니다. (다음 세대 산출 시 다시 1번부터 시작됩니다!)")
  (princ)
)


;;; ==========================================================================
;;; [명령어 등록 - 초스피드 단축키 (재귀 방지 직접 호출)]
;;; ==========================================================================

;; 1. 조적/벽돌 물량 산출 (메인 단축키 JJ: 길이 x 높이 = 면적 + 벽돌 매수)
(defun c:JJ   () (_wls_main_engine t))
(defun c:WB   () (_wls_main_engine t))
(defun c:WBS  () (_wls_main_engine t))
(defun c:ㅓㅓ () (_wls_main_engine t))
(defun c:물량 () (_wls_main_engine t))
(defun c:조적 () (_wls_main_engine t))
(defun c:벽돌 () (_wls_main_engine t))
(defun c:조   () (_wls_main_engine t))
(defun c:4    () (_wls_main_engine t))

;; 2. 일반 벽체 산출 (길이 x 높이 = 면적)
(defun c:WW   () (_wls_main_engine nil))
(defun c:WLS  () (_wls_main_engine nil))
(defun c:WS   () (_wls_main_engine nil))
(defun c:ㅈㅈ () (_wls_main_engine nil))
(defun c:벽체 () (_wls_main_engine nil))
(defun c:벽   () (_wls_main_engine nil))
(defun c:3    () (_wls_main_engine nil))

;; 3. 엑셀(CSV) 파일 바로 열기 (EX / XL / 엑셀)
(defun c:EX (/ csv_path)
  (setq csv_path (_wls_get_csv_path))
  (if (findfile csv_path)
    (progn
      (startapp "explorer.exe" csv_path)
      (princ (strcat "\n>> [완료] 물량 집계표를 열었습니다: " csv_path "\n"))
    )
    (princ "\n>> [안내] 아직 저장된 물량 집계표가 없습니다. 산출(JJ 또는 WW)을 먼저 진행하세요!\n")
  )
  (princ)
)
(defun c:XL   () (c:EX))
(defun c:엑셀 () (c:EX))
(defun c:ㄷㅌ () (c:EX))

(princ "\n[뽀삐 물량산출 로드 완료] 조적/벽돌: JJ (또는 WB, 4) | 일반벽체: WW (또는 3) | 엑셀열기: EX, XL")
(princ)
