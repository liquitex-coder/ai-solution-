"""keys.manifest.yaml stays value-free and host-pinned (requirements §37 K-1/K-2).

keykeeper itself is not a dependency of this repo, so this parses the flat
manifest layout with the standard library. It checks the decisions recorded in
§37: only the WordPress keys are declared, only WP_BEARER_TOKEN may be sent, and
only to public-api.wordpress.com.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# keykeeper's KeySpec fields (src/keykeeper/manifest.py _KEY_FIELDS); anything else is rejected there too.
KEY_FIELDS = {"name", "env_var", "issuer", "scopes", "expires", "rotation",
              "issue_url", "allowed_hosts", "allowed_commands", "notes"}


def parse_manifest(text: str) -> tuple[str, dict[str, dict[str, object]]]:
    """Parse the flat `project:` + `keys:` list layout used by keys.manifest.yaml."""
    project = ""
    keys: dict[str, dict[str, object]] = {}
    current: dict[str, object] | None = None
    list_field = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("project:"):
            project = line.split(":", 1)[1].strip()
        elif line.startswith("- name:"):
            name = line.split(":", 1)[1].strip()
            current = {"name": name}
            keys[name] = current
            list_field = ""
        elif current is not None and line.startswith("  - "):
            items = current.setdefault(list_field, [])
            assert isinstance(items, list)
            items.append(line[4:].strip())
        elif current is not None and line.startswith("  "):
            field, _, value = line.strip().partition(":")
            value = value.strip()
            current[field] = value if value else []
            list_field = field
    return project, keys


class KeysManifestTests(unittest.TestCase):
    def setUp(self):
        text = (ROOT / "keys.manifest.yaml").read_text(encoding="utf-8")
        self.project, self.keys = parse_manifest(text)

    def test_declares_only_the_wordpress_keys(self):
        self.assertEqual(self.project, "ai-solution")
        self.assertEqual(set(self.keys), {"WP_BEARER_TOKEN", "WP_APP_PASSWORD"})

    def test_only_known_fields_so_no_values(self):
        for name, spec in self.keys.items():
            self.assertLessEqual(set(spec), KEY_FIELDS, name)
            self.assertEqual(spec.get("env_var"), name)

    def test_bearer_token_is_pinned_to_wordpress_com(self):
        self.assertEqual(self.keys["WP_BEARER_TOKEN"].get("allowed_hosts"), ["public-api.wordpress.com"])

    def test_sandbox_password_is_never_sent(self):
        spec = self.keys["WP_APP_PASSWORD"]
        self.assertFalse(spec.get("allowed_hosts"))
        self.assertFalse(spec.get("allowed_commands"))

    def test_plan_directory_is_gitignored(self):
        lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".keykeeper/", lines)


if __name__ == "__main__":
    unittest.main()
