;;;
;;;
;;; 아키모아.2013.08.24.
;;;
;;;
;;; CTB, PRINTER, PAPER 설정
;;;
;;; 이 부분의 변수 ctb_file, prt_name, paper_size 에 ctb파일이름,프린터설정세이브파일이름,용지설정이름으로 
;;; 대체한후 AutoCAD에서 로드하여야 한다.
;;; 
;;;

;Plot Device 설정
(setq prt_name "도마동현장.pc3")		;; 프린터 이름 설정
(setq ctb_file "monochrome.ctb")				;; 펜 설정
(setq paper_size "A3")						;; 용지 설정

;PDF Device 설정: ACAD2012
(setq pdf_prt_name "DWG To PDF.pc3")				;; 프린터 이름 설정
(setq pdf_ctb_file "monochrome.ctb")				;; 펜 설정
(setq pdf_paper_size "ISO_full_bleed_A3_(297.00_x_420.00_MM)")	;; 용지 설정

;출력용 Layer명 지정(PLOTBOX)
(setq #PlotClayer "0")		;;플롯용 박스 기본 레이어 설정 (Default: "0")
(setq #PlotColor 2)		;;플롯용 박스 색상 설정 (Default: nil)

;;;
;;; PLOT 설정값 확인
;;;
;;; 평소 사용하는 환경으로 PLOT설정을 배치에 적용한 뒤,
;;; PLOTNAME 명령으로 위의 값을 확인할 수 있다.
;;;

(defun c:PLOTNAME ()
(princ "\n플로터 이름: ") (prin1 (vla-get-ConfigName LayObj))
(princ "\n용지 이름: ") (prin1 (vla-get-CanonicalMediaName LayObj))
(princ "\n펜 이름: ") (prin1 (vla-get-StyleSheet LayObj))
(princ "\n")(princ)
)

;;;
;;;
;;; 출력 명령어 설정
;;; C:OOO 를 원하는 명령으로 바꾼다.
;;;
;;; -기본 명령어-
;;; PX: 박스로 된 도면외각을 선택하여 출력한다.
;;; PXX: 도면 전체를 출력한다.
;;; RV: 도면 출력과 동일하게 미리보기를 한다.
;;; PI: 블록으로 된 도면외각을 출력한다.
;;; PB: PLOT 전용 사각박스를 생성한다.
;;; PDF: 박스로 된 도면외각을 PDF파일로 출력한다.
;;; PDI: 블록으로 된 도면외각을 PDF파일로 출력한다.
;;;
;;;

(defun C:PX () (prompt (strcat "PLOTEXPRESS\n출력할 도면 선택...")) (#PLOT_EXPRESS "Plot_Mode"))
(defun C:PXX () (prompt (strcat "PLOTEXPRESSALL\nPLOT전용 LAYER 전체 출력...")) (#PLOT_EXPRESS "AP_Mode"))
(defun C:RV () (prompt (strcat "DREVIEW\n미리보기 할 도면 선택...")) (#PLOT_EXPRESS "RV_Mode"))
(defun C:PI () (prompt (strcat "PLOTINSERTBLOCK\n출력할 블록 선택...")) (#PLOT_EXPRESS "Block_Mode"))
(defun C:PB () (prompt (strcat "PLOTBOX\nPLOT전용 BOX 생성...")) (c:PLOTBOX))
(defun C:PDF () (prompt (strcat "PDFOUT\nBOX를 PDF로 내보내기...")) (#PLOT_EXPRESS "PDF_Mode"))
(defun C:PDI () (prompt (strcat "PDFBLOCKOUT\n블록을 PDF로 내보내기...")) (#PLOT_EXPRESS "PDFi_Mode"))

;;;
;;;
;;; 도면 Open 시 자동으로 플로터 확인
;;;
;;;

(vl-load-com)
(setq LayObj (vla-get-ActiveLayout (vla-get-ActiveDocument (vlax-get-acad-object))))

(and
  (or
    (and
      (member prt_name (vlax-safearray->list (vlax-variant-value (vla-GetPlotDeviceNames LayObj))))
      (member ctb_file (vlax-safearray->list (vlax-variant-value (vla-GetPlotStyleTableNames LayObj))))
      ;;(member paper_size (vlax-safearray->list (vlax-variant-value (vla-GetCanonicalMediaNames LayObj))))
    )
    (prompt "\nLISP: 플롯 설정값이 올바르지 않음. PLOTNAME 명령으로 현재 설정값을 확인하십시오.")
  )
  (or
    (/= (vla-get-ConfigName LayObj) prt_name)
    (/= (vla-get-StyleSheet LayObj) ctb_file)
    (/= (vla-get-CanonicalMediaName LayObj) paper_size)
  )
  (progn
    (vla-put-ConfigName LayObj prt_name)
    (vla-put-StyleSheet LayObj ctb_file)
    (vla-put-CanonicalMediaName LayObj paper_size)
  )
)

;;;
;;;
;;; 도면 Open 시 자동으로 UCS 초기화
;;;
;;;

(if (= (getvar "worlducs") 0) (and (setvar "cmdecho" 0) (vl-cmdf "UCS" "") (setvar "cmdecho" 1) (prompt (strcat "\n **UCS Initialized** "))))

;;;
;;;
;;;    플롯박스 만들기
;;;
;;; CLA에 해당하는 layer에 4각 폴리곤을 작성한다.
;;; 해당 layer가 없을 경우 자동으로 작성한다.
;;; 4각 폴리곤을 도면폼 외곽에 씌우면 차후에 일괄출력에 활용가능하다.
;;;
;;;

(defun c:PLOTBOX ( / COL CLA pt)
(if (= (getvar "worlducs") 0) (and (setvar "cmdecho" 0) (vl-cmdf "UCS" "") (setvar "cmdecho" 1)))
(setq CLA #PlotClayer)
(setq COL #PlotColor)
(if (= nil (tblsearch "layer" CLA))
  (entmake (list (cons 0 "LAYER") (cons 100 "AcDbSymbolTableRecord") (cons 100 "AcDbLayerTableRecord")
		 (cons 2 CLA) (cons 6 "CONTINUOUS") (cons 62 2) (cons 70 0)
	   )
  )
)
(and (setq pt (getpoint "첫 번째 구석점 지정: "))
     (cadr (setq pt (list pt (getcorner pt "다른 구석점 지정: "))))
     (setq pt (list (list (caar pt) (caadr pt)) (list (cadar pt) (cadadr pt))))
)
(if (= (length pt) 2)
  (entmake 
    (vl-remove-if 'not
	(list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 CLA)
	      (if COL (cons 62 COL)) (cons 100 "AcDbPolyline") (cons 90 4) (cons 70 1)
	      (cons 10 (list (apply 'min (car pt)) (apply 'min (cadr pt))))
	      (cons 10 (list (apply 'max (car pt)) (apply 'min (cadr pt))))
	      (cons 10 (list (apply 'max (car pt)) (apply 'max (cadr pt))))
	      (cons 10 (list (apply 'min (car pt)) (apply 'max (cadr pt))))
	)
    )
  )
)(princ)
)

;;;
;;;
;;;    박스 정렬
;;;
;;; 박스를 선택한 순서를 기준으로 x축 방향으로 재정렬한다.
;;;
;;;

(defun PTE:highlight (ss x) (mapcar '(lambda (ent)(redraw ent x)) (vl-remove-if 'listp (mapcar 'cadr (ssnamex ss)))))

(defun #SS_Sort_Sub (ss / n buffer ss_lst)
(setq n (cadddr (car (ssnamex ss))))
(foreach x (ssnamex ss)
  (if (equal n (cadddr x))
    (setq buffer (append buffer (list (cadr x))))
    (setq ss_lst (append ss_lst (list (list n buffer))) n (cadddr x) buffer (list (cadr x)))
  )
)
(setq ss_lst (vl-remove-if '(lambda (x) (listp (car (cadr x)))) (append ss_lst (list (list n buffer)))))
ss_lst
)


(defun #SS_Sort_Main (ss / SortSS MinPt MaxPt MinPtB MaxPtB)
(setq SortSS (ssadd))
(foreach x (#SS_Sort_Sub ss)
  (if (= (length (cadr x)) 1)
    (ssadd (car (cadr x)) SortSS)
    (mapcar '(lambda (f) (ssadd f SortSS))
      (vl-sort (cadr x)
	'(lambda (a b)
	 (if
	  (equal 
	    (cadr (progn (vla-GetBoundingBox (vlax-ename->vla-object a) 'MinPt 'MaxPt) (vlax-safearray->list MinPt)))
	    (cadr (progn (vla-GetBoundingBox (vlax-ename->vla-object b) 'MinPtB 'MaxPtB) (vlax-safearray->list MinPtB)))
	    40.0
	  )
	  (< (car (vlax-safearray->list MinPt)) (car (vlax-safearray->list MinPtB)))
	  (> (cadr (vlax-safearray->list MinPt)) (cadr (vlax-safearray->list MinPtB)))
	 )
	)
      )
    )
  )
)SortSS
)

(defun List->Safearray (lst) (vlax-safearray-fill (vlax-make-safearray vlax-vbdouble (cons 0 (1- (length lst)))) lst))

(defun #BoxReaction (ss SF_List / en n MinPt MaxPt ns nb)
(repeat (setq n (sslength ss))
  (and
    (setq en (ssname ss (setq n (1- n))))
    (progn
      (command "zoom" "object" en "")
      (vla-GetBoundingBox (vlax-ename->vla-object en) 'MinPt 'MaxPt)
      (setq MinPt (vlax-safearray->list MinPt) MaxPt (vlax-safearray->list MaxPt))
      (if (> 70 (distance MinPt MaxPt))
	(ssdel en ss)
	(if (setq nb 0 ns (ssget "w" MinPt MaxPt SF_List))
	  (progn (ssdel en ns) (repeat (sslength ns) (ssdel (ssname ns nb) ss) (setq nb (1+ nb))))
	)
      )
    )
  )
)ss
)

;;;
;;;   PDF 넘버링
;;;
;;; PDF파일의 넘버를 증가하거나 감소한다.
;;;
;;;

(defun $PDF_NUM_ADD ( / n TXT1 TXT2 FN F1 F2)
(setq n 0
      TXT1
        (vl-list->string
	  (reverse
	    (vl-remove-if '(lambda (f) (= 0 (if (= f 92) (setq n nil) n))) (reverse (vl-string->list #PDF_Filename)))
	  )
        )
      TXT2 (substr #PDF_Filename (1+ (strlen TXT1)))
      FN (substr TXT2 1 (- (setq n (strlen TXT2)) 4))
)
(if (< 4 n)
  (progn
    (setq n 0
	  F2 (reverse (vl-remove-if '(lambda (f) (= nil (if (or (< f 48) (> f 57)) (setq n nil) n))) (reverse (vl-string->list FN))))
	  F1 (substr FN 1 (- (strlen FN) (length F2)))
    )
    (setq F2 (vl-string->list (itoa (fix (1+ (atoi (vl-list->string F2)))))))
    (if (> 3 (length F2)) (while (> 3 (length F2)) (setq F2 (append (list 48) F2))))
    (setq F2 (vl-list->string F2) FN (strcat F1 F2))
  )
  (setq FN (strcat FN "001"))
)(setq #PDF_Filename (strcat TXT1 FN ".pdf"))#PDF_Filename
)


(defun $PDF_NUM_MINUS ( / n TXT1 TXT2 FN F1 F2)
(setq n 0
      TXT1
        (vl-list->string
	  (reverse
	    (vl-remove-if '(lambda (f) (= 0 (if (= f 92) (setq n nil) n))) (reverse (vl-string->list #PDF_Filename)))
	  )
        )
      TXT2 (substr #PDF_Filename (1+ (strlen TXT1)))
      FN (substr TXT2 1 (- (setq n (strlen TXT2)) 4))
)
(if (< 4 n)
  (progn
    (setq n 0
	  F2 (reverse (vl-remove-if '(lambda (f) (= nil (if (or (< f 48) (> f 57)) (setq n nil) n))) (reverse (vl-string->list FN))))
	  F1 (substr FN 1 (- (strlen FN) (length F2)))
    )
    (setq F2 (vl-string->list (itoa (fix (1- (atoi (vl-list->string F2)))))))
    (if (> 3 (length F2)) (while (> 3 (length F2)) (setq F2 (append (list 48) F2))))
    (setq F2 (vl-list->string F2) FN (strcat F1 F2))
  )
  (setq FN (strcat FN "001"))
)(setq #PDF_Filename (strcat TXT1 FN ".pdf"))#PDF_Filename
)

;;;
;;;
;;;   박스 출력
;;;
;;; 선택한 4각 폴리곤의 도면을 출력한다.
;;; 다중선택도 가능하다.
;;;
;;;

(defun #PLOT_EXPRESS ($Mode / AcDoc AcLay AcPlot sa ss n MinPt MaxPt LP SF_List CLA)
(if (= (getvar "worlducs") 0) (and (setvar "cmdecho" 0) (vl-cmdf "UCS" "") (setvar "cmdecho" 1)))
(setq CLA #PlotClayer);;전체 자동출력 시 Plot전용 Layer 설정값
(if (or (= $Mode "Block_Mode") (= $Mode "PDFi_Mode"))
  (setq SF_List (list (cons 0 "INSERT")))
  (setq SF_List (list (cons 0 "LWPOLYLINE") (cons 40 0) (cons 41 0) (cons 70 1) (cons 90 4)))
)

(setq AcDoc (vla-get-ActiveDocument (vlax-get-acad-object))
      AcLay (vla-get-activelayout AcDoc)
      AcPlot (vla-get-plot AcDoc)
      n 0
)


(if (or (= $Mode "PDF_Mode") (= $Mode "PDFi_Mode"))
  (and
    (if #PDF_Filename ($PDF_NUM_ADD) (setq #PDF_Filename (strcat (getvar "dwgprefix") "A001.pdf")))
    (or
      (/= (vla-get-ConfigName AcLay) pdf_prt_name)
      (/= (vla-get-StyleSheet AcLay) pdf_ctb_file)
      (/= (vla-get-CanonicalMediaName AcLay) pdf_paper_size)
    )
    (progn
      (vla-put-ConfigName AcLay pdf_prt_name)
      (vla-put-StyleSheet AcLay pdf_ctb_file)
      (vla-put-CanonicalMediaName AcLay pdf_paper_size)
    )
  )
  (and
    (or
      (/= (vla-get-ConfigName AcLay) prt_name)
      (/= (vla-get-StyleSheet AcLay) ctb_file)
      (/= (vla-get-CanonicalMediaName AcLay) paper_size)
    )
    (progn
      (vla-put-ConfigName AcLay prt_name)
      (vla-put-StyleSheet AcLay ctb_file)
      (vla-put-CanonicalMediaName AcLay paper_size)
    )
  )
)

(and 
  (if (or (= $Mode "PDF_Mode") (= $Mode "PDFi_Mode"))
    (and
      (if (setq Buffer (getfiled "PDF 파일 작성" #PDF_Filename "pdf" 1))
	(and
	  (setq #PDF_Filename Buffer)
	  ($PDF_NUM_ADD)
	  ($PDF_NUM_MINUS)
	)
      )
    ) T
  )
  (if (= $Mode "AP_Mode")
    (progn
      (initget "Yes No")
      (if (/= (getkword "\n전체 도면을 출력하시겠습니까? [예(Y)/아니오(N)] <Y>: ") "No") (setq sa (ssget "X" SF_List)))
    )
    (setq sa (ssget SF_List))
  )
  (progn (vla-startundomark AcDoc) (setvar "cmdecho" 0) (command "zoom" "object" ss)(graphscr) (setq ss (#SS_Sort_Main sa)))
  (#BoxReaction ss SF_List)
  (/= (sslength ss) 0)
  (progn
    (vla-startundomark acDoc)
    (setvar "backgroundplot" 0)
    (vla-put-paperunits AcLay acmillimeters)
    (vla-put-standardscale AcLay acvpscaletofit)
    (vla-put-centerplot AcLay :vlax-true)
    (command "zoom" "object" ss "")(graphscr)
    (setvar "cmdecho" 1)
    (repeat (sslength ss)
      (vla-GetBoundingBox (vlax-ename->vla-object (ssname ss n)) 'MinPt 'MaxPt)
      (setq MinPt (vlax-safearray->list MinPt)
	    MaxPt (vlax-safearray->list MaxPt)
	    n (1+ n)
      )
      (ssget "W" MinPt MaxPt)
      (if (< (- (car MinPt) (car MaxPt)) (- (cadr MinPt) (cadr MaxPt)))	(setq LP 1) (setq LP 0))
      (setq DCSFix (trans '(0 0) 2 0)
	    MinPt (List->Safearray (list (- (car MinPt) (car DCSFix)) (- (cadr MinPt) (cadr DCSFix))))
	    MaxPt (List->Safearray (list (- (car MaxPt) (car DCSFix)) (- (cadr MaxPt) (cadr DCSFix))))
      )
      (vla-put-PlotRotation AcLay LP)
      (vla-SetWindowToPlot AcLay MinPt MaxPt)
      (vla-put-PlotType AcLay AcWindow)
      (if (= $Mode "RV_Mode")
	(vla-DisplayPlotPreview AcPlot acPartialPreview)
	(if (or (= $Mode "PDF_Mode") (= $Mode "PDFi_Mode"))
	  (progn (vla-PlotToFile AcPlot #PDF_Filename) ($PDF_NUM_ADD))
	  (progn (vla-PlotToDevice AcPlot) (PTE:highlight (ssget "P") 2)) ;;출력객체 숨김 옵션
	)
      )
    )
    (sssetfirst nil ss) (ssget)
    (setvar "cmdecho" 1)
    (vla-endundomark acDoc)
    (if (/= $Mode "RV_Mode")
      (prompt 
	(strcat "\n" (getvar "dwgprefix")(getvar "dwgname")
	  (if (or (= $Mode "PDF_Mode") (= $Mode "PDFi_Mode")) "\n" "\n\n출력된 객체를 표현하려면 Regen명령으로 재생성...\n")
	  (rtos n) " 장이 출력되었습니다."
	)
      )
      (prompt (strcat "\n" (rtos n) "장을 미리보기 완료하였습니다."))
    )
    (if (and (/= $Mode "RV_Mode") (> n 1))
      (alert 
	(strcat "\n\t" (getvar "dwgname") "\n\t" (rtos n) " 장이 출력되었습니다."
	  (if (or (= $Mode "PDF_Mode") (= $Mode "PDFi_Mode")) "" "\n\n\t출력된 객체를 표현하려면 Regen명령으로 객체 재생성이 필요합니다.")
	)
      )
    )(vlr-beep-reaction) ;;출력완료 신호음
  )
)
(if (or (= $Mode "PDF_Mode") (= $Mode "PDFi_Mode")) ($PDF_NUM_MINUS))
(vla-endundomark AcDoc)
(princ)
)

(defun C:PLOTEXPRESS () (prompt (strcat "PLOTEXPRESS\n출력할 도면 선택...")) (#PLOT_EXPRESS "Plot_Mode"))
(defun C:PLOTEXPRESSALL () (prompt (strcat "PLOTEXPRESSALL\nPLOT전용 LAYER 전체 출력...")) (#PLOT_EXPRESS "AP_Mode"))
(defun C:DREVIEW () (prompt (strcat "DREVIEW\n미리보기 할 도면 선택...")) (#PLOT_EXPRESS "RV_Mode"))
(defun C:PLOTBLOCK () (prompt (strcat "PLOTINSERTBLOCK\n출력할 블록 선택...")) (#PLOT_EXPRESS "Block_Mode"))
(defun C:PDFOUT () (prompt (strcat "PDFOUT\nPDF로 내보내기...")) (#PLOT_EXPRESS "PDF_Mode"))
(defun C:PDFBLOCKOUT () (prompt (strcat "PDFBLOCKOUT\nPDF로 내보내기...")) (#PLOT_EXPRESS "PDFi_Mode"))