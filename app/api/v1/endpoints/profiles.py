from fastapi import APIRouter, Depends, status
from typing import List
import uuid
import datetime
from app.schemas.contracts import ProfileCreate, ProfileUpdate, ProfileResponse
from app.core.security import get_current_user_id, verify_profile_ownership
from app.core.errors import NotFoundException

router = APIRouter()

# In-memory store for Phase 01 contract tests; replaced by DB models in DB migration phase
_profiles_db: dict[str, ProfileResponse] = {}

@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_in: ProfileCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create birth profile bound to current user_id."""
    profile_id = f"prof_{uuid.uuid4().hex[:12]}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    profile = ProfileResponse(
        id=profile_id,
        user_id=current_user_id,
        name=profile_in.name,
        date_of_birth=profile_in.date_of_birth,
        time_of_birth=profile_in.time_of_birth,
        place_of_birth=profile_in.place_of_birth,
        latitude=profile_in.latitude,
        longitude=profile_in.longitude,
        timezone_id=profile_in.timezone_id,
        gender=profile_in.gender,
        is_primary=profile_in.is_primary,
        created_at=now
    )
    _profiles_db[profile_id] = profile
    return profile

@router.get("", response_model=List[ProfileResponse])
async def list_profiles(current_user_id: str = Depends(get_current_user_id)):
    """List profiles belonging exclusively to current_user_id."""
    return [p for p in _profiles_db.values() if p.user_id == current_user_id]

@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get single profile enforcing profile ownership boundary."""
    profile = _profiles_db.get(profile_id)
    if not profile:
        raise NotFoundException(f"Profile {profile_id} not found")
    
    # Strictly enforce ownership boundary
    verify_profile_ownership(profile.user_id, current_user_id)
    return profile

@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: str,
    profile_in: ProfileUpdate,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update profile enforcing ownership boundary."""
    profile = _profiles_db.get(profile_id)
    if not profile:
        raise NotFoundException(f"Profile {profile_id} not found")
    
    verify_profile_ownership(profile.user_id, current_user_id)
    
    updated_data = profile.model_dump()
    for field, val in profile_in.model_dump(exclude_unset=True).items():
        if val is not None:
            updated_data[field] = val
            
    updated_profile = ProfileResponse(**updated_data)
    _profiles_db[profile_id] = updated_profile
    return updated_profile

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete profile enforcing ownership boundary."""
    profile = _profiles_db.get(profile_id)
    if not profile:
        raise NotFoundException(f"Profile {profile_id} not found")
    
    verify_profile_ownership(profile.user_id, current_user_id)
    del _profiles_db[profile_id]
    return None
