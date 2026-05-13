from typing import final, override

import structlog

from external_clients.profile_api.v1.profile_grpc import ProfileServiceStub
from external_clients.profile_api.v1.profile_pb2 import (
    ActivateSubscriptionRequest,
    CreateProfileRequest,
    DeletePhotoRequest,
    Gender,
    GenderPref,
    GetPreferencesRequest,
    GetPresignedUrlRequest,
    GetProfileByIdRequest,
    GetProfileRequest,
    SetGeoRequest,
    SetPreferencesRequest,
    SubscriptionTier,
    UpdateProfileRequest,
    UploadPhotoRequest,
)
from gateway.domain.profile import Gender as DomainGender
from gateway.domain.profile import PhotoInfo, Profile
from gateway.domain.profile import SubscriptionTier as DomainSubscriptionTier
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.adapters.GrpcProfileServiceAdapter")

_GENDER_MAP: dict[DomainGender, int] = {
    DomainGender.ANY: Gender.GENDER_UNSPECIFIED,
    DomainGender.UNSPECIFIED: Gender.GENDER_UNSPECIFIED,
    DomainGender.MALE: Gender.GENDER_MALE,
    DomainGender.FEMALE: Gender.GENDER_FEMALE,
}

_GENDER_REVERSE: dict[int, DomainGender] = {v: k for k, v in _GENDER_MAP.items()}
_GENDER_PREF_MAP: dict[DomainGender, int] = {
    DomainGender.ANY: GenderPref.GENDER_PREF_ANY,
    DomainGender.MALE: GenderPref.GENDER_PREF_MALE,
    DomainGender.FEMALE: GenderPref.GENDER_PREF_FEMALE,
    DomainGender.UNSPECIFIED: GenderPref.GENDER_PREF_UNSPECIFIED,
}
_GENDER_PREF_REVERSE: dict[int, DomainGender] = {
    GenderPref.GENDER_PREF_ANY: DomainGender.ANY,
    GenderPref.GENDER_PREF_MALE: DomainGender.MALE,
    GenderPref.GENDER_PREF_FEMALE: DomainGender.FEMALE,
    GenderPref.GENDER_PREF_UNSPECIFIED: DomainGender.UNSPECIFIED,
}

_SUBSCRIPTION_TIER_MAP: dict[DomainSubscriptionTier, int] = {
    DomainSubscriptionTier.FREE: SubscriptionTier.SUBSCRIPTION_TIER_FREE,
    DomainSubscriptionTier.PREMIUM: SubscriptionTier.SUBSCRIPTION_TIER_PREMIUM,
}

_SUBSCRIPTION_TIER_REVERSE: dict[int, DomainSubscriptionTier] = {
    SubscriptionTier.SUBSCRIPTION_TIER_FREE: DomainSubscriptionTier.FREE,
    SubscriptionTier.SUBSCRIPTION_TIER_PREMIUM: DomainSubscriptionTier.PREMIUM,
}


@final
class GrpcProfileServiceAdapter(ProfileServiceProtocol):
    def __init__(self, *, stub: ProfileServiceStub) -> None:
        self._stub = stub

    @override
    async def get_profile(self, telegram_id: int) -> Profile | None:
        resp = await self._stub.GetProfile(GetProfileRequest(telegram_id=telegram_id))
        if not resp.found:
            return None
        return Profile(
            telegram_id=telegram_id,
            profile_id=resp.profile_id,
            name=resp.name,
            age=resp.age,
            city=resp.city,
            bio=resp.bio,
            gender=_GENDER_REVERSE.get(resp.gender, DomainGender.UNSPECIFIED),
            photos=[PhotoInfo(photo_id=p.photo_id, is_active=p.is_active) for p in resp.photos],
            latitude=resp.latitude if resp.HasField("latitude") else None,
            longitude=resp.longitude if resp.HasField("longitude") else None,
            subscription_tier=_SUBSCRIPTION_TIER_REVERSE.get(resp.subscription_tier, DomainSubscriptionTier.FREE),
            subscription_expires_at_seconds=(
                resp.subscription_expires_at_seconds if resp.HasField("subscription_expires_at_seconds") else None
            ),
            is_active=True,
        )

    @override
    async def get_profile_by_id(self, profile_id: int) -> Profile | None:
        resp = await self._stub.GetProfileById(GetProfileByIdRequest(profile_id=profile_id))
        if not resp.found:
            return None

        profile = await self.get_profile(resp.telegram_id)
        if profile is not None:
            return Profile(
                telegram_id=profile.telegram_id,
                profile_id=profile.profile_id,
                name=profile.name,
                age=profile.age,
                city=profile.city,
                bio=profile.bio,
                gender=profile.gender,
                photos=profile.photos,
                latitude=profile.latitude,
                longitude=profile.longitude,
                subscription_tier=profile.subscription_tier,
                subscription_expires_at_seconds=profile.subscription_expires_at_seconds,
                is_active=resp.is_active,
            )

        return Profile(
            telegram_id=resp.telegram_id,
            profile_id=resp.profile_id,
            name=resp.name,
            age=resp.age,
            city=resp.city,
            bio=resp.bio,
            gender=_GENDER_REVERSE.get(resp.gender, DomainGender.UNSPECIFIED),
            photos=[],
            latitude=resp.latitude if resp.HasField("latitude") else None,
            longitude=resp.longitude if resp.HasField("longitude") else None,
            subscription_tier=_SUBSCRIPTION_TIER_REVERSE.get(resp.subscription_tier, DomainSubscriptionTier.FREE),
            subscription_expires_at_seconds=(
                resp.subscription_expires_at_seconds if resp.HasField("subscription_expires_at_seconds") else None
            ),
            is_active=resp.is_active,
        )

    @override
    async def create_profile(self, request: ProfileServiceProtocol.CreateRequest) -> int:
        resp = await self._stub.CreateProfile(
            CreateProfileRequest(
                telegram_id=request.telegram_id,
                name=request.name,
                age=request.age,
                city=request.city,
                bio=request.bio,
                gender=_GENDER_MAP.get(request.gender, Gender.GENDER_UNSPECIFIED),
                latitude=request.latitude,
                longitude=request.longitude,
            )
        )
        return resp.profile_id

    @override
    async def update_profile(self, request: ProfileServiceProtocol.UpdateRequest) -> None:
        _ = await self._stub.UpdateProfile(
            UpdateProfileRequest(
                telegram_id=request.telegram_id,
                name=request.name,
                age=request.age,
                city=request.city,
                bio=request.bio,
            )
        )

    @override
    async def set_geo(self, telegram_id: int, latitude: float, longitude: float) -> None:
        _ = await self._stub.SetGeo(SetGeoRequest(telegram_id=telegram_id, latitude=latitude, longitude=longitude))

    @override
    async def upload_photo(self, telegram_id: int, data: bytes, content_type: str) -> int:
        resp = await self._stub.UploadPhoto(
            UploadPhotoRequest(telegram_id=telegram_id, data=data, content_type=content_type)
        )
        return resp.photo_id

    @override
    async def delete_photo(self, telegram_id: int, photo_id: int) -> None:
        _ = await self._stub.DeletePhoto(DeletePhotoRequest(telegram_id=telegram_id, photo_id=photo_id))

    @override
    async def get_presigned_url(self, photo_id: int) -> str:
        resp = await self._stub.GetPresignedUrl(GetPresignedUrlRequest(photo_id=photo_id))
        return resp.url

    @override
    async def set_preferences(self, request: ProfileServiceProtocol.SetPreferencesRequest) -> None:
        _ = await self._stub.SetPreferences(
            SetPreferencesRequest(
                telegram_id=request.telegram_id,
                gender_pref=_GENDER_PREF_MAP.get(request.gender_pref, GenderPref.GENDER_PREF_UNSPECIFIED),
                age_min=request.age_min,
                age_max=request.age_max,
                max_distance_km=request.max_distance_km,
            )
        )

    @override
    async def get_preferences(self, telegram_id: int) -> ProfileServiceProtocol.Preferences | None:
        resp = await self._stub.GetPreferences(GetPreferencesRequest(telegram_id=telegram_id))
        if not resp.found:
            return None
        return ProfileServiceProtocol.Preferences(
            gender_pref=_GENDER_PREF_REVERSE.get(resp.gender_pref, DomainGender.ANY),
            age_min=resp.age_min,
            age_max=resp.age_max,
            max_distance_km=resp.max_distance_km,
        )

    @override
    async def activate_subscription(self, request: ProfileServiceProtocol.ActivateSubscriptionRequest) -> int:
        resp = await self._stub.ActivateSubscription(
            ActivateSubscriptionRequest(
                telegram_id=request.telegram_id,
                tier=_SUBSCRIPTION_TIER_MAP.get(request.tier, SubscriptionTier.SUBSCRIPTION_TIER_FREE),
                duration_seconds=request.duration_seconds,
                telegram_payment_charge_id=request.telegram_payment_charge_id or "",
                provider_payment_charge_id=request.provider_payment_charge_id or "",
                invoice_payload=request.invoice_payload or "",
            )
        )
        return resp.subscription_expires_at_seconds
