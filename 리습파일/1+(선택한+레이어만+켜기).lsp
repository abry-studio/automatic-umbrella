
(defun C:1 (/ cmd lyr ss test)
     (setq cmd (getvar "cmdecho"))
     (setvar "cmdecho" 0)
     (command "layer" "on" "*" "")
     (setvar "cmdecho" cmd)
)
(c:lo)
