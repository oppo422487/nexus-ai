"""Local exact-name reading confined to a current incoming call window."""
import asyncio
import io


def match_lines(lines,cfg):
    from core.whatsapp_contact_rules import identity_key,live_rules
    observed={identity_key(line) for line in lines if str(line).strip()}
    matches=[]
    for rule in live_rules(cfg):
        for alias in [rule['contact_name'],*rule.get('aliases',[])]:
            if identity_key(alias) in observed:matches.append(alias)
    keys={identity_key(value) for value in matches}
    if len(keys)!=1:raise RuntimeError('Local incoming caller name is missing or ambiguous.')
    return matches[0]


async def ocr_lines(image):
    from winsdk.windows.storage.streams import InMemoryRandomAccessStream,DataWriter
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    engine=OcrEngine.try_create_from_language(Language('en-US'))
    if engine is None:raise RuntimeError('Windows English OCR is unavailable.')
    buf=io.BytesIO();image.save(buf,format='PNG')
    stream=InMemoryRandomAccessStream();writer=DataWriter(stream)
    try:
        writer.write_bytes(buf.getvalue());await writer.store_async();stream.seek(0)
        decoder=await BitmapDecoder.create_async(stream)
        bitmap=await decoder.get_software_bitmap_async()
        try:result=await engine.recognize_async(bitmap)
        finally:bitmap.close()
        return [line.text for line in result.lines]
    finally:
        writer.detach_stream();writer.close();stream.close()


def local_caller(controller,cfg):
    title=getattr(controller.window,'Name','')
    # Never match a name seen in the main window's chat/sidebar/history.
    if not isinstance(title,str) or title.casefold().strip() not in (
            'voice call','incoming voice call','incoming call','whatsapp voice call'):
        raise RuntimeError('Local caller reading requires the separate current call window.')
    nodes=controller.nodes()
    if controller.state()=='incoming':
        try:return match_lines([n.Name for n in nodes if not n.IsOffscreen and n.ControlTypeName=='TextControl'],cfg)
        except RuntimeError:pass
    from core.whatsapp_call_vision import capture
    frame=capture(controller.window.NativeWindowHandle)
    lines=asyncio.run(asyncio.wait_for(ocr_lines(frame.image),timeout=4))
    labels={str(s).casefold().strip() for s in lines}
    incoming=any('incoming' in s and 'call' in s for s in labels)
    buttons=bool(labels & {'accept','answer','accept call','answer call'}) and bool(labels & {'decline','reject','decline call','reject call'})
    if any('video' in s for s in labels) or not (incoming or buttons):
        raise RuntimeError('Local OCR did not verify a current incoming voice call.')
    return match_lines(lines,cfg)
