from sqlalchemy import Column, Integer, String
from app.db.database import Base


class PixverseGeneration(Base):
    __tablename__ = "pixverse_history"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, index=True)
    app_bundle_id = Column(String, nullable=False)
    apphud_user_id = Column(String, nullable=False)
    description = Column(String, nullable=False)
