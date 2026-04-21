# vhs tape — 10-second demo of xiao
# Regenerate: vhs docs/demo/demo.tape

Output docs/demo/demo.gif

Set Shell "zsh"
Set FontSize 14
Set Width 1100
Set Height 620
Set Padding 16
Set TypingSpeed 40ms
Set PlaybackSpeed 1.0
Set Theme "Dracula"

Env XIAO_NO_CTA "1"

Hide
Type "export PATH=$PWD/.venv/bin:$PATH && clear"
Enter
Sleep 300ms
Show

Type "xiao status"
Sleep 300ms
Enter
Sleep 2500ms

Type "xiao status --json | head -12"
Sleep 300ms
Enter
Sleep 2500ms

Type "xiao consumables --json | head -12"
Sleep 300ms
Enter
Sleep 2500ms
