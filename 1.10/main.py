
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
import aiofiles
from pathlib import Path
from datetime import datetime
import uuid
from PIL import Image
import io
import json


UPLOAD_ROOT = Path('uploads')
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_MIME_PREFIX = 'image/'
THUMBNAIL_MAX_SIZE = (400, 400)

app = FastAPI(title='Photo Gallery API')


def secure_filename(filename: str) -> str:
    name = Path(filename).name
    return name.replace(' ', '_')


async def save_upload_file(file: UploadFile, dest: Path) -> int:
    async with aiofiles.open(dest, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
        return len(content)


def make_thumbnail(image_bytes: bytes) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as img:
        img.thumbnail(THUMBNAIL_MAX_SIZE)
        out = io.BytesIO()

        if img.mode in ('RGBA', 'LA'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            bg.save(out, format='JPEG', quality=85)
        else:
            img.convert('RGB').save(out, format='JPEG', quality=85)
        return out.getvalue()


@app.post('/upload')
async def upload_images(
        artist: Optional[str] = Form(None),
        files: List[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail='No files uploaded')

    today = datetime.utcnow().strftime('%Y-%m-%d')
    batch_id = uuid.uuid4().hex
    dest_dir = UPLOAD_ROOT / today / batch_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for upload in files:
        if not upload.content_type or not upload.content_type.startswith(ALLOWED_MIME_PREFIX):
            results.append({'filename': upload.filename, 'status': 'rejected', 'reason': 'invalid_mime'})
            continue

        content = await upload.read()
        size = len(content)
        if size == 0:
            results.append({'filename': upload.filename, 'status': 'rejected', 'reason': 'empty_file'})
            continue
        if size > MAX_FILE_SIZE:
            results.append({'filename': upload.filename, 'status': 'rejected', 'reason': 'file_too_large'})
            continue

        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
        except Exception:
            results.append({'filename': upload.filename, 'status': 'rejected', 'reason': 'not_an_image'})
            continue

        safe_name = secure_filename(upload.filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        orig_path = dest_dir / unique_name

        async with aiofiles.open(orig_path, 'wb') as f:
            await f.write(content)

        thumb_bytes = make_thumbnail(content)
        thumb_name = f"thumb_{unique_name.rsplit('.', 1)[0]}.jpg"
        thumb_path = dest_dir / thumb_name
        async with aiofiles.open(thumb_path, 'wb') as f:
            await f.write(thumb_bytes)

        metadata = {
            'original_filename': upload.filename,
            'saved_filename': unique_name,
            'thumbnail_filename': thumb_name,
            'content_type': upload.content_type,
            'size_bytes': size,
            'artist': artist,
            'saved_at_utc': datetime.utcnow().isoformat() + 'Z',
            'path': str(orig_path),
        }
        meta_path = dest_dir / f'{unique_name}.json'
        async with aiofiles.open(meta_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))

        results.append({'filename': upload.filename, 'status': 'saved', 'metadata': metadata})

    return JSONResponse({'batch_id': batch_id, 'date': today, 'results': results})


@app.get('/ping')
async def ping():
    return {'status': 'ok'}
