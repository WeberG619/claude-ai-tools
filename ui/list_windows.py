"""List all windows"""
from pywinauto import Desktop

d = Desktop(backend="uia")
wins = d.windows()
for w in wins[:10]:
    try:
        print(f"- {w.window_text()}")
    except:
        pass
