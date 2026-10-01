' SIGTRANS Saude - lancador invisivel do servico
' Sobe o iniciar-servico.bat SEM mostrar a janela preta (window style 0).
' Chamado pela tarefa de inicializacao do Windows (ver instalar-servico.bat).
Set fso = CreateObject("Scripting.FileSystemObject")
pasta = fso.GetParentFolderName(WScript.ScriptFullName)
bat = pasta & "\iniciar-servico.bat"
CreateObject("WScript.Shell").Run """" & bat & """", 0, False
