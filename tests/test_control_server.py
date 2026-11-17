import errno
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
import control_server


class ControlServerTests(unittest.TestCase):
    def tearDown(self):
        server=getattr(self,'server',None)
        if server:
            server.server_close()

    def test_ephemeral_port_is_bound_on_loopback(self):
        self.server=control_server.create_local_server(0)
        self.assertEqual(self.server.server_address[0],'127.0.0.1')
        self.assertGreater(self.server.server_port,0)

    def test_busy_port_uses_next_available_candidate(self):
        fallback=object()
        busy=OSError(errno.EADDRINUSE,'Address already in use')
        with patch.object(control_server,'LocalServer',side_effect=[busy,fallback]) as factory:
            self.assertIs(control_server.create_local_server(8765,1),fallback)
        self.assertEqual([call.args[0][1] for call in factory.call_args_list],[8765,8766])

    def test_strict_port_reports_exhaustion(self):
        busy=OSError(errno.EADDRINUSE,'Address already in use')
        with patch.object(control_server,'LocalServer',side_effect=busy):
            with self.assertRaisesRegex(OSError,'8765'):
                control_server.create_local_server(8765,0)

    def test_windows_access_denied_port_uses_next_candidate(self):
        fallback=object()
        blocked=OSError(10013,'Access is denied')
        with patch.object(control_server,'LocalServer',side_effect=[blocked,fallback]) as factory:
            self.assertIs(control_server.create_local_server(8765,1),fallback)
        self.assertEqual([call.args[0][1] for call in factory.call_args_list],[8765,8766])
