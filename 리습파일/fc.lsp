(defun C:FC()

  (setq !Style (tblnext "STYLE" T))

  (while !Style

    (setq !Style (strcase (cdr (assoc 2 !Style))))

    (command "style" !Style "malgun.ttf" "0" "1" "0" "N" "N") 

    (setq !Style (tblnext "STYLE"))

  )

)