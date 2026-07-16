import os
import requests
import re
from loguru import logger
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from docxcompose.composer import Composer
from docx import Document
from pdf2docx import Converter

def get_attachment_links(item_id: str) -> list:
    """Find file names from MoJ API and return them as pseudo-links for the NextJS action."""
    links = []
    try:
        r = requests.get(f"https://vbpl-bientap-gateway.moj.gov.vn/api/qtdc/public/doc/{item_id}", verify=False, timeout=10)
        data = r.json().get('data', {})
        def find_files(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, str) and ('.doc' in v.lower() or '.pdf' in v.lower()):
                        if 'template' not in v.lower():
                            if v not in links: links.append(v)
                    find_files(v)
            elif isinstance(d, list):
                for i in d: find_files(i)
        find_files(data)
        
        # The frontend sometimes dynamically constructs the filename from docNum!
        # e.g., docNum "284a/TB-BTC" -> "284a_TB-BTC.doc"
        doc_num = data.get('docNum', '')
        if doc_num:
            clean_num = doc_num.replace('/', '_').replace('\\', '_')
            for ext in ['.doc', '.docx', '.pdf']:
                guess_name = f"{clean_num}{ext}"
                if guess_name not in links:
                    links.append(guess_name)
                    
    except Exception as e:
        logger.warning(f"Error fetching API for {item_id}: {e}")
    
    # Sometimes it's the exact item_id, sometimes a UUID. We will just return the filenames.
    # The actual download requires NextJS action. We prefix with a special scheme to indicate it.
    return [f"nextjs://{item_id}/{name}" for name in links]

def download_file(url: str, out_path: str):
    """Download a file using NextJS server action proxy."""
    if not url.startswith("nextjs://"):
        # Fallback for normal URLs (if any)
        try:
            r = requests.get(url, verify=False, stream=True, timeout=20)
            r.raise_for_status()
            with open(out_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            return True
        except: return False

    # Extract folderName and objectName
    parts = url.replace("nextjs://", "").split("/", 1)
    if len(parts) != 2: return False
    folder_name, object_name = parts

    # NextJS Server Action Headers
    target_url = f'https://vbpl.vn/van-ban/chi-tiet/thong-bao-284a-tb-btc--{folder_name}?tabs=tai-ve'
    headers = {
        'accept': 'text/x-component',
        'content-type': 'text/plain;charset=UTF-8',
        'next-action': 'bad13391811d5f14d7670e66189def56c08ceb1f',
    }
    
    # Try a few common bucket names
    import json
    import base64
    for bucket in ["vbpl", "moj", "default"]:
        payload = json.dumps([{"bucketName": bucket, "folderName": folder_name, "objectName": object_name, "preview": None}])
        try:
            r = requests.post(target_url, headers=headers, data=payload, verify=False, timeout=30)
            if r.status_code == 200:
                lines = r.text.split('\n')
                for line in lines:
                    if line.startswith('2:T'):
                        b64_parts = line[3:].split(',', 1)
                        if len(b64_parts) == 2:
                            b64 = b64_parts[1].strip("\"'")
                            data = base64.b64decode(b64)
                            if len(data) > 0:
                                with open(out_path, 'wb') as f: f.write(data)
                                return True
        except Exception as e:
            logger.error(f"Download failed for {object_name}: {e}")
    return False

def merge_docx(files: list, out_file: str):
    """Merge multiple docx files into one."""
    if not files:
        return
    if len(files) == 1:
        import shutil
        shutil.copy(files[0], out_file)
        return
        
    master = Document(files[0])
    composer = Composer(master)
    for file in files[1:]:
        doc = Document(file)
        composer.append(doc)
    composer.save(out_file)

def pdf_to_docx(pdf_file: str, docx_file: str):
    """Convert a PDF file to a DOCX file."""
    try:
        cv = Converter(pdf_file)
        cv.convert(docx_file, start=0, end=None)
        cv.close()
        return True
    except Exception as e:
        logger.error(f"Failed to convert {pdf_file} to docx: {e}")
        return False

def process_fallback_downloads(item_id: str, out_dir: str):
    """
    Main function to download and process attachments.
    Returns the final file path if successful, otherwise None.
    """
    links = get_attachment_links(item_id)
    if not links:
        logger.warning(f"No attachments found for {item_id}")
        return None
        
    docx_links = [l for l in links if l.lower().endswith('.docx')]
    doc_links = [l for l in links if l.lower().endswith('.doc')]
    pdf_links = [l for l in links if l.lower().endswith('.pdf')]
    
    # Try all links in order: DOCX -> DOC -> PDF
    targets = docx_links + doc_links + pdf_links
    if not targets:
        return None
        
    downloaded_files = []
    for i, link in enumerate(targets):
        ext = '.docx' if link in docx_links else ('.doc' if link in doc_links else '.pdf')
        tmp_path = os.path.join(out_dir, f"temp_part_{i}{ext}")
        logger.info(f"Downloading attachment: {link}")
        if download_file(link, tmp_path):
            downloaded_files.append((tmp_path, link))
            
    if not downloaded_files:
        return None
        
    import shutil
    largest_file = None
    largest_size = 0
    
    for f_path, link in downloaded_files:
        orig_name = link
        if orig_name.startswith('nextjs://'):
            orig_name = orig_name.split('/')[-1]
            
        ext = os.path.splitext(orig_name)[1]
        safe_name = "".join(c for c in orig_name if c.isalnum() or c in "._- ")
        if not safe_name: safe_name = f"noi_dung_{len(str(largest_size))}{ext}"
        
        target_path = os.path.join(out_dir, safe_name)
        # Avoid overwriting if multiple files resolve to same name
        counter = 1
        base_name, e = os.path.splitext(target_path)
        while os.path.exists(target_path):
            target_path = f"{base_name}_{counter}{e}"
            counter += 1
            
        shutil.copy(f_path, target_path)
        logger.info(f"Saved attachment to {target_path}")
        
        size = os.path.getsize(target_path)
        if size > largest_size:
            largest_size = size
            largest_file = target_path
            
    # Cleanup temp files
    for f_path, _ in downloaded_files:
        if os.path.exists(f_path):
            try:
                os.remove(f_path)
            except:
                pass
                
    return largest_file
