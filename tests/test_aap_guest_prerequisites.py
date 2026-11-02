import importlib.util
from pathlib import Path
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "guest_prerequisites",
    Path(__file__).resolve().parents[1] / "src/aap_guest_prerequisites.py",
)
guest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guest)


class GuestPrerequisitesTests(unittest.TestCase):
    def test_only_existing_growth_layout_is_supported(self):
        mount = {"filesystems": [{"source": "/dev/sda4", "fstype": "xfs"}]}
        devices = {
            "blockdevices": [
                {
                    "name": "sda",
                    "size": 64_424_509_440,
                    "children": [{"name": "sda4", "type": "part", "size": 50}],
                }
            ]
        }
        self.assertTrue(guest.root_layout(mount, devices)["supported"])
        mount["filesystems"][0]["source"] = "/dev/mapper/root"
        self.assertFalse(guest.root_layout(mount, devices)["supported"])
        mount["filesystems"][0] = {"source": "/dev/sda4", "fstype": "ext4"}
        self.assertFalse(guest.root_layout(mount, devices)["supported"])

    def test_tls_failure_never_becomes_success(self):
        with mock.patch.object(guest.ssl, "create_default_context") as context:
            with mock.patch.object(
                guest.socket, "create_connection", side_effect=OSError
            ):
                self.assertEqual(
                    guest.trusted_https("example.invalid"), {"verified": False}
                )
            context.assert_called_once_with()

    def test_tls_probe_uses_hostname_and_sends_no_application_data(self):
        with mock.patch.object(guest.ssl, "create_default_context") as context:
            with mock.patch.object(guest.socket, "create_connection") as connection:
                self.assertEqual(
                    guest.trusted_https("example.invalid"), {"verified": True}
                )
            context.return_value.wrap_socket.assert_called_once_with(
                connection.return_value.__enter__.return_value,
                server_hostname="example.invalid",
            )
            context.return_value.wrap_socket.return_value.__enter__.return_value.send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
