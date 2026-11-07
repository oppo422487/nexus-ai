"""Dangerous command patterns shared by safety adapters."""

DANGEROUS_COMMAND_HINTS = {
    "delete system32",
    "delete all files",
    "format drive",
    "format c drive",
    "powershell",
    "cmd",
    "regedit",
    "rm -rf",
}

