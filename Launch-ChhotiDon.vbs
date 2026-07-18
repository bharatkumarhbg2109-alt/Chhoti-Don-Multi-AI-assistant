Option Explicit
Dim shell, fso, scriptDir, command, exitCode
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & scriptDir & "\Start-ChhotiDon.ps1"" -Quiet"
exitCode = shell.Run(command, 0, True)
If exitCode <> 0 Then
  MsgBox "CHHOTI DON could not start. See " & scriptDir & "\.runtime\launcher.log and service logs.", 16, "CHHOTI DON"
End If
