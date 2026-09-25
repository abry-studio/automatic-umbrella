; 글짜 왕창 더해서 한개의 문자 수정해 써지기  


       (defun c:tc (/ z ss sno no tno sum x entity etype num h pt dd)
       (setvar "cmdecho" 0)
       (prompt "\nSelect Text: ")
       (setq ss (ssget))                
       (setq sno (sslength ss))             
       (setq no 0)
       (setq sum 0.0)
       (setq tno 0)


       (repeat sno
           (setq x (ssname ss no))
           (setq etype (cdr (assoc 0 (entget x))))
           (if (= etype "TEXT")
               (progn
                  (setq entity (entget x))
                  (setq num (cdr (assoc 1 entity)))
                  (setq num (atof num))
                  (setq sum (+ sum num))
                  (setq tno (1+ tno))
               )
           )
           (setq no (1+ no))
       )

       (setq tno (itoa tno))
       (setq sum (rtos sum 2 2))
       (princ "\nAdding ")
       (princ tno)
       (princ " \nTexts: ")
       (princ "\nThe Result is: ")
       (princ sum)
       (princ "   ")

  (prompt "\n수정할 텍스트를 고르시오: ")
(setq ent1 (entsel))
(setq ent2 (nth 0 ent1))   


;ent2 <===== <Entity name: 32425a0>




(setq ent3 (entget ent2))

; ent3====>
;     ((-1 . <Entity name: 32425a0>) (0 . "TEXT") (5 . "41C") (100 . "AcDbEntity") 
;    (67 . 0) (8 . "0") (100 . "AcDbText") (10 24.9217 128.381 0.0) (40 . 0.7) (1 . 
;    "14.93") (50 . 0.0) (41 . 1.0) (51 . 0.0) (7 . "STANDARD") (71 . 0) (72 . 0) 
;    (11 0.0 0.0 0.0) (210 0.0 0.0 1.0) (100 . "AcDbText") (73 . 0))



(entmod (subst (cons 1 sum) (assoc 1 ent3) ent3))     

          
       (setvar "cmdecho" 1)
       (setvar "blipmode" 1)
       (prin1))


-----------------------------------------------------------------------------------------

(defun c:AA1( / point AR1 pnt selection AREA)

        (graphscr)
        (SETVAR "CMDECHO" 0)
; Text control
  (if (= (tblsearch "style" "ghs") nil)
      (command "style" "ghs" "romans,Ghs" "" "" "" "" ""))
  (setvar "textstyle" "ghs")


        (PROMPT  "   Text Size <")
        (if (= TS nil)
            (progn
                 (setq TS 1.0)
          )
        )
        (prin1 ts)
        (PROMPT  ">")

        (setq point (getpoint "\n Pick Internal Point"))


  (while (/= cadr point nil)
  (setq old_layer (getvar "clayer"))
  (if (= (tblsearch "layer" "면적구하기") nil)
      (command "layer" "m" "면적구하기" "c" "30" "" "")
      (if (/= old_layer "면적구하기")
          (setvar "clayer" "면적구하기"))) ;if,if





(command "BPOLY" point "")
        (command "area" "e" "last")
        (setq ar1 (rtos (getvar "area") 2 2))
        (setq AREA (strcat "" AR1 ))



        (command "text" point TS  0  AREA)
    (setvar "clayer" old_layer)
        (setq point (getpoint "\n  Pick Internal Point: <CR=Exit>:"))
  ) ;while end

        (SETVAR "CMDECHO" 1)
        (PRIN1)
)


