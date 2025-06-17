from typing import Annotated
from fastapi import Depends, Form, UploadFile, File, Query, APIRouter

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.video import PixverseGeneration
from app.services.video_service import text2video, image2video, get_status_generate

router = APIRouter()


@router.post("/text2video", tags=['Text-to-video'])
async def generate_text2video(app_bundle_id: Annotated[str, Form(...)],
                              apphud_user_id: Annotated[str, Form(...)],
                              prompt: Annotated[str, Form(...)],
                              db: Session = Depends(get_db)):

    result = text2video(prompt)
    db_video = PixverseGeneration(
        video_id=str(result),
        app_bundle_id=app_bundle_id,
        apphud_user_id=apphud_user_id,
        description='generate video from text'
    )
    db.add(db_video)
    db.commit()

    return {'video_id': result}


@router.post("/image2video", tags=['Image-to-video'])
async def generate_image2video(app_bundle_id: Annotated[str, Form(...)],
                               apphud_user_id: Annotated[str, Form(...)],
                               prompt: Annotated[str, Form(...)],
                               image: UploadFile = File(...),
                               db: Session = Depends(get_db)):

    image_data = await image.read()
    result = image2video(prompt, image_data)

    db_video = PixverseGeneration(
        video_id=str(result),
        app_bundle_id=app_bundle_id,
        apphud_user_id=apphud_user_id,
        description='generate video from image'
    )
    db.add(db_video)
    db.commit()

    return {'video_id': result}


@router.get("/get_status", tags=['Get status'])
async def get_video_generation_status(app_bundle_id: Annotated[str, Query(...)],
                                      apphud_user_id: Annotated[str, Query(...)],
                                      video_id: Annotated[int, Query(...)],
                                      db: Session = Depends(get_db)):

    result = get_status_generate(video_id)
    db_video = PixverseGeneration(
        video_id=str(video_id),
        app_bundle_id=app_bundle_id,
        apphud_user_id=apphud_user_id,
        description='check generation'
    )
    db.add(db_video)
    db.commit()

    return result
