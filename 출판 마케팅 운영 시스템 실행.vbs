Option Explicit
Dim shell, fso, root, cmd
root = "Y:\출판사업본부\06. 출판 마케팅 운영 시스템"
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
cmd = """" & root & "\업데이트 후 실행.cmd" & """"
shell.Run cmd, 1, False
