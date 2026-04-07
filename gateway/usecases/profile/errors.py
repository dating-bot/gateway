"""Domain errors for profile create/update flows (gRPC failures mapped in usecases)."""


class ProfileMutationError(Exception):
    """Base for create/update profile failures surfaced to Telegram handlers."""


class DuplicateProfileError(ProfileMutationError):
    """CreateProfile: profile already exists for telegram_id."""


class ProfileNotFoundForMutationError(ProfileMutationError):
    """UpdateProfile: no profile for telegram_id."""


class ProfileServiceTransportError(ProfileMutationError):
    """Unexpected gRPC failure from profile_service."""
