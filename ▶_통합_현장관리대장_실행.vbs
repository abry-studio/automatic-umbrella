Option Explicit

Dim xl, wb, fso, targetPath
Set fso = CreateObject("Scripting.FileSystemObject")

targetPath = "C:\Users\ry789\OneDrive\Desktop\통합_현장관리및공정관리대장.xlsm"
If Not fso.FileExists(targetPath) Then
    targetPath = "C:\Users\ry789\OneDrive\Desktop\05 뽀삐 프로그램\통합_현장관리및공정관리대장.xlsm"
End If

If Not fso.FileExists(targetPath) Then
    targetPath = "C:\Users\ry789\Desktop\통합_현장관리및공정관리대장.xlsm"
End If

Set xl = CreateObject("Excel.Application")
xl.Visible = True
xl.DisplayAlerts = True
xl.UserControl = True
Set wb = xl.Workbooks.Open(targetPath)
wb.Sheets(1).Activate
