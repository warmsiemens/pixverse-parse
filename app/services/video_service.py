import os.path
import tempfile
import time
from typing import Optional, Dict, Any
from uuid import uuid4

import oss2

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.services.playwright_service import manager


def request_with_retry(method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    for _ in range(settings.MAX_RETRIES):
        try:
            response = httpx.request(method, url, timeout=15, **kwargs)
            if response.status_code in settings.RETRY_STATUS_CODES:
                time.sleep(settings.RETRY_DELAY)
                continue
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502,
                                detail=f"HTTP error: {e.response.status_code} -"
                                       f" {e.response.text}")

    raise HTTPException(status_code=504, detail="Max retries exceeded")


def _check_pixverse_error(response: Dict):
    if response.get("ErrCode", 0) != 0:
        raise HTTPException(
            status_code=502,
            detail=f"Pixverse error {response.get('ErrCode')}:"
                   f" {response.get('ErrMsg', 'Unknown error')}"
        )


def text2video(prompt):
    headers = {
        "content-type": "application/json",
        "origin": "https://app.pixverse.ai",
        "referer": "https://app.pixverse.ai/",
        "x-platform": "Web",
        "token": manager.token,
        "accept": "application/json, text/plain, */*",
        "refresh": "credit",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 YaBrowser/25.4.0.0 Safari/537.36"
        ),
    }

    payload = {
        "lip_sync_tts_speaker_id": "Auto",
        "prompt": prompt,
        "duration": 5,
        "quality": "360p",
        "aspect_ratio": "16:9",
        "motion_mode": "normal",
        "model": "v4.5",
        "credit_change": 20
    }

    url = f"{settings.BASE_URL}/video/t2v"

    response = request_with_retry("POST", url, json=payload, headers=headers)
    _check_pixverse_error(response)

    video_id = response.get("Resp", {}).get("video_id")
    if not video_id:
        raise HTTPException(status_code=500, detail="video_id not found")
    return video_id


def get_upload_token():
    url = f"{settings.BASE_URL}/getUploadToken"
    headers = {
        "origin": "https://app.pixverse.ai",
        "referer": "https://app.pixverse.ai/",
        "x-platform": "Web",
        "token": manager.token,
        "accept": "application/json, text/plain, */*",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 YaBrowser/25.4.0.0 Safari/537.36"
        ),
    }
    response = request_with_retry("POST", url, headers=headers)
    _check_pixverse_error(response)
    security_dict = response.get("Resp", '')
    if not security_dict:
        raise HTTPException(status_code=500, detail="keys and token dict not found")
    return security_dict


def upload_image(image_data):
    image_id_name = str(uuid4())
    security_dict = get_upload_token()
    access_key_id = security_dict['Ak']
    access_key_secret = security_dict['Sk']
    security_token = security_dict['Token']
    endpoint = 'oss-accelerate.aliyuncs.com'
    bucket_name = 'pixverse-fe-upload'
    object_name = f'upload/{image_id_name}.jpg'

    auth = oss2.StsAuth(access_key_id, access_key_secret, security_token)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    try:
        temp_file.write(image_data)
        temp_file.flush()
        temp_file.close()
        file_size = os.path.getsize(temp_file.name)
        oss2.resumable_upload(bucket, object_name, temp_file.name)
    finally:
        os.remove(temp_file.name)

    return image_id_name, file_size


def batch_upload_media(image_data):
    image_id_name, file_size = upload_image(image_data)
    url = f"{settings.BASE_URL}/media/batch_upload_media"
    headers = {
        "origin": "https://app.pixverse.ai",
        "referer": "https://app.pixverse.ai/",
        "x-platform": "Web",
        "token": manager.token,
        "content-type": "application/json",
        "accept": "application/json, text/plain, */*",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 YaBrowser/25.4.0.0 Safari/537.36"
        ),
    }
    file_name = f'{image_id_name}.jpg'
    obj_path = f'upload/{file_name}'

    payload = {
        "images": [
            {
                "name": file_name,
                "size": file_size,
                "path": obj_path
            }
        ]
    }
    response = request_with_retry("POST", url, headers=headers, json=payload)
    _check_pixverse_error(response)
    data = response.get("Resp", {})

    if not data:
        raise HTTPException(status_code=500, detail="data not found")
    return data


def image2video(prompt, image_data):
    upload_data = batch_upload_media(image_data=image_data)
    parsed_upload_data = upload_data.get("result", [])
    if not parsed_upload_data:
        raise HTTPException(status_code=500, detail="result not found")

    customer_img_path = parsed_upload_data[0].get("path")
    customer_img_url = parsed_upload_data[0].get("url")

    headers = {
        "content-type": "application/json",
        "origin": "https://app.pixverse.ai",
        "referer": "https://app.pixverse.ai/",
        "x-platform": "Web",
        "token": manager.token,
        "accept": "application/json, text/plain, */*",
        "refresh": "credit",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 YaBrowser/25.4.0.0 Safari/537.36"
        ),
    }

    payload = {
        "customer_img_path": customer_img_path,
        "customer_img_url": customer_img_url,
        "lip_sync_tts_speaker_id": "Auto",
        "prompt": prompt,
        "duration": 5,
        "quality": "360p",
        "motion_mode": "normal",
        "model": "v4.5",
        "credit_change": 20
    }

    url = f"{settings.BASE_URL}/video/i2v"

    response = request_with_retry("POST", url, json=payload, headers=headers)
    _check_pixverse_error(response)

    video_id = response.get("Resp", {}).get("video_id")
    if not video_id:
        raise HTTPException(status_code=500, detail="video_id not found")
    return video_id


def get_status_generate(video_id):
    status_dict = {1: 'Generation successful', 5: 'Generating', 6: 'Deleted',
                   7: 'Contents moderation failed', 8: 'Generation failed'}

    headers = {
        "content-type": "application/json",
        "origin": "https://app.pixverse.ai",
        "referer": "https://app.pixverse.ai/",
        "x-platform": "Web",
        "token": manager.token,
        "accept": "application/json, text/plain, */*",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 YaBrowser/25.4.0.0 Safari/537.36"
        ),
    }
    payload = {'offset': 0, 'limit': 50, 'polling': True,
               'filter': {'off_peak': 0}, 'web_offset': 0, 'app_offset': 0}

    url = f"{settings.BASE_URL}/video/list/personal"
    response = request_with_retry("POST", url, json=payload, headers=headers)
    _check_pixverse_error(response)

    data = response.get("Resp", {}).get("data")
    if not data:
        raise HTTPException(status_code=500, detail="data about generations not found")

    for generation in data:
        if generation["video_id"] == video_id:
            if generation["video_status"] == 1:
                return {"url": generation["url"]}
            return {"status": status_dict[generation["video_status"]]}
