"""Verify the Windows client's real public HTTPS source importer without mock data.

Do not use customer URLs or credentials here.
"""
from runtime import source_onboarding

url = "https://example.com/"
item = source_onboarding.inspect_remote("website", url)
assert item["read"] is True, "Source was not marked readable"
assert "Example Domain" in item["excerpt"], "Real website text was not extracted"
assert source_onboarding.consolidate([item])["suggestions"]["website"]["value"] == url
print("PASS public HTTPS website source was fetched and its text extracted")
