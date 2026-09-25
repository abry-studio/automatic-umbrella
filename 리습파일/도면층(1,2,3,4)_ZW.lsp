(defun C:1 (/ e n)
    (setq e (car (entsel ">>> Pick an object to setting layer :")))
    (if e (progn
	  (setq e (entget e))
	  (setq n (cdr (assoc 8 e)))
	  (command "layer" "set" n "")
	  )
    )
)

(defun C:2 ()
(SETQ ES (CAR (ENTSEL ">>PICK FREEZE..?"))
      EG (ENTGET ES)
      AS (CDR (ASSOC 8 EG))
);SETQ
(COMMAND "LAYER" "off" AS "")
)

(defun C:4 ()
(SETQ ES (CAR (ENTSEL ">>PICK NO FREEZE..?"))
      EG (ENTGET ES)
      AS (CDR (ASSOC 8 EG))
);SETQ
(COMMAND "LAYER" "s" AS "off" "*" """")
)

(defun C:3 () (COMMAND "LAYER" "on" "*" ""))