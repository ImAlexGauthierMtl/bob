"""Presentation dependencies for Bob Cloud stub."""

from app.application.use_cases.bob_cloud_stub_use_cases import BobCloudStubUseCases
from app.infrastructure.fixtures import BobCloudFixtureSource


_fixture_source = BobCloudFixtureSource()


def get_stub_use_cases() -> BobCloudStubUseCases:
    return BobCloudStubUseCases(fixtures=_fixture_source)


def reset_stub_fixture_source() -> None:
    _fixture_source.reset()
