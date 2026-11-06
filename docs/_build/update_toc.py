"""Fill the TOC / list-of-figures / list-of-tables fields of a .docx with LibreOffice (UNO).

    python3 update_toc.py <in.docx> <out.docx>

Starts a headless soffice on a private profile, updates every document index, saves as Word 2007+.
"""
import os
import subprocess
import sys
import tempfile
import time

import uno
from com.sun.star.beans import PropertyValue


def prop(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


src, dst = (os.path.abspath(a) for a in sys.argv[1:3])
profile = tempfile.mkdtemp(prefix="lo-toc-")
port = 2099
proc = subprocess.Popen(["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--invisible", "--norestore",
                         f"--accept=socket,host=127.0.0.1,port={port};urp;"])
try:
    ctx = None
    for _ in range(60):
        try:
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
            ctx = resolver.resolve(f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(0.5)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = None
    for _ in range(20):  # a fresh profile may not be ready to load documents right after connecting
        doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(src), "_blank", 0, (prop("Hidden", True),))
        if doc is not None:
            break
        time.sleep(2)
    idx = doc.getDocumentIndexes()
    styles = [n for n in doc.getStyleFamilies().getByName("ParagraphStyles").getElementNames()]
    caption_style = {1: next(n for n in styles if n.lower().replace(" ", "") == "hinhcaption"),
                     2: next(n for n in styles if n.lower().replace(" ", "") == "bangcaption")}
    for i, style in caption_style.items():   # list of figures / tables: paragraphs of the caption style
        x = idx.getByIndex(i)
        x.CreateFromOutline = False
        x.CreateFromMarks = False
        x.CreateFromLevelParagraphStyles = True
        lps = x.LevelParagraphStyles
        uno.invoke(lps, "replaceByIndex", (1, uno.Any("[]string", (style,))))
    for _ in range(2):  # second pass: page numbers settle after the lists themselves take space
        for i in range(idx.getCount()):
            idx.getByIndex(i).update()
        doc.refresh()
    for i in range(idx.getCount()):
        x = idx.getByIndex(i)
        print(i, x.getName(), len(x.getAnchor().getString().splitlines()), "lines")
    doc.storeToURL(uno.systemPathToFileUrl(dst), (prop("FilterName", "MS Word 2007 XML"),))
    doc.close(True)
finally:
    proc.terminate()
    proc.wait(timeout=30)
