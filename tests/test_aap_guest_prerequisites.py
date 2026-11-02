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

    def test_preparation_requires_proved_growth_and_does_not_require_installer_runtime_yet(
        self,
    ):
        checks = {
            "bundle_temporary_space": False,
            "bundle_var_temporary_space": True,
            "required_tools": False,
            "trusted_redhat_https": True,
        }
        tools = {"growpart": True, "podman": False}
        storage = {"supported": True, "unallocated_bytes": 30 * guest.GIB}
        filesystems = {
            p: {"available_bytes": 3 * guest.GIB, "shares_root": True}
            for p in ("/tmp", "/var/tmp")
        }
        report = guest.phase_assessment(checks, tools, storage, filesystems, 0)
        self.assertTrue(report["preparation_ready"])
        self.assertFalse(report["installer_ready"])
        self.assertEqual(report["pending_installer_tools"], ["podman"])
        self.assertFalse(
            guest.phase_assessment(checks, tools, storage, filesystems, 1)[
                "preparation_ready"
            ]
        )
        filesystems["/tmp"]["shares_root"] = False
        self.assertFalse(
            guest.phase_assessment(checks, tools, storage, filesystems, 0)[
                "preparation_ready"
            ]
        )

    def test_tls_failure_never_becomes_success(self):
        with mock.patch.object(guest.ssl, "create_default_context") as context:
            with mock.patch.object(
                guest.socket, "create_connection", side_effect=OSError
            ):
                self.assertFalse(
                    guest.trusted_https("example.invalid", "/nonexistent")["verified"]
                )
            context.assert_called_once_with()

    def test_installed_vendor_ca_retry_keeps_verification_and_sni(self):
        import ssl
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            ca = Path(directory) / "vendor.pem"
            ca.write_text("fixture-vendor-ca")
            system, vendor = mock.MagicMock(), mock.MagicMock()
            system.wrap_socket.side_effect = ssl.SSLCertVerificationError(1, "fixture")
            vendor.check_hostname = True
            vendor.verify_mode = ssl.CERT_REQUIRED
            with mock.patch.object(
                guest.ssl, "create_default_context", side_effect=[system, vendor]
            ):
                with mock.patch.object(guest.socket, "create_connection") as connection:
                    result = guest.trusted_https("example.invalid", directory)
            self.assertTrue(result["verified"])
            self.assertEqual(result["trust"], "installed_rhsm_ca")
            self.assertEqual(len(result["failed_attempts"]), 1)
            vendor.load_verify_locations.assert_called_once_with(cafile=str(ca))
            vendor.wrap_socket.assert_called_once_with(
                connection.return_value.__enter__.return_value,
                server_hostname="example.invalid",
            )
            self.assertTrue(vendor.check_hostname)
            self.assertEqual(vendor.verify_mode, ssl.CERT_REQUIRED)

    def test_tls_probe_uses_hostname_and_sends_no_application_data(self):
        with mock.patch.object(guest.ssl, "create_default_context") as context:
            with mock.patch.object(guest.socket, "create_connection") as connection:
                self.assertTrue(guest.trusted_https("example.invalid")["verified"])
            context.return_value.wrap_socket.assert_called_once_with(
                connection.return_value.__enter__.return_value,
                server_hostname="example.invalid",
            )
            context.return_value.wrap_socket.return_value.__enter__.return_value.send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
