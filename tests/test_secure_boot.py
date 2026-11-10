#!/usr/bin/python
# Copyright 2022 Northern.tech AS
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os
import platform

import pytest


def is_legacy_host():
    # The host running the tests: bookworm/jammy ship the 2M OVMF, which has
    # Secure Boot compiled in and always reports a state. Newer debianoids ship
    # only the 4M OVMF (see tests/uefi-nvram/README.md).
    codename = platform.freedesktop_os_release().get("VERSION_CODENAME")
    return codename in ("bookworm", "jammy")


@pytest.mark.only_with_image("uefiimg")
@pytest.mark.usefixtures("setup_board")
class TestSecureBoot:
    @pytest.mark.min_mender_version("1.0.0")
    def test_secure_boot_enabled(self, connection, conversion, bitbake_variables):
        if not conversion:
            pytest.skip("MEN-5253: Secure Boot not yet working for Yocto")

        # On modern (4M OVMF) hosts, images booted with Secure Boot off
        # (QEMU_NO_SECURE_BOOT=1) run on the plain, non-SB OVMF_CODE_4M.fd, which
        # exposes no SecureBoot state for mokutil to read -- so there is nothing
        # to assert. The firmware-choice comment in scripts/test/mender-convert-qemu
        # explains why (Ubuntu cannot boot the SMM/q35 .secboot firmware). The
        # legacy 2M firmware always reports a state, so the no-grub.d "disabled"
        # check below still runs on bookworm/jammy.
        if not is_legacy_host() and os.environ.get("QEMU_NO_SECURE_BOOT") == "1":
            pytest.skip(
                "Secure Boot disabled on a modern host; the non-SB OVMF cannot "
                "report Secure Boot state"
            )

        output = connection.run("mokutil --sb-state").stdout.strip()

        # For mender-convert, Secure Boot is disabled if `grub.d` integration is
        # turned off.
        if bitbake_variables["MENDER_GRUB_D_INTEGRATION"] == "n":
            assert "SecureBoot disabled" in output
            return

        assert output == "SecureBoot enabled"
